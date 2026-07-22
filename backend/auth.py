import datetime
import secrets
from urllib.parse import urlencode

import bcrypt
import requests

from . import config, db

SESSION_COOKIE_NAME = "locai_session"
OAUTH_STATE_COOKIE_NAME = "locai_oauth_state"
SESSION_TTL_DAYS = 30

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _user_row_to_dict(row):
    return {"id": row[0], "email": row[1], "display_name": row[2]}


def create_user(email, password=None, google_id=None, display_name=None):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, google_id, display_name) "
            "VALUES (%s, %s, %s, %s) RETURNING id, email, display_name",
            (email, hash_password(password) if password else None, google_id, display_name),
        )
        row = cur.fetchone()
        conn.commit()
        return _user_row_to_dict(row)
    finally:
        conn.close()


def get_user_by_email(email):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, display_name, password_hash FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "display_name": row[2], "password_hash": row[3]}
    finally:
        conn.close()


def get_user_by_google_id(google_id):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, display_name FROM users WHERE google_id = %s", (google_id,))
        row = cur.fetchone()
        return _user_row_to_dict(row) if row else None
    finally:
        conn.close()


def link_google_id(user_id, google_id):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, user_id))
        conn.commit()
    finally:
        conn.close()


def create_session(user_id) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=SESSION_TTL_DAYS)
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO sessions (id, user_id, expires_at) VALUES (%s, %s, %s)", (token, user_id, expires))
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_from_session(token):
    if not token:
        return None
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT u.id, u.email, u.display_name FROM sessions s "
            "JOIN users u ON u.id = s.user_id "
            "WHERE s.id = %s AND s.expires_at > now()",
            (token,),
        )
        row = cur.fetchone()
        return _user_row_to_dict(row) if row else None
    finally:
        conn.close()


def delete_session(token):
    if not token:
        return
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE id = %s", (token,))
        conn.commit()
    finally:
        conn.close()


def get_profile(user_id):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT budget, duration_nights, start_location, interests, locale "
            "FROM user_profiles WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "budget": float(row[0]) if row[0] is not None else None,
            "duration_nights": row[1],
            "start_location": row[2],
            "interests": row[3],
            "locale": row[4],
        }
    finally:
        conn.close()


def save_profile(user_id, profile: dict):
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_profiles (user_id, budget, duration_nights, start_location, interests, locale, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                budget = EXCLUDED.budget,
                duration_nights = EXCLUDED.duration_nights,
                start_location = EXCLUDED.start_location,
                interests = EXCLUDED.interests,
                locale = EXCLUDED.locale,
                updated_at = now()
            """,
            (
                user_id,
                profile.get("budget"),
                profile.get("duration_nights"),
                profile.get("start_location"),
                profile.get("interests"),
                profile.get("locale"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def google_oauth_configured():
    return bool(config.GOOGLE_OAUTH_CLIENT_ID and config.GOOGLE_OAUTH_CLIENT_SECRET)


def google_login_url(state):
    params = {
        "client_id": config.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": config.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_google_code(code):
    """
    Server-side authorization-code exchange -- the client secret never
    leaves the backend (NFR5/NFR10). Raises AuthError on any failure so the
    callback route can turn it into a clean redirect rather than a raw 500.
    """
    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": config.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": config.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": config.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        userinfo_resp = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()
    except (requests.RequestException, KeyError, ValueError) as e:
        raise AuthError(f"Google token exchange failed: {e}")
