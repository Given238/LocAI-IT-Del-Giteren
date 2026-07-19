import logging

from . import llm, locations
from .candidates import fetch_candidate_pool
from .schemas import DayPlan, ItineraryResponse, PlaceOut

logger = logging.getLogger(__name__)


def _distance_km(row, start_coords):
    if start_coords is None:
        return None
    lat, lon = row.get("latitude"), row.get("longitude")
    if lat is None or lon is None:
        return None
    return locations.haversine_km(start_coords[0], start_coords[1], float(lat), float(lon))


def _place_out(row, category, price_min_key, price_max_key, detail_key=None, start_coords=None):
    return PlaceOut(
        id=row["id"],
        name=row.get("name") or row.get("transport_name"),
        category=category,
        price_min=row.get(price_min_key),
        price_max=row.get(price_max_key),
        address=row.get("address"),
        rating=row.get("rating"),
        detail=row.get(detail_key) if detail_key else None,
        distance_km=_distance_km(row, start_coords),
    )


def _index_by_id(rows):
    return {row["id"]: row for row in rows}


def _resolve(ids, index, category, price_min_key, price_max_key, detail_key=None, start_coords=None):
    """Only ids present in our own DB-backed candidate pool are trusted --
    anything the LLM invents that isn't in `index` is silently dropped
    rather than rendered, so a hallucinated id/name/price can never reach
    the response."""
    resolved = []
    for pid in ids or []:
        row = index.get(pid)
        if row is None:
            logger.warning("LLM referenced unknown %s id %r; dropping", category, pid)
            continue
        resolved.append(_place_out(row, category, price_min_key, price_max_key, detail_key, start_coords))
    return resolved


def _sum_range(places):
    lo = sum(p.price_min for p in places if p.price_min is not None)
    hi = sum((p.price_max if p.price_max is not None else p.price_min) for p in places if p.price_min is not None)
    return lo, hi


def build_itinerary(req) -> ItineraryResponse:
    pool = fetch_candidate_pool(req)

    candidates_considered = {
        "attractions": len(pool.attractions),
        "hotels": len(pool.hotels),
        "restaurants": len(pool.restaurants),
        "transport": len(pool.transport),
        "kuliner": len(pool.kuliner),
    }

    # Exact-match only -- an unrecognized start_location simply means no
    # distance data gets attached anywhere below, never a guessed nearest hub.
    start_coords = locations.resolve_start_location(req.start_location)
    distance_reference = req.start_location if start_coords else None

    if not pool.feasible:
        return ItineraryResponse(
            feasible=False,
            message="; ".join(pool.infeasible_reasons),
            constraints=req,
            summary=None,
            days=[],
            estimated_total_cost_min=None,
            estimated_total_cost_max=None,
            candidates_considered=candidates_considered,
            distance_reference=distance_reference,
        )

    plan = llm.generate_itinerary_plan(req, pool)

    attraction_idx = _index_by_id(pool.attractions)
    hotel_idx = _index_by_id(pool.hotels)
    restaurant_idx = _index_by_id(pool.restaurants)
    transport_idx = _index_by_id(pool.transport)

    days = []
    total_min = total_max = 0.0
    for day in plan.get("days", []):
        attractions = _resolve(
            day.get("attraction_ids"), attraction_idx, "attraction",
            "entry_fee_min", "entry_fee_max", "description", start_coords,
        )
        meals = _resolve(
            day.get("restaurant_ids"), restaurant_idx, "restaurant",
            "price_min", "price_max", "recommend_menu", start_coords,
        )
        transport = _resolve(
            day.get("transport_ids"), transport_idx, "transport",
            "price_min", "price_max", "route_raw",
        )
        lodging = None
        hotel_id = day.get("hotel_id")
        if hotel_id is not None:
            hotel_row = hotel_idx.get(hotel_id)
            if hotel_row is None:
                logger.warning("LLM referenced unknown hotel id %r; dropping", hotel_id)
            else:
                lodging = _place_out(hotel_row, "hotel", "price_min", "price_max", "facilities", start_coords)

        day_places = attractions + meals + transport + ([lodging] if lodging else [])
        day_min, day_max = _sum_range(day_places)
        total_min += day_min
        total_max += day_max

        days.append(DayPlan(
            day=day.get("day", len(days) + 1),
            attractions=attractions,
            meals=meals,
            lodging=lodging,
            transport=transport,
            narrative=day.get("narrative") or "",
            estimated_cost_min=day_min,
            estimated_cost_max=day_max,
        ))

    return ItineraryResponse(
        feasible=True,
        message=None,
        constraints=req,
        summary=plan.get("summary"),
        days=days,
        estimated_total_cost_min=total_min,
        estimated_total_cost_max=total_max,
        candidates_considered=candidates_considered,
        distance_reference=distance_reference,
    )
