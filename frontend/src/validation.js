// Single source of truth for the itinerary constraint fields' validation --
// shared by ItineraryForm and Onboarding so there is exactly one set of
// rules, matching what the backend's ItineraryRequest actually requires
// (backend/schemas.py: budget > 0, duration_nights >= 0 integer,
// start_location non-empty; interests/locale are always optional).

export function isValidBudget(raw) {
  if (raw === "" || raw === null || raw === undefined) return false;
  const n = Number(raw);
  return !Number.isNaN(n) && n > 0;
}

export function isValidDuration(raw) {
  if (raw === "" || raw === null || raw === undefined) return false;
  const n = Number(raw);
  return !Number.isNaN(n) && n >= 0 && Number.isInteger(n);
}

export function isValidStartLocation(raw) {
  return typeof raw === "string" && raw.trim().length > 0;
}
