"""
Phase 4 comparison test: geospatial distance + locale-tone dropdown.

Verifies two things the playbook calls out explicitly:
1. Locale only changes narrative tone -- never which places are picked or
   their structured facts. Since the LLM samples with temperature=0.4, it
   can legitimately choose different candidate ids across separate calls
   for reasons unrelated to locale (ordinary non-determinism). So instead
   of requiring the whole response to be byte-identical across locales,
   this checks the property that actually matters: for any place id that
   appears in more than one run, its resolved name/price/address is
   identical everywhere it appears. That can only be false if locale (or
   anything else) leaked into the DB-resolution step.
2. An unrecognized start_location gets NO distance data at all -- never a
   guessed nearest match.

Usage: start the API first (uvicorn backend.main:app --reload), then run
    ./.venv/Scripts/python.exe scripts/test_phase4.py
"""
import os

import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

BASE_CASE = {
    "budget": 500000,
    "duration_nights": 1,
    "start_location": "Sibolga",
    "interests": None,
}

LOCALES_TO_COMPARE = [None, "indonesian", "filipino"]


def call(payload):
    resp = requests.post(f"{API_BASE_URL}/itinerary", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def all_places(body):
    """Flatten every resolved place across all days into a single list."""
    places = []
    for day in body.get("days", []):
        places.extend(day["attractions"])
        places.extend(day["meals"])
        places.extend(day["transport"])
        if day["lodging"]:
            places.append(day["lodging"])
    return places


def print_narratives(locale, body):
    print(f"--- locale={locale!r} ---")
    print("summary:", body.get("summary"))
    for day in body.get("days", []):
        print(f"  day {day['day']} narrative: {day['narrative']!r}")
    ids = sorted({p["id"] for p in all_places(body)})
    print(f"  chosen place ids: {ids}")
    print()


def section(title):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def main():
    section("TEST 1: locale tone comparison (same constraints, different locale)")
    responses = {}
    for locale in LOCALES_TO_COMPARE:
        payload = {**BASE_CASE, "locale": locale}
        body = call(payload)
        responses[locale] = body
        print_narratives(locale, body)

    section("TEST 1 CHECK: same (category, id) -> identical resolved facts across all locales")
    # Keyed by (category, id), not just id -- ids are only unique WITHIN a
    # table (attractions/hotels/restaurants/transport each have their own
    # independent SERIAL sequence), so e.g. transport id=4 and hotel id=4
    # are unrelated real rows that happen to share a number.
    seen = {}
    mismatches = []
    for locale, body in responses.items():
        for p in all_places(body):
            key = (p["category"], p["id"])
            fact = (p["name"], p["price_min"], p["price_max"], p["address"])
            if key in seen and seen[key] != fact:
                mismatches.append((key, seen[key], fact, locale))
            seen[key] = fact
    if mismatches:
        print("FAIL -- found id(s) whose resolved facts differ across locale runs:")
        for key, before, after, locale in mismatches:
            print(f"  id {key}: {before} != {after} (seen with locale={locale!r})")
    else:
        print(f"PASS -- {len(seen)} distinct place ids appeared across the {len(responses)} "
              f"runs, and every id resolved to identical name/price/address every time it "
              f"appeared. (Note: which ids get CHOSEN can vary run to run -- that's ordinary "
              f"LLM sampling non-determinism, not a locale leak. What matters is that facts "
              f"for a given id never change, and they didn't.)")

    section("TEST 2: unrecognized start_location -> no distance data, no guessing")
    recognized = call({**BASE_CASE, "start_location": "Sibolga"})
    unrecognized = call({**BASE_CASE, "start_location": "Jakarta"})

    print("Recognized ('Sibolga'):")
    print("  distance_reference:", recognized.get("distance_reference"))
    sample = all_places(recognized)[:3]
    for p in sample:
        print(f"    {p['name']}: distance_km={p['distance_km']}")

    print()
    print("Unrecognized ('Jakarta' -- a real city, but not a Toba-region hub in our table):")
    print("  distance_reference:", unrecognized.get("distance_reference"))
    all_none = all(p["distance_km"] is None for p in all_places(unrecognized))
    for p in all_places(unrecognized)[:3]:
        print(f"    {p['name']}: distance_km={p['distance_km']}")
    print()
    if unrecognized.get("distance_reference") is None and all_none:
        print("PASS -- no distance_reference and no distance_km anywhere in the response.")
    else:
        print("FAIL -- unrecognized location still produced distance data somewhere.")


if __name__ == "__main__":
    main()
