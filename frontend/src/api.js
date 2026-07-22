const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// credentials: "include" on every call -- harmless for /itinerary and
// /chat (they don't use the session), but required for the session cookie
// to be sent/received at all: frontend (:5173) and backend (:8000) are
// different origins in dev, and browsers never attach cookies cross-origin
// without this.
async function request(method, path, body) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Could not reach the LocAI backend. Is the API server running?",
      null,
    );
  }

  let responseBody = null;
  try {
    responseBody = await res.json();
  } catch {
    // no JSON body (e.g. a plain 500 with no detail, or a 204) -- fall through
  }

  if (!res.ok) {
    const detail = responseBody?.detail || responseBody?.message || res.statusText;
    throw new ApiError(detail, res.status);
  }

  return responseBody;
}

export function fetchItinerary(payload) {
  return request("POST", "/itinerary", payload);
}

export function fetchChat(history, message) {
  return request("POST", "/chat", { history, message });
}

export function apiGet(path) {
  return request("GET", path);
}

export function apiPost(path, body) {
  return request("POST", path, body ?? {});
}

export function apiPut(path, body) {
  return request("PUT", path, body ?? {});
}
