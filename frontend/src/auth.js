import { apiGet, apiPost, apiPut, ApiError } from "./api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function signup(email, password, displayName) {
  return apiPost("/auth/signup", { email, password, display_name: displayName || null });
}

export function login(email, password) {
  return apiPost("/auth/login", { email, password });
}

export function logout() {
  return apiPost("/auth/logout");
}

// { user: {...} | null, profile: {...} | null } -- null user means guest,
// never throws for that case (session cookie missing/expired is a normal
// state, not an error).
export function getMe() {
  return apiGet("/auth/me");
}

export function saveProfileRemote(profile) {
  return apiPut("/auth/profile", profile);
}

export async function isGoogleLoginAvailable() {
  try {
    const config = await apiGet("/auth/config");
    return Boolean(config?.google_configured);
  } catch {
    return false;
  }
}

export function googleLoginUrl() {
  return `${API_BASE_URL}/auth/google/login`;
}

export { ApiError };
