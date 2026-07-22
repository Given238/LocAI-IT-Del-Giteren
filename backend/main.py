import logging
import secrets
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import auth, config, db
from .auth_schema import ensure_auth_schema
from .chat import handle_chat
from .itinerary import build_itinerary
from .llm import LLMGenerationError
from .schemas import (
    ChatRequest,
    ChatResponse,
    ItineraryRequest,
    ItineraryResponse,
    LoginRequest,
    MeResponse,
    ProfileData,
    SignupRequest,
    UserOut,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LocAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    ensure_auth_schema()


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite=config.COOKIE_SAMESITE,
        max_age=auth.SESSION_TTL_DAYS * 24 * 3600,
        path="/",
    )


def get_current_user(request: Request) -> Optional[dict]:
    """Optional auth -- returns None for guests, never raises. Chat/voice/
    form/onboarding all stay usable with zero login (see CLAUDE.md: auth is
    additive, not a gate)."""
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    return auth.get_user_from_session(token)


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Real auth gate -- only for endpoints that are meaningless for a
    guest (there's no server-side profile to read/write without an
    account; guests keep using the browser-local profile instead)."""
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return user


@app.get("/health")
def health():
    try:
        conn = db.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        finally:
            conn.close()
        return {"status": "ok", "database": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"database unreachable: {e}")


@app.post("/itinerary", response_model=ItineraryResponse)
def create_itinerary(req: ItineraryRequest):
    try:
        return build_itinerary(req)
    except LLMGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return handle_chat(req)
    except LLMGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Auth -- email/password + Google OAuth, server-side session cookie.
# ---------------------------------------------------------------------------


@app.post("/auth/signup", response_model=UserOut)
def signup(req: SignupRequest, response: Response):
    email = auth.normalize_email(req.email)
    if auth.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = auth.create_user(email=email, password=req.password, display_name=req.display_name)
    _set_session_cookie(response, auth.create_session(user["id"]))
    return user


@app.post("/auth/login", response_model=UserOut)
def login(req: LoginRequest, response: Response):
    user = auth.get_user_by_email(auth.normalize_email(req.email))
    if not user or not auth.verify_password(req.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    _set_session_cookie(response, auth.create_session(user["id"]))
    return UserOut(id=user["id"], email=user["email"], display_name=user["display_name"])


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    auth.delete_session(request.cookies.get(auth.SESSION_COOKIE_NAME))
    response.delete_cookie(auth.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/auth/me", response_model=MeResponse)
def me(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        return MeResponse()
    profile = auth.get_profile(user["id"])
    return MeResponse(user=UserOut(**user), profile=ProfileData(**profile) if profile else None)


@app.put("/auth/profile", response_model=ProfileData)
def update_profile(req: ProfileData, user: dict = Depends(require_user)):
    auth.save_profile(user["id"], req.model_dump())
    return req


@app.get("/auth/config")
def auth_config():
    return {"google_configured": auth.google_oauth_configured()}


@app.get("/auth/google/login")
def google_login():
    if not auth.google_oauth_configured():
        raise HTTPException(status_code=503, detail="Google login isn't configured on this server.")
    state = secrets.token_urlsafe(16)
    redirect = RedirectResponse(auth.google_login_url(state))
    redirect.set_cookie(
        auth.OAUTH_STATE_COOKIE_NAME, state,
        httponly=True, secure=config.COOKIE_SECURE, samesite=config.COOKIE_SAMESITE,
        max_age=600, path="/",
    )
    return redirect


@app.get("/auth/google/callback")
def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    expected_state = request.cookies.get(auth.OAUTH_STATE_COOKIE_NAME)
    if error or not code or not state or state != expected_state:
        return RedirectResponse(f"{config.FRONTEND_URL}/?auth_error=1")

    try:
        userinfo = auth.exchange_google_code(code)
    except auth.AuthError:
        return RedirectResponse(f"{config.FRONTEND_URL}/?auth_error=1")

    google_id = userinfo.get("sub")
    email = auth.normalize_email(userinfo.get("email", ""))
    name = userinfo.get("name")

    user = auth.get_user_by_google_id(google_id)
    if not user:
        existing = auth.get_user_by_email(email)
        if existing:
            auth.link_google_id(existing["id"], google_id)
            user = existing
        else:
            user = auth.create_user(email=email, google_id=google_id, display_name=name)

    redirect = RedirectResponse(config.FRONTEND_URL)
    _set_session_cookie(redirect, auth.create_session(user["id"]))
    redirect.delete_cookie(auth.OAUTH_STATE_COOKIE_NAME, path="/")
    return redirect
