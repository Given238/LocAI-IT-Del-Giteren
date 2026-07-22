from . import db

# Idempotent on purpose (CREATE TABLE IF NOT EXISTS), unlike scripts/etl.py's
# DDL which DROPs and recreates the tourism tables on every run -- users and
# their sessions must never be wiped by re-running the dataset ETL, so this
# lives in its own module and runs once at API startup instead.
DDL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_id TEXT UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    budget NUMERIC,
    duration_nights INT,
    start_location TEXT,
    interests TEXT[],
    locale TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
"""


def ensure_auth_schema():
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        conn.commit()
    finally:
        conn.close()
