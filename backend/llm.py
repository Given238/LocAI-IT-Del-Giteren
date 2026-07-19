import json
import re
import time

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from . import config


class LLMGenerationError(Exception):
    pass


def get_client() -> OpenAI:
    if not (config.LLM_API_KEY and config.LLM_BASE_URL and config.LLM_MODEL):
        raise LLMGenerationError(
            "SEA-LION LLM is not configured (missing LLM_API_KEY / LLM_BASE_URL / LLM_MODEL)"
        )
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


def _truncate(text, n=140):
    if not text:
        return None
    text = str(text)
    return text if len(text) <= n else text[:n].rstrip() + "..."


def _candidate_summary(pool):
    return {
        "attractions": [
            {
                "id": a["id"], "name": a["name"], "type": a["place_type"],
                "price_min": a["entry_fee_min"], "price_max": a["entry_fee_max"],
                "rating": a["rating"], "hours": a["operational_hour"],
                "desc": _truncate(a["description"]),
            }
            for a in pool.attractions
        ],
        "hotels": [
            {
                "id": h["id"], "name": h["name"], "price_per_head": h["price_min"],
                "rating": h["rating"], "facilities": _truncate(h["facilities"]),
            }
            for h in pool.hotels
        ],
        "restaurants": [
            {
                "id": r["id"], "name": r["name"],
                "price_per_head_min": r["price_min"], "price_per_head_max": r["price_max"],
                "rating": r["rating"], "menu": _truncate(r["recommend_menu"]),
            }
            for r in pool.restaurants
        ],
        "transport": [
            {
                "id": t["id"], "name": t["transport_name"], "route": t["route_raw"],
                "price_min": t["price_min"], "price_max": t["price_max"],
                "vehicle": t["vehicle_type"], "hours": t["operational_hour"],
            }
            for t in pool.transport
        ],
        "local_food_context": [
            {"id": k["id"], "name": k["name"], "desc": _truncate(k["description"], 100)}
            for k in pool.kuliner
        ],
    }


LOCALE_TONE_INSTRUCTIONS = {
    "indonesian": (
        "Write the summary and every day's narrative in natural, warm Bahasa Indonesia, "
        "in a friendly, conversational travel-guide register."
    ),
    "malaysian": "Write in English with a warm, friendly Malaysian travel-guide tone and register.",
    "singaporean": "Write in English with a clear, efficient, friendly Singaporean travel-guide tone.",
    "filipino": "Write in English with a warm, enthusiastic, welcoming Filipino travel-guide tone.",
    "thai": "Write in English with a gentle, polite, welcoming tone reflecting Thai hospitality.",
    "vietnamese": "Write in English with a warm, practical Vietnamese travel-guide tone.",
}


def _locale_instruction(locale):
    if not locale:
        return None
    return LOCALE_TONE_INSTRUCTIONS.get(locale.strip().lower())


RESPONSE_SHAPE = (
    '{"summary": "2-3 sentence overview of the whole trip, generic, no place names", '
    '"days": [{"day": 1, "attraction_ids": [1, 2], "restaurant_ids": [3], '
    '"hotel_id": 4, "transport_ids": [5], "narrative": '
    '"2-4 sentences of connective/context text for this day, referring to items by '
    'role only, e.g. \'Start with your morning transport, then spend the day at your '
    'first attraction before a second nearby stop. Grab lunch at your chosen restaurant '
    'and settle into your accommodation for the night.\'"}]}'
)


def build_messages(req, pool):
    num_days = req.duration_nights + 1 if req.duration_nights > 0 else 1
    system = (
        "You are a Lake Toba (Danau Toba), North Sumatra trip-planning assistant. "
        "You are given a traveler's constraints and REAL candidate places/services from "
        "a verified database, each with a numeric id. Build a day-by-day itinerary using "
        "ONLY the ids given below -- never invent a place, price, id, or detail that is "
        "not in the candidate lists. If a category has no suitable candidate for a day, "
        "leave that list empty or the field null rather than inventing one. Keep total "
        "estimated spending within the traveler's budget.\n"
        "The actual verified name/price/address of each pick is rendered separately from "
        "your id choices, so the narrative and summary must NOT name, quote, or paraphrase "
        "any specific place, restaurant, hotel, or transport operator -- not even ones from "
        "the candidate lists. Instead, refer to picks generically by their role or order, "
        "e.g. 'your morning transport', 'the first attraction', 'a nearby lunch stop', "
        "'day 2's accommodation'. Use the narrative only for connective tissue, pacing, and "
        "context (why this order, what to expect, time-of-day framing) -- never as the "
        "place a name first appears.\n"
        "Respond with ONLY a single raw JSON object -- no markdown code fences, no "
        f"commentary before or after -- matching exactly this shape:\n{RESPONSE_SHAPE}\n"
        f"Plan exactly {num_days} day(s). Always set hotel_id to null when duration_nights "
        "is 0 (same-day trip, no overnight stay)."
    )
    locale_instruction = _locale_instruction(req.locale)
    if locale_instruction:
        system += (
            f"\nTONE (applies ONLY to the \"summary\" and \"narrative\" text, nothing else): "
            f"{locale_instruction} This is a tone/phrasing instruction only -- it must not "
            "change which ids you choose, how many days you plan, or any numeric/factual "
            "content; those are driven solely by the constraints and candidates above."
        )
    user_payload = {
        "constraints": {
            "budget_idr": req.budget,
            "duration_nights": req.duration_nights,
            "start_location": req.start_location,
            "interests": req.interests,
        },
        "candidates": _candidate_summary(pool),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, default=float)},
    ]


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def generate_itinerary_plan(req, pool, max_attempts=5) -> dict:
    client = get_client()
    messages = build_messages(req, pool)
    backoff = 3
    last_error = None

    for _ in range(max_attempts):
        try:
            resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=2500,
            )
        except RateLimitError as e:
            last_error = e
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue
        except (APIError, APIConnectionError) as e:
            last_error = e
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue

        content = resp.choices[0].message.content or ""
        try:
            return _extract_json(content)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "That was not valid JSON. Reply again with ONLY the JSON object described earlier, nothing else.",
            })
            continue

    raise LLMGenerationError(
        f"SEA-LION did not return a usable itinerary after {max_attempts} attempts: {last_error}"
    )
