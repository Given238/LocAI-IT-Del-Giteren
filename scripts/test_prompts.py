"""
Sends the 5 example prompts from the dataset's "prompt" sheet to the running
/itinerary endpoint and prints each response for manual review.

/itinerary takes structured fields (budget, duration_nights, start_location,
interests), not free text, so each raw prompt below is manually translated
into those fields -- there's no NL-parsing layer in Phase 2. The original
Indonesian text is printed alongside the translation so the mapping is
auditable.

Usage: start the API first (uvicorn backend.main:app --reload), then run
    ./.venv/Scripts/python.exe scripts/test_prompts.py
"""
import io
import json
import os
import sys

import requests

# Some place names in the dataset use Batak script (e.g. "Sopo Guru Tatea
# Bulan | ᯘᯬᯇᯬ..."), which crashes on Windows' default cp1252 console
# encoding. Force UTF-8 stdout so results always print instead of crashing.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

CASES = [
    {
        "raw_prompt": (
            "Saya ingin berlibur ke Danau Toba selama 1 malam. Budget saya sekitar "
            "Rp500.000,-. Saat ini saya berada di Sibolga. Tolong berikan rekomendasi "
            "itinerary yang mencakup tempat wisata, akomodasi, transportasi, dan "
            "kuliner lokal. Harap sesuaikan dengan anggaran dan durasi yang saya miliki."
        ),
        "request": {
            "budget": 500000,
            "duration_nights": 1,
            "start_location": "Sibolga",
            "interests": None,
        },
    },
    {
        "raw_prompt": (
            "Saya ingin liburan ke Samosir. Titik awal keberangkatan saya dari Medan "
            "Amplas. Mohon buatkan itinerary wisata selama 3 hari 2 malam, dengan "
            "estimasi budget Rp 1.500.000 - Rp 2.000.000 per orang. Saya ingin "
            "mengunjungi tempat-tempat wisata populer di Samosir, dan sekitarnya."
        ),
        "request": {
            "budget": 2000000,
            "duration_nights": 2,
            "start_location": "Medan Amplas",
            "interests": None,
        },
    },
    {
        "raw_prompt": (
            "Saya berencana liburan selama 3 hari 2 malam dengan titik keberangkatan "
            "dari Tebing Tinggi, Sumatera Utara. Budget saya sekitar Rp 1.500.000 per "
            "orang, dan saya ingin menjelajahi kawasan selatan Danau Toba selain "
            "Parapat dan Samosir, seperti: Balige (wisata budaya dan kuliner), Huta "
            "Ginjang (spot foto dan view Danau Toba dari ketinggian), Tao Silalahi "
            "(danau yang tenang, cocok untuk healing)"
        ),
        "request": {
            "budget": 1500000,
            "duration_nights": 2,
            "start_location": "Tebing Tinggi",
            "interests": ["culture", "culinary", "nature"],
        },
    },
    {
        "raw_prompt": (
            "Saya mahasiswa Institut Teknologi Del, saya mau refreshing di hari Sabtu. "
            "Berangkat pukul 12.00 hingga pukul 19.00. Kemana saya harus pergi?. Budget "
            "saya sekitar Rp100.000,-. Tolong berikan rekomendasi itinerary yang "
            "mencakup tempat wisata, akomodasi, transportasi, dan kuliner lokal. Harap "
            "sesuaikan dengan anggaran dan durasi yang saya miliki."
        ),
        "request": {
            "budget": 100000,
            "duration_nights": 0,
            "start_location": "Institut Teknologi Del, Laguboti",
            "interests": None,
        },
    },
    {
        "raw_prompt": (
            "Saya mau ke Toba menghadiri wisuda di Institut Teknologi Del. Sehabis "
            "wisuda kami mau jalan jalan di sekitar sebentar tidak sampai bermalam. "
            "Kemana kami harus pergi?. Budget saya sekitar Rp1.000.000,-. Tolong "
            "berikan rekomendasi itinerary yang mencakup tempat wisata, akomodasi, "
            "transportasi, dan kuliner lokal. Harap sesuaikan dengan anggaran dan "
            "durasi yang saya miliki."
        ),
        "request": {
            "budget": 1000000,
            "duration_nights": 0,
            "start_location": "Institut Teknologi Del, Laguboti",
            "interests": None,
        },
    },
]


def main():
    for i, case in enumerate(CASES, start=1):
        print("=" * 90)
        print(f"PROMPT {i}")
        print("=" * 90)
        print("Raw prompt (from dataset):")
        print(f"  {case['raw_prompt']}")
        print()
        print("Translated to structured request:")
        print(f"  {json.dumps(case['request'], ensure_ascii=False)}")
        print()

        try:
            resp = requests.post(f"{API_BASE_URL}/itinerary", json=case["request"], timeout=60)
        except requests.RequestException as e:
            print(f"REQUEST FAILED: {e}")
            print()
            continue

        print(f"HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(json.dumps(body, indent=2, ensure_ascii=False))
        except ValueError:
            print(resp.text)
        print()


if __name__ == "__main__":
    main()
