import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .itinerary import build_itinerary
from .llm import LLMGenerationError
from .schemas import ItineraryRequest, ItineraryResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LocAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
