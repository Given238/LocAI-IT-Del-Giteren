// Local, browser-scoped stand-in for a real user profile. There is no
// login/signup yet (see CLAUDE.md Next Steps -- it's sequenced right after
// onboarding), so "the user's profile" for now means "this browser's
// stored preferences," not a backend-linked account. Once real auth
// exists, this should migrate to per-account server-side storage (flagged
// in CLAUDE.md) -- the shape here is deliberately identical to
// ItineraryRequest's fields so that migration is a storage-location change,
// not a data-model change.
const STORAGE_KEY = "locai_profile";

export function loadProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveProfile(profile) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...profile, onboarded: true }));
  } catch {
    // Storage unavailable (private browsing, quota, etc.) -- onboarding
    // still works for the current session, it just won't persist.
  }
}

export function hasOnboarded(profile) {
  return Boolean(profile?.onboarded);
}
