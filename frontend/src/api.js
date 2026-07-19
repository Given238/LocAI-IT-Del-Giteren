const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function postJson(path, payload) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ApiError(
      "Could not reach the LocAI backend. Is the API server running?",
      null,
    );
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    // no JSON body (e.g. a plain 500 with no detail) -- fall through
  }

  if (!res.ok) {
    const detail = body?.detail || body?.message || res.statusText;
    throw new ApiError(detail, res.status);
  }

  return body;
}

export function fetchItinerary(payload) {
  return postJson("/itinerary", payload);
}

export function fetchChat(history, message) {
  return postJson("/chat", { history, message });
}
