from dataclasses import dataclass, field
from typing import Optional

from . import db

# Maps user-facing interest keywords to attractions.place_type values.
# "culinary" deliberately has no attraction place_type: it doesn't filter
# attractions, it's satisfied by restaurants/kuliner which are always
# included regardless of interests.
INTEREST_PLACE_TYPES = {
    "nature": ["Wisata Alam"],
    "culture": ["Wisata Budaya / Sejarah", "Museum"],
    "history": ["Wisata Budaya / Sejarah", "Museum"],
    "spiritual": ["Wisata Rohani"],
    "religious": ["Wisata Rohani"],
    "recreation": ["Wisata Buatan"],
    "business": ["Wisata Bisnis"],
}


def resolve_attraction_place_types(interests: Optional[list[str]]) -> Optional[list[str]]:
    if not interests:
        return None
    types = set()
    for interest in interests:
        types.update(INTEREST_PLACE_TYPES.get(interest.strip().lower(), []))
    return sorted(types) if types else None


@dataclass
class CandidatePool:
    attractions: list
    hotels: list
    restaurants: list
    transport: list
    kuliner: list
    infeasible_reasons: list = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.infeasible_reasons


def _rows_to_dicts(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_attractions(cur, budget, interests, limit=40):
    place_types = resolve_attraction_place_types(interests)
    sql = """
        SELECT id, name, place_type, entry_fee_min, entry_fee_max, address,
               rating, operational_hour, description, latitude, longitude
        FROM attractions
        WHERE needs_review = FALSE
          AND (status IS NULL OR status <> 'tutup')
          AND (entry_fee_min IS NULL OR entry_fee_min <= %s)
    """
    params = [budget]
    if place_types:
        sql += " AND place_type = ANY(%s)"
        params.append(place_types)
    sql += " ORDER BY rating DESC NULLS LAST LIMIT %s"
    params.append(limit)
    cur.execute(sql, params)
    return _rows_to_dicts(cur)


def query_hotels(cur, budget, limit=20):
    cur.execute(
        """
        SELECT id, name, place_type_raw, price_min, price_max, address, rating, facilities,
               latitude, longitude
        FROM hotels
        WHERE needs_review = FALSE
          AND (status IS NULL OR status <> 'tutup')
          AND (price_min IS NULL OR price_min <= %s)
        ORDER BY rating DESC NULLS LAST LIMIT %s
        """,
        [budget, limit],
    )
    return _rows_to_dicts(cur)


def query_restaurants(cur, budget, limit=30):
    cur.execute(
        """
        SELECT id, name, place_type_raw, price_min, price_max, address, rating, recommend_menu,
               latitude, longitude
        FROM restaurants
        WHERE needs_review = FALSE
          AND (status IS NULL OR status <> 'tutup')
          AND (price_min IS NULL OR price_min <= %s)
        ORDER BY rating DESC NULLS LAST LIMIT %s
        """,
        [budget, limit],
    )
    return _rows_to_dicts(cur)


def query_transport(cur, start_location, budget):
    like = f"%{start_location.strip()}%"
    cur.execute(
        """
        SELECT id, transport_name, route_raw, origin, destination, price_min, price_max,
               vehicle_type, operational_hour
        FROM transport
        WHERE (price_min IS NULL OR price_min <= %s)
          AND (route_raw ILIKE %s OR transport_name ILIKE %s)
        ORDER BY price_min NULLS LAST
        """,
        [budget, like, like],
    )
    rows = _rows_to_dicts(cur)
    if rows:
        return rows
    # No route mentions the start location by name (dataset only covers ~16
    # routes) -- fall back to all budget-feasible routes rather than
    # returning zero transport options.
    cur.execute(
        """
        SELECT id, transport_name, route_raw, origin, destination, price_min, price_max,
               vehicle_type, operational_hour
        FROM transport
        WHERE (price_min IS NULL OR price_min <= %s)
        ORDER BY price_min NULLS LAST
        """,
        [budget],
    )
    return _rows_to_dicts(cur)


def query_kuliner(cur, limit=8):
    cur.execute("SELECT id, name, description FROM kuliner LIMIT %s", [limit])
    return _rows_to_dicts(cur)


def fetch_candidate_pool(req) -> CandidatePool:
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        attractions = query_attractions(cur, req.budget, req.interests)
        hotels = query_hotels(cur, req.budget) if req.duration_nights > 0 else []
        restaurants = query_restaurants(cur, req.budget)
        transport = query_transport(cur, req.start_location, req.budget)
        kuliner = query_kuliner(cur)
    finally:
        conn.close()

    reasons = []
    if not attractions:
        interest_note = f" matching interests {req.interests}" if req.interests else ""
        reasons.append(f"No attractions found within budget Rp{req.budget:,.0f}{interest_note}")
    if not restaurants:
        reasons.append(f"No restaurants found within budget Rp{req.budget:,.0f}")
    if req.duration_nights > 0 and not hotels:
        reasons.append(
            f"No lodging found within budget Rp{req.budget:,.0f} for a {req.duration_nights}-night stay"
        )

    # A row with price_min IS NULL passes the SQL filter above (unknown price
    # isn't excluded, in case it happens to be affordable) but that also lets
    # an impossible budget slip through as "feasible" if every remaining
    # candidate has no known price. Gate on the cheapest *known* price per
    # required category actually fitting the budget.
    if not reasons:
        known_restaurant_prices = [float(r["price_min"]) for r in restaurants if r["price_min"] is not None]
        known_hotel_prices = [float(h["price_min"]) for h in hotels if h["price_min"] is not None]
        known_transport_prices = [float(t["price_min"]) for t in transport if t["price_min"] is not None]

        cheapest_total = 0.0
        if known_restaurant_prices:
            meals_needed = max(1, req.duration_nights + 1)
            cheapest_total += min(known_restaurant_prices) * meals_needed
        elif restaurants:
            reasons.append("No restaurants with a known price found -- cannot confirm this budget is workable")

        if req.duration_nights > 0:
            if known_hotel_prices:
                cheapest_total += min(known_hotel_prices) * req.duration_nights
            elif hotels:
                reasons.append("No lodging with a known price found -- cannot confirm this budget is workable")

        if known_transport_prices:
            cheapest_total += min(known_transport_prices)

        if not reasons and cheapest_total > req.budget:
            reasons.append(
                f"Even the cheapest available options (~Rp{cheapest_total:,.0f} for lodging/food/transport) "
                f"exceed your budget of Rp{req.budget:,.0f}"
            )

    return CandidatePool(attractions, hotels, restaurants, transport, kuliner, reasons)
