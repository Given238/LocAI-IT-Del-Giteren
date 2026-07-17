import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL")

# Comma-separated list of allowed frontend origins, or "*" for any (fine for
# a demo with no auth/cookies -- tighten this once there's a deployed URL).
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")
