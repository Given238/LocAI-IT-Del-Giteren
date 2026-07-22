import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL")

# Comma-separated list of allowed frontend origins. Cookies now carry the
# session (see backend/auth.py), and browsers reject
# "Access-Control-Allow-Origin: *" combined with credentialed requests --
# so this can no longer default to "*" the way it did before auth existed.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
]

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
    "GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"
)
# Where the Google callback redirects back to once a session is set.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Reserved for future cookie-signing/CSRF-token hardening -- the current
# session design (a random opaque token looked up in the sessions table,
# see backend/auth.py) doesn't need it, since forging a session means
# guessing a secrets.token_urlsafe(32) value directly, not forging a
# signature. Not required to start the app.
SESSION_SECRET = os.environ.get("SESSION_SECRET")

# Cookies default to dev-friendly settings (plain HTTP on localhost).
# In production, behind a real domain, set COOKIE_SECURE=true; if the
# frontend and backend end up on genuinely different sites (not just
# different localhost ports, which share a "site" for SameSite purposes),
# set COOKIE_SAMESITE=none (which additionally requires COOKIE_SECURE=true).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")
