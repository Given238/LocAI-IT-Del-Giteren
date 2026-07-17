"""
ETL pipeline: raw Dataset_Tourism.xlsx -> clean PostgreSQL tables.

Reads the panitia's raw Excel dataset, cleans/normalizes it, and loads it
into Postgres (DATABASE_URL from .env). Rebuilds all tables from scratch
on every run (DROP + CREATE) so it's safe to re-run during development.

Design rule followed throughout: never invent a value. Missing or
ambiguous data is left NULL and flagged via a needs_review column (or,
for reviews, a match_type of 'unmatched') rather than guessed.
"""
import os
import re
import sys
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from rapidfuzz import fuzz, process

load_dotenv()

DATASET_PATH = os.environ.get("DATASET_PATH", "data/raw/Dataset_Tourism.xlsx")
DATABASE_URL = os.environ.get("DATABASE_URL")
FUZZY_THRESHOLD_ATTRACTIONS = 90
FUZZY_THRESHOLD_REVIEWS = 88

HOTEL_TYPES = {
    "hotel", "guest house", "rumah wisata", "hotel bintang 1",
    "hotel bintang 2", "hotel bintang 3", "hotel bintang 4",
    "hotel bintang 5", "pondok", "vila", "villa", "hotel resor", "motel",
}
RESTO_TYPES = {"restoran", "restaurant", "rumah makan", "cafe", "kafe"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def clean_str(x):
    """Return a stripped, whitespace-collapsed string, or None if blank/NaN."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).replace("\xa0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s if s else None


def normalize_name(name):
    """Lowercase/collapsed form used only for matching, never stored."""
    s = clean_str(name)
    if s is None:
        return None
    return re.sub(r"\s+", " ", s.lower().strip())


def parse_comma_decimal(x):
    """'4,3' -> 4.3. Returns None if unparseable."""
    s = clean_str(x)
    if s is None:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_price(raw):
    """
    Parse a price field into (min, max, raw_text, needs_review).

    Handles: 'Gratis' (free), 'Sukarela' (donation - intentionally no
    fixed number, NOT the same as missing), single numbers, and
    "X - Y" ranges. Range separator may be a plain hyphen or a Unicode
    en-dash wrapped in non-breaking spaces (seen in resto-metadata).
    '.' is always treated as a thousands separator, consistent with
    every clean value in these columns.
    """
    s = clean_str(raw)
    if s is None:
        return None, None, None, False

    low = s.lower()
    if low == "gratis":
        return 0, 0, s, False
    if low == "sukarela":
        return None, None, s, False

    normalized = s.replace("–", "-").replace("—", "-")
    parts = re.split(r"\s*-\s*", normalized)

    def to_int(part):
        digits = re.sub(r"[^\d]", "", part)
        return int(digits) if digits else None

    if len(parts) == 1:
        val = to_int(parts[0])
        if val is None:
            return None, None, s, True
        return val, val, s, False
    if len(parts) == 2:
        lo, hi = to_int(parts[0]), to_int(parts[1])
        if lo is None or hi is None:
            return None, None, s, True
        return lo, hi, s, False
    return None, None, s, True


def parse_latlong(raw):
    """'lat, lon' text -> (lat, lon) floats, or (None, None) if unparseable."""
    s = clean_str(raw)
    if s is None:
        return None, None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def richness(record, fields):
    return sum(1 for f in fields if record.get(f) is not None)


# ---------------------------------------------------------------------------
# Load & pre-clean
# ---------------------------------------------------------------------------

def load_sheets():
    xls = pd.ExcelFile(DATASET_PATH)
    sheets = {}
    for name in [
        "wisata-metadata", "tempat-wisata-v1", "hotel-metadata",
        "resto-metadata", "transportasi", "kuliner", "wisata-v2",
        "resto-hotel-v2",
    ]:
        sheets[name] = pd.read_excel(xls, sheet_name=name)
    return sheets


def drop_blank_rows(df, key_col):
    """Drop rows where the key (name) column is blank. Returns (df, n_dropped)."""
    before = len(df)
    mask = df[key_col].apply(clean_str).notna()
    cleaned = df[mask].copy()
    return cleaned, before - len(cleaned)


# ---------------------------------------------------------------------------
# Attractions: merge wisata-metadata + tempat-wisata-v1, dedupe
# ---------------------------------------------------------------------------

def build_attraction_records(sheets):
    wm, n_drop_wm = drop_blank_rows(sheets["wisata-metadata"], "place-name")
    tv1, n_drop_tv1 = drop_blank_rows(sheets["tempat-wisata-v1"], "place")

    records = []
    for _, row in wm.iterrows():
        lat, lon = parse_latlong(row.get("lat-long"))
        fee_min, fee_max, fee_raw, fee_review = parse_price(row.get("entry-fee"))
        records.append({
            "name": clean_str(row.get("place-name")),
            "place_type": clean_str(row.get("place-type")),
            "entry_fee_min": fee_min, "entry_fee_max": fee_max,
            "entry_fee_raw": fee_raw, "entry_fee_needs_review": fee_review,
            "latitude": lat, "longitude": lon,
            "operational_hour": clean_str(row.get("operational-hour")),
            "operational_day": clean_str(row.get("operational-day")),
            "address": clean_str(row.get("address")),
            "rating": parse_comma_decimal(row.get("place-rating")),
            "status": clean_str(row.get("status")),
            "ownership": clean_str(row.get("place-ownership")),
            "description": clean_str(row.get("description")),
            "source": "wisata-metadata",
        })
    for _, row in tv1.iterrows():
        fee_min, fee_max, fee_raw, fee_review = parse_price(row.get("entry-fee"))
        records.append({
            "name": clean_str(row.get("place")),
            "place_type": clean_str(row.get("type")),
            "entry_fee_min": fee_min, "entry_fee_max": fee_max,
            "entry_fee_raw": fee_raw, "entry_fee_needs_review": fee_review,
            "latitude": None, "longitude": None,
            "operational_hour": clean_str(row.get("service-hour")),
            "operational_day": None,
            "address": clean_str(row.get("add")),
            "rating": parse_comma_decimal(row.get("rating")),
            "status": None,
            "ownership": None,
            "description": clean_str(row.get("addons")),
            "source": "tempat-wisata-v1",
        })

    return records, {"wisata-metadata": (len(sheets["wisata-metadata"]), n_drop_wm),
                      "tempat-wisata-v1": (len(sheets["tempat-wisata-v1"]), n_drop_tv1)}


RICH_FIELDS = ["place_type", "entry_fee_min", "latitude", "operational_hour",
               "address", "rating", "status", "ownership", "description"]


def dedupe_attractions(records):
    """
    Group records by exact normalized name, then fuzzy-match remaining
    singleton groups against each other. Within a group, the richest
    record is the base; missing fields are filled from other members.
    Returns (final_records, merge_log).
    """
    groups = {}
    for r in records:
        key = normalize_name(r["name"])
        groups.setdefault(key, []).append(r)

    keys = list(groups.keys())
    merge_log = []
    used = set()
    fuzzy_merged = {}  # key -> target key it was merged into

    for i, k1 in enumerate(keys):
        if k1 in used:
            continue
        for k2 in keys[i + 1:]:
            if k2 in used:
                continue
            score = fuzz.token_sort_ratio(k1, k2)
            if score >= FUZZY_THRESHOLD_ATTRACTIONS:
                groups[k1].extend(groups[k2])
                used.add(k2)
                fuzzy_merged[k2] = k1
                merge_log.append({
                    "name_a": groups[k1][0]["name"], "name_b": k2,
                    "score": score, "type": "fuzzy",
                })

    final_records = []
    for key, members in groups.items():
        if key in used:
            continue
        if len(members) > 1:
            base = max(members, key=lambda r: richness(r, RICH_FIELDS))
            for other in members:
                if other is base:
                    continue
                for field in RICH_FIELDS + ["longitude"]:
                    if base.get(field) is None and other.get(field) is not None:
                        base[field] = other[field]
            base["source"] = ",".join(sorted({m["source"] for m in members}))
            final_records.append(base)
        else:
            final_records.append(members[0])

    return final_records, merge_log


# ---------------------------------------------------------------------------
# Hotels / restaurants: reclassify hotel-metadata, merge resto-metadata
# ---------------------------------------------------------------------------

def build_hotel_and_restaurant_records(sheets):
    hm, n_drop_hm = drop_blank_rows(sheets["hotel-metadata"], "place-name")
    rm, n_drop_rm = drop_blank_rows(sheets["resto-metadata"], "place-name")

    hotels, restaurants = [], []

    for _, row in hm.iterrows():
        pt_raw = clean_str(row.get("place-type"))
        pt_norm = pt_raw.lower() if pt_raw else None
        lat, lon = parse_latlong(row.get("lat-long"))
        p_min, p_max, p_raw, p_review = parse_price(row.get("price-per-head"))
        rec = {
            "name": clean_str(row.get("place-name")),
            "place_type_raw": pt_raw,
            "price_min": p_min, "price_max": p_max, "price_raw": p_raw,
            "check_in": clean_str(row.get("check-in")),
            "check_out": clean_str(row.get("check-out")),
            "opening_hours": None,
            "recommend_menu": clean_str(row.get("recommend-menu")),
            "facilities": clean_str(row.get("Fasilitas")),
            "address": clean_str(row.get("address")),
            "latitude": lat, "longitude": lon,
            "rating": row.get("place-rating") if pd.notna(row.get("place-rating")) else None,
            "status": clean_str(row.get("status")),
            "source_sheet": "hotel-metadata",
            "needs_review": p_review,
            "review_notes": "price unparseable" if p_review else None,
        }
        if pt_norm in HOTEL_TYPES:
            hotels.append(rec)
        elif pt_norm in RESTO_TYPES:
            restaurants.append(rec)
        else:
            rec["needs_review"] = True
            note = f"unrecognized place-type '{pt_raw}' in hotel-metadata; kept as hotel pending manual classification"
            rec["review_notes"] = (rec["review_notes"] + "; " + note) if rec["review_notes"] else note
            hotels.append(rec)

    for _, row in rm.iterrows():
        lat, lon = parse_latlong(row.get("lat-long"))
        p_min, p_max, p_raw, p_review = parse_price(row.get("price-per-head"))
        restaurants.append({
            "name": clean_str(row.get("place-name")),
            "place_type_raw": clean_str(row.get("place-type")),
            "price_min": p_min, "price_max": p_max, "price_raw": p_raw,
            "check_in": None, "check_out": None,
            "opening_hours": clean_str(row.get("opening-hours")),
            "recommend_menu": clean_str(row.get("recommend-menu")),
            "facilities": clean_str(row.get("Fasilitas")),
            "address": clean_str(row.get("address")),
            "latitude": lat, "longitude": lon,
            "rating": row.get("place-rating") if pd.notna(row.get("place-rating")) else None,
            "status": clean_str(row.get("status")),
            "source_sheet": "resto-metadata",
            "needs_review": p_review,
            "review_notes": "price unparseable" if p_review else None,
        })

    counts = {"hotel-metadata": (len(sheets["hotel-metadata"]), n_drop_hm),
              "resto-metadata": (len(sheets["resto-metadata"]), n_drop_rm)}
    return hotels, restaurants, counts


# ---------------------------------------------------------------------------
# Transport / kuliner
# ---------------------------------------------------------------------------

def build_transport_records(sheets):
    tr, n_drop = drop_blank_rows(sheets["transportasi"], "transport-name")
    records = []
    for _, row in tr.iterrows():
        p_min, p_max, p_raw, _ = parse_price(row.get("price"))
        direction = clean_str(row.get("direction"))
        origin = destination = None
        if direction:
            legs = re.split(r"\s+ke\s+", direction, flags=re.IGNORECASE)
            if len(legs) == 2:
                origin, destination = legs[0].strip(), legs[1].strip()
        records.append({
            "transport_name": clean_str(row.get("transport-name")),
            "route_raw": direction,
            "origin": origin, "destination": destination,
            "price_min": p_min, "price_max": p_max, "price_raw": p_raw,
            "vehicle_type": clean_str(row.get("jenis-mobil")),
            "description": clean_str(row.get("description")),
            "operational_hour": clean_str(row.get("operational-hour")),
        })
    return records, {"transportasi": (len(sheets["transportasi"]), n_drop)}


def build_kuliner_records(sheets):
    kl, n_drop = drop_blank_rows(sheets["kuliner"], "kuliner-name")
    records = [{"name": clean_str(row.get("kuliner-name")),
                "description": clean_str(row.get("description"))}
               for _, row in kl.iterrows()]
    return records, {"kuliner": (len(sheets["kuliner"]), n_drop)}


# ---------------------------------------------------------------------------
# Reviews: fuzzy-match to places, never drop unmatched rows
# ---------------------------------------------------------------------------

def match_place(raw_name, choices_map):
    """
    choices_map: {normalized_name: id_or_(table,id)}
    Returns (matched_value, match_type, score).
    """
    norm = normalize_name(raw_name)
    if norm is None:
        return None, "unmatched", None
    if norm in choices_map:
        return choices_map[norm], "exact", 100.0
    result = process.extractOne(norm, choices_map.keys(), scorer=fuzz.token_sort_ratio,
                                 score_cutoff=FUZZY_THRESHOLD_REVIEWS)
    if result:
        best_key, score, _ = result
        return choices_map[best_key], "fuzzy", score
    return None, "unmatched", None


def build_wisata_reviews(sheets, attraction_id_by_name):
    df = sheets["wisata-v2"]
    rows = []
    unmatched_samples = []
    match_counts = {"exact": 0, "fuzzy": 0, "unmatched": 0}
    for _, row in df.iterrows():
        raw_name = row.get("place-name")
        aid, match_type, score = match_place(raw_name, attraction_id_by_name)
        match_counts[match_type] += 1
        if match_type == "unmatched" and len(unmatched_samples) < 15:
            unmatched_samples.append(clean_str(raw_name))
        scraped = row.get("scraped-at-date")
        rows.append((
            aid, clean_str(raw_name), match_type, score,
            clean_str(row.get("name")),
            row.get("reviewer-rating") if pd.notna(row.get("reviewer-rating")) else None,
            clean_str(row.get("review-text")),
            clean_str(row.get("published-at")),
            scraped.date() if pd.notna(scraped) else None,
        ))
    return rows, match_counts, unmatched_samples


def build_resto_hotel_reviews(sheets, place_id_by_name):
    df = sheets["resto-hotel-v2"]
    rows = []
    unmatched_samples = []
    match_counts = {"exact": 0, "fuzzy": 0, "unmatched": 0}
    for _, row in df.iterrows():
        raw_name = row.get("place-name")
        result, match_type, score = match_place(raw_name, place_id_by_name)
        match_counts[match_type] += 1
        table, pid = result if result else (None, None)
        if match_type == "unmatched" and len(unmatched_samples) < 15:
            unmatched_samples.append(clean_str(raw_name))
        scraped = row.get("scraped-at-date")
        rows.append((
            table, pid, clean_str(raw_name), match_type, score,
            clean_str(row.get("name")),
            row.get("reviewer-rating") if pd.notna(row.get("reviewer-rating")) else None,
            clean_str(row.get("review-text")),
            clean_str(row.get("reviewer-type")),
            clean_str(row.get("published-at")),
            scraped.date() if pd.notna(scraped) else None,
        ))
    return rows, match_counts, unmatched_samples


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DDL = """
DROP TABLE IF EXISTS wisata_reviews, resto_hotel_reviews, attractions,
    hotels, restaurants, transport, kuliner CASCADE;

CREATE TABLE attractions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    place_type TEXT,
    entry_fee_min NUMERIC,
    entry_fee_max NUMERIC,
    entry_fee_raw TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    operational_hour TEXT,
    operational_day TEXT,
    address TEXT,
    rating NUMERIC,
    status TEXT,
    ownership TEXT,
    description TEXT,
    source_sheets TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_notes TEXT
);

CREATE TABLE hotels (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    place_type_raw TEXT,
    price_min NUMERIC,
    price_max NUMERIC,
    price_raw TEXT,
    check_in TEXT,
    check_out TEXT,
    opening_hours TEXT,
    recommend_menu TEXT,
    facilities TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    rating NUMERIC,
    status TEXT,
    source_sheet TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_notes TEXT
);

CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    place_type_raw TEXT,
    price_min NUMERIC,
    price_max NUMERIC,
    price_raw TEXT,
    check_in TEXT,
    check_out TEXT,
    opening_hours TEXT,
    recommend_menu TEXT,
    facilities TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    rating NUMERIC,
    status TEXT,
    source_sheet TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_notes TEXT
);

CREATE TABLE transport (
    id SERIAL PRIMARY KEY,
    transport_name TEXT,
    route_raw TEXT,
    origin TEXT,
    destination TEXT,
    price_min NUMERIC,
    price_max NUMERIC,
    price_raw TEXT,
    vehicle_type TEXT,
    description TEXT,
    operational_hour TEXT
);

CREATE TABLE kuliner (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE wisata_reviews (
    id SERIAL PRIMARY KEY,
    attraction_id INT REFERENCES attractions(id),
    raw_place_name TEXT,
    match_type TEXT NOT NULL,
    match_score NUMERIC,
    reviewer_name TEXT,
    reviewer_rating NUMERIC,
    review_text TEXT,
    published_at_raw TEXT,
    scraped_at_date DATE
);

CREATE TABLE resto_hotel_reviews (
    id SERIAL PRIMARY KEY,
    place_table TEXT,
    place_id INT,
    raw_place_name TEXT,
    match_type TEXT NOT NULL,
    match_score NUMERIC,
    reviewer_name TEXT,
    reviewer_rating NUMERIC,
    review_text TEXT,
    reviewer_type TEXT,
    published_at_raw TEXT,
    scraped_at_date DATE
);
"""


def insert_attractions(cur, records):
    cols = ["name", "place_type", "entry_fee_min", "entry_fee_max", "entry_fee_raw",
            "latitude", "longitude", "operational_hour", "operational_day", "address",
            "rating", "status", "ownership", "description", "source_sheets",
            "needs_review", "review_notes"]
    values = []
    for r in records:
        values.append((
            r["name"], r["place_type"], r["entry_fee_min"], r["entry_fee_max"],
            r["entry_fee_raw"], r["latitude"], r["longitude"], r["operational_hour"],
            r["operational_day"], r["address"], r["rating"], r["status"],
            r["ownership"], r["description"], r["source"],
            bool(r.get("entry_fee_needs_review")),
            "entry fee unparseable" if r.get("entry_fee_needs_review") else None,
        ))
    query = f"INSERT INTO attractions ({', '.join(cols)}) VALUES %s RETURNING id, name"
    result = psycopg2.extras.execute_values(cur, query, values, fetch=True)
    return result


def insert_hotels_or_restaurants(cur, table, records):
    cols = ["name", "place_type_raw", "price_min", "price_max", "price_raw",
            "check_in", "check_out", "opening_hours", "recommend_menu", "facilities",
            "address", "latitude", "longitude", "rating", "status", "source_sheet",
            "needs_review", "review_notes"]
    values = [tuple(r[c] for c in cols) for r in records]
    query = f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s RETURNING id, name"
    return psycopg2.extras.execute_values(cur, query, values, fetch=True)


def insert_transport(cur, records):
    cols = ["transport_name", "route_raw", "origin", "destination", "price_min",
            "price_max", "price_raw", "vehicle_type", "description", "operational_hour"]
    values = [tuple(r[c] for c in cols) for r in records]
    psycopg2.extras.execute_values(
        cur, f"INSERT INTO transport ({', '.join(cols)}) VALUES %s", values)


def insert_kuliner(cur, records):
    values = [(r["name"], r["description"]) for r in records]
    psycopg2.extras.execute_values(
        cur, "INSERT INTO kuliner (name, description) VALUES %s", values)


def insert_wisata_reviews(cur, rows):
    cols = ["attraction_id", "raw_place_name", "match_type", "match_score",
            "reviewer_name", "reviewer_rating", "review_text", "published_at_raw",
            "scraped_at_date"]
    psycopg2.extras.execute_values(
        cur, f"INSERT INTO wisata_reviews ({', '.join(cols)}) VALUES %s", rows)


def insert_resto_hotel_reviews(cur, rows):
    cols = ["place_table", "place_id", "raw_place_name", "match_type", "match_score",
            "reviewer_name", "reviewer_rating", "review_text", "reviewer_type",
            "published_at_raw", "scraped_at_date"]
    psycopg2.extras.execute_values(
        cur, f"INSERT INTO resto_hotel_reviews ({', '.join(cols)}) VALUES %s", rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not DATABASE_URL:
        sys.exit("DATABASE_URL not set in .env")
    if not Path(DATASET_PATH).exists():
        sys.exit(f"Dataset not found at {DATASET_PATH}")

    print(f"Loading {DATASET_PATH} ...")
    sheets = load_sheets()
    before_counts = {}

    attraction_records, c = build_attraction_records(sheets)
    before_counts.update(c)
    final_attractions, merge_log = dedupe_attractions(attraction_records)

    hotels, restaurants, c = build_hotel_and_restaurant_records(sheets)
    before_counts.update(c)

    transport_records, c = build_transport_records(sheets)
    before_counts.update(c)

    kuliner_records, c = build_kuliner_records(sheets)
    before_counts.update(c)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            print("Rebuilding schema ...")
            cur.execute(DDL)

            print("Inserting attractions ...")
            attraction_rows = insert_attractions(cur, final_attractions)
            attraction_id_by_name = {normalize_name(name): aid for aid, name in attraction_rows}

            print("Inserting hotels ...")
            hotel_rows = insert_hotels_or_restaurants(cur, "hotels", hotels)
            print("Inserting restaurants ...")
            restaurant_rows = insert_hotels_or_restaurants(cur, "restaurants", restaurants)

            place_id_by_name = {}
            for hid, name in hotel_rows:
                place_id_by_name[normalize_name(name)] = ("hotels", hid)
            for rid, name in restaurant_rows:
                place_id_by_name.setdefault(normalize_name(name), ("restaurants", rid))

            print("Inserting transport ...")
            insert_transport(cur, transport_records)

            print("Inserting kuliner ...")
            insert_kuliner(cur, kuliner_records)

            print("Matching + inserting wisata-v2 reviews (fuzzy matching, this may take a moment) ...")
            wisata_review_rows, wv2_counts, wv2_unmatched_samples = build_wisata_reviews(
                sheets, attraction_id_by_name)
            insert_wisata_reviews(cur, wisata_review_rows)

            print("Matching + inserting resto-hotel-v2 reviews ...")
            rh_review_rows, rh_counts, rh_unmatched_samples = build_resto_hotel_reviews(
                sheets, place_id_by_name)
            insert_resto_hotel_reviews(cur, rh_review_rows)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("BEFORE (raw sheet rows -> blank rows dropped)")
    print("=" * 70)
    for sheet, (before, dropped) in before_counts.items():
        print(f"  {sheet:<20} {before:>6} rows  ({dropped} blank dropped)")
    print(f"  wisata-v2            {len(sheets['wisata-v2']):>6} rows")
    print(f"  resto-hotel-v2       {len(sheets['resto-hotel-v2']):>6} rows")

    print("\n" + "=" * 70)
    print("AFTER (rows loaded per table)")
    print("=" * 70)
    n_needs_review_attr = sum(1 for r in final_attractions if r.get("entry_fee_needs_review"))
    print(f"  attractions          {len(final_attractions):>6}  "
          f"(from {len(attraction_records)} raw wm+tv1 records, "
          f"{len(attraction_records) - len(final_attractions)} merged away, "
          f"{len(merge_log)} via fuzzy match, {n_needs_review_attr} needs_review)")
    print(f"  hotels               {len(hotels):>6}  "
          f"(needs_review: {sum(1 for h in hotels if h['needs_review'])})")
    print(f"  restaurants          {len(restaurants):>6}  "
          f"(needs_review: {sum(1 for r in restaurants if r['needs_review'])})")
    print(f"  transport            {len(transport_records):>6}")
    print(f"  kuliner              {len(kuliner_records):>6}")
    print(f"  wisata_reviews       {len(wisata_review_rows):>6}  "
          f"(exact {wv2_counts['exact']}, fuzzy {wv2_counts['fuzzy']}, "
          f"unmatched {wv2_counts['unmatched']})")
    print(f"  resto_hotel_reviews  {len(rh_review_rows):>6}  "
          f"(exact {rh_counts['exact']}, fuzzy {rh_counts['fuzzy']}, "
          f"unmatched {rh_counts['unmatched']})")

    print("\n" + "=" * 70)
    print("SPOT-CHECK: fuzzy attraction merges (verify these aren't false positives)")
    print("=" * 70)
    if merge_log:
        for m in merge_log:
            print(f"  '{m['name_a']}' <- '{m['name_b']}'  (score {m['score']:.0f})")
    else:
        print("  (none - all cross-sheet matches were exact-name)")

    print("\n" + "=" * 70)
    print("SPOT-CHECK: hotel-metadata rows needing manual review")
    print("=" * 70)
    for h in hotels:
        if h["needs_review"]:
            print(f"  '{h['name']}' - {h['review_notes']}")

    print("\n" + "=" * 70)
    print("SAMPLE unmatched review place-names (not linked to any place, kept in DB)")
    print("=" * 70)
    print(f"  wisata_reviews ({wv2_counts['unmatched']} total unmatched), sample:")
    for n in wv2_unmatched_samples:
        print(f"    - {n}")
    print(f"  resto_hotel_reviews ({rh_counts['unmatched']} total unmatched), sample:")
    for n in rh_unmatched_samples:
        print(f"    - {n}")

    print("\nDone.")


if __name__ == "__main__":
    main()
