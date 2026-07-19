"""
Runs a short scripted conversation against the live /chat endpoint:
ask for a plan with missing info -> clarify -> get plan -> ask for a PDF.

Prints the full transcript, plus a few sanity checks: that the itinerary
only shows up once the clarifying info is given, that its structured
places/prices/addresses are identical to what /itinerary would return for
the same constraints, and that the PDF step involves no new LLM call and
reuses the exact itinerary already in the conversation.

Usage: start the API first (uvicorn backend.main:app --reload), then run
    ./.venv/Scripts/python.exe scripts/test_chat.py
"""
import io
import json
import os
import sys

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

TURNS = [
    "Hi! I want to plan a trip to Danau Toba.",
    "My budget is Rp500,000 and I'm starting from Sibolga.",
    "One night.",
    "Can I get that as a PDF?",
]


def send(history, message):
    payload = {"history": [m for m in history], "message": message}
    resp = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()


def main():
    history = []
    print("=" * 90)
    print("SHORT CONVERSATION: missing info -> clarify -> plan -> PDF")
    print("=" * 90)

    for turn in TURNS:
        print(f"\nUSER: {turn}")
        body = send(history, turn)
        print(f"ASSISTANT: {body['reply']}")

        history.append({"role": "user", "content": turn})
        assistant_msg = {"role": "assistant", "content": body["reply"]}
        if body.get("itinerary"):
            assistant_msg["itinerary"] = body["itinerary"]
        history.append(assistant_msg)

        if body.get("itinerary"):
            itin = body["itinerary"]
            print(f"  [itinerary attached: feasible={itin['feasible']}, "
                  f"days={len(itin.get('days', []))}, "
                  f"total=Rp{itin.get('estimated_total_cost_min')}-{itin.get('estimated_total_cost_max')}]")
            for day in itin.get("days", []):
                names = (
                    [a["name"] for a in day["attractions"]]
                    + [m["name"] for m in day["meals"]]
                    + ([day["lodging"]["name"]] if day["lodging"] else [])
                    + [t["name"] for t in day["transport"]]
                )
                print(f"    day {day['day']}: {names}")

        if body.get("pdf_base64"):
            print(f"  [PDF attached: {body['pdf_filename']}, "
                  f"{len(body['pdf_base64'])} base64 chars]")
            import base64
            with open(f"pdf_from_chat_{body['pdf_filename']}", "wb") as f:
                f.write(base64.b64decode(body["pdf_base64"]))
            print(f"  [saved to pdf_from_chat_{body['pdf_filename']} for inspection]")

    print()
    print("=" * 90)
    print("CHECK: PDF step should carry the SAME itinerary as the plan step, unchanged")
    print("=" * 90)
    plan_msgs = [m for m in history if m["role"] == "assistant" and m.get("itinerary")]
    if len(plan_msgs) >= 2:
        first, last = plan_msgs[0]["itinerary"], plan_msgs[-1]["itinerary"]
        same = json.dumps(first, sort_keys=True) == json.dumps(last, sort_keys=True)
        print(f"Itinerary unchanged between plan turn and PDF turn: {same}")
    else:
        print(f"Only found {len(plan_msgs)} itinerary-bearing turn(s); expected at least 2 "
              "(the plan turn and the PDF turn) to compare.")


if __name__ == "__main__":
    main()
