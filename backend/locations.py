import math
import re
from typing import Optional

# Curated Toba-region hubs, real approximate town-center coordinates.
# Deliberately NOT exhaustive -- this is the "no guessing" boundary: if a
# start_location doesn't land here (directly or via LOCATION_ALIASES), we
# return no distance data rather than fuzzy-matching to the nearest name.
LOCATION_COORDS = {
    "medan": (3.5952, 98.6722),
    "sibolga": (1.7427, 98.7792),
    "parapat": (2.6587, 98.9376),
    "balige": (2.3325, 99.0625),
    "silangit airport": (2.2528, 98.9917),
    "tuktuk": (2.6667, 98.8500),
    "pangururan": (2.7667, 98.7667),
    "tomok": (2.6167, 98.8500),
    "ambarita": (2.6833, 98.8500),
    "simanindo": (2.7000, 98.8333),
    "ajibata": (2.6167, 98.9333),
    "tebing tinggi": (3.3286, 99.1625),
    "pematang siantar": (2.9595, 99.0687),
    "tarutung": (2.0167, 98.9667),
    "dolok sanggul": (2.1833, 98.9833),
    "siborong-borong": (2.1667, 98.9500),
    "muara": (2.3667, 99.0333),
    "porsea": (2.3833, 99.1333),
    "laguboti": (2.3833, 99.1667),
    "onan runggu": (2.5333, 98.9167),
    "tigaras": (2.8333, 99.0667),
}

# Known real-world aliases for the same hubs above -- curated ahead of time,
# not resolved at request time. This is distinct from fuzzy-matching an
# unrecognized input: every alias here is an exact, deliberately-chosen
# string, not a similarity guess.
LOCATION_ALIASES = {
    "samosir": "pangururan",
    "medan amplas": "medan",
    "bandara silangit": "silangit airport",
    "silangit": "silangit airport",
    "institut teknologi del": "laguboti",
    "institut teknologi del, laguboti": "laguboti",
    "itdel": "laguboti",
    "siantar": "pematang siantar",
    "pematangsiantar": "pematang siantar",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def resolve_start_location(start_location: str) -> Optional[tuple[float, float]]:
    """
    Exact-match only (after normalization) against LOCATION_COORDS /
    LOCATION_ALIASES. Returns None if there's no match -- callers must NOT
    fall back to a nearest-sounding guess; distance data should simply be
    omitted for that request.
    """
    key = _normalize(start_location)
    if key in LOCATION_COORDS:
        return LOCATION_COORDS[key]
    if key in LOCATION_ALIASES:
        return LOCATION_COORDS[LOCATION_ALIASES[key]]
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
