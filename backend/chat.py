import ast
import base64
import re

from pydantic import ValidationError

from .itinerary import build_itinerary
from .llm import LLMGenerationError, complete_with_retry, get_client
from .pdf_export import build_itinerary_pdf
from .schemas import ChatResponse, ItineraryRequest

TOOL_NAME = "generate_itinerary"

# Gemma-SEA-LION-v4-27B-IT (our configured LLM_MODEL) doesn't have native
# structured tool_calls -- per docs.sea-lion.ai/guides/tool_calling it emits
# a fenced ```tool_code``` block containing a Python-style call instead.
# There's no v4.5 model documented; v3-70B has real tool_calls but we stay
# on v4-27B for consistency with the rest of the app.
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Generate a verified, budget-grounded Danau Toba (Lake Toba) trip itinerary. "
            "Runs a real pipeline: SQL-filtered database candidates, then ranking/narration, "
            "then every fact re-verified against the database. Only call this once you know "
            "the traveler's budget, trip duration, and starting location -- never guess them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "budget": {"type": "number", "description": "Total trip budget in Indonesian Rupiah (IDR)"},
                "duration_nights": {
                    "type": "integer",
                    "description": "Nights away; 0 for a same-day trip with no overnight stay",
                },
                "start_location": {
                    "type": "string",
                    "description": "Where the traveler is starting from, e.g. a city or town name",
                },
                "interests": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["nature", "culture", "spiritual", "recreation", "culinary", "business"],
                    },
                    "description": "Optional interest categories",
                },
                "locale": {
                    "type": "string",
                    "enum": ["indonesian", "malaysian", "singaporean", "filipino", "thai", "vietnamese"],
                    "description": "Optional SEA locale for narrative tone only -- never affects facts",
                },
            },
            "required": ["budget", "duration_nights", "start_location"],
        },
    },
}

SYSTEM_PROMPT = (
    "You are LocAI's trip-planning chat assistant for Lake Toba (Danau Toba), North Sumatra.\n"
    "You have exactly one tool, generate_itinerary. It runs a verified pipeline (SQL-filtered "
    "real database candidates, ranking, then every fact re-checked against the database) and "
    "returns a grounded itinerary. You have no place data of your own -- the only way to get a "
    "real answer is to call this tool.\n"
    "Behavior:\n"
    "- If the user wants a trip plan and you already have their budget, trip duration (nights; "
    "0 means a same-day trip), and starting location, call generate_itinerary with those values "
    "(plus interests/locale only if they mentioned them).\n"
    "- If ANY of budget, duration, or starting location is missing, do NOT call the tool and do "
    "NOT guess a default. Ask a short, specific question for exactly what's missing instead.\n"
    "- If the user is just chatting, greeting you, or asking something unrelated to trip "
    "planning, reply briefly and naturally in plain text -- don't call the tool.\n"
    "- Never invent place names, prices, or facts about Danau Toba yourself. Every factual claim "
    "must come from a generate_itinerary call, not from you.\n"
    "To call the tool, respond with ONLY this exact format and nothing else (omit interests/"
    "locale entirely if not mentioned):\n"
    "```tool_code\n"
    'generate_itinerary(budget=500000, duration_nights=1, start_location="Sibolga")\n'
    "```\n"
    "Otherwise, just reply in plain conversational text."
)

_TOOL_CODE_RE = re.compile(r"```tool_code\s*\n(.*?)```", re.DOTALL)


def _extract_tool_call(content):
    """
    Parses Gemma-SEA-LION's text-based tool-call convention safely: only
    ast.literal_eval (no eval()) is used on the arguments, and anything that
    doesn't parse as exactly a call to TOOL_NAME with keyword args is
    rejected -- falling back to treating the content as a plain reply rather
    than guessing at a malformed call.
    """
    if not content:
        return None
    match = _TOOL_CODE_RE.search(content)
    if not match:
        return None
    code = match.group(1).strip()
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError:
        return None
    if not isinstance(tree.body, ast.Call):
        return None
    call = tree.body
    if getattr(call.func, "id", None) != TOOL_NAME:
        return None
    if call.args:
        return None  # only keyword args are supported/expected
    kwargs = {}
    for kw in call.keywords:
        if kw.arg is None:
            return None
        try:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
        except Exception:
            return None
    return kwargs


def _messages_for_llm(history, message):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        msgs.append({"role": m.role, "content": m.content})
    msgs.append({"role": "user", "content": message})
    return msgs


def _last_itinerary(history):
    for m in reversed(history):
        if m.role == "assistant" and m.itinerary is not None:
            return m.itinerary
    return None


_PDF_REQUEST_RE = re.compile(r"\b(pdf|download|export)\b", re.IGNORECASE)


def _looks_like_pdf_request(message):
    return bool(_PDF_REQUEST_RE.search(message))


def handle_chat(req) -> ChatResponse:
    if _looks_like_pdf_request(req.message):
        itinerary = _last_itinerary(req.history)
        if itinerary is not None and itinerary.feasible:
            pdf_bytes, filename = build_itinerary_pdf(itinerary)
            return ChatResponse(
                reply="Here's your itinerary as a PDF -- no need to regenerate anything, it's the same plan from above.",
                itinerary=itinerary,
                pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
                pdf_filename=filename,
            )
        # No verified itinerary in history yet -- fall through to a normal
        # LLM turn so it can ask for trip details instead of silently failing.

    client = get_client()
    messages = _messages_for_llm(req.history, req.message)
    content = complete_with_retry(
        client, messages, lambda c: c, retry_prompt="",
        max_attempts=4, temperature=0.3, max_tokens=800,
    )

    tool_args = _extract_tool_call(content)
    if tool_args is None:
        return ChatResponse(reply=content.strip())

    try:
        itinerary_req = ItineraryRequest(**tool_args)
    except ValidationError:
        return ChatResponse(
            reply="I need a valid budget, trip length (in nights), and starting location to "
            "plan this -- could you share those?"
        )

    try:
        itinerary = build_itinerary(itinerary_req)
    except LLMGenerationError:
        return ChatResponse(
            reply="I'm having trouble generating that itinerary right now -- please try again in a moment."
        )

    if not itinerary.feasible:
        return ChatResponse(reply=itinerary.message or "I couldn't find anything that fits those constraints.",
                             itinerary=itinerary)

    reply = itinerary.summary or "Here's your itinerary:"
    return ChatResponse(reply=reply, itinerary=itinerary)
