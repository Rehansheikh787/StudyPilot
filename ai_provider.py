"""
ai_provider.py — Unified, reliable AI calling layer for StudyPilot.

Mirrors the reliability pattern used across the rest of the portfolio
(Morning Digest, RupeeRadar, Chief of Staff AI):

    Gemini (primary, schema-locked)
        -> Groq (fallback, JSON-mode + Pydantic validation)
            -> Deterministic local fallback (never blank, never crashes)

Every AI call in StudyPilot should go through generate_structured() so the
app degrades gracefully instead of breaking when a provider is down, rate
limited, or a key is missing.
"""

import os
import re
import sys
import json
from typing import Type, TypeVar, Optional, Callable
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)


# ─── Schemas ──────────────────────────────────────────────────────────

class SyllabusEntry(BaseModel):
    subject: str
    unit: str = ""
    chapters: list[str] = []
    exam_date: str = ""
    weightage: str = ""


class SyllabusList(BaseModel):
    entries: list[SyllabusEntry]


class TimetableSlot(BaseModel):
    subject: str
    duration_minutes: int = 0
    chapters_to_cover: list[str] = []
    notes: str = ""
    exam_date: str = ""


class TimetableDay(BaseModel):
    day: int
    date: str
    slots: list[TimetableSlot] = []
    total_study_minutes: int = 0


class WeeklyTimetable(BaseModel):
    timetable: list[TimetableDay]
    weekly_summary: str = ""


# ─── JSON extraction helper (shared cleanup logic) ───────────────────

def _extract_json_block(raw: str) -> str:
    cleaned = raw.strip()
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()

    start_list = cleaned.find("[")
    start_obj = cleaned.find("{")
    if start_list != -1 and (start_obj == -1 or start_list < start_obj):
        start, end = start_list, cleaned.rfind("]")
    elif start_obj != -1:
        start, end = start_obj, cleaned.rfind("}")
    else:
        start, end = -1, -1

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object/array found in model response.")
    return cleaned[start:end + 1]


def _coerce_to_model(raw_text: str, schema: Type[T]) -> T:
    cleaned = _extract_json_block(raw_text)
    data = json.loads(cleaned)
    # Support both a bare list (e.g. syllabus extraction) and a dict payload
    if isinstance(data, list) and schema is SyllabusList:
        data = {"entries": data}
    return schema.model_validate(data)


# ─── Provider 1: Gemini (schema-locked) ───────────────────────────────

def _try_gemini(prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> Optional[T]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return _coerce_to_model(response.text, schema)
    except Exception as e:
        print(f"[ai_provider] Gemini attempt failed: {e}", file=sys.stderr)
        return None


# ─── Provider 2: Groq (JSON mode + Pydantic validation) ──────────────

def _try_groq(prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> Optional[T]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content
        return _coerce_to_model(raw, schema)
    except (ValidationError, json.JSONDecodeError, ValueError) as e:
        print(f"[ai_provider] Groq response failed schema validation: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ai_provider] Groq attempt failed: {e}", file=sys.stderr)
        return None


# ─── Public entrypoint ─────────────────────────────────────────────────

def generate_structured(
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
    local_fallback_fn: Optional[Callable[[], T]] = None,
) -> tuple[T, str]:
    """
    Attempts Gemini, then Groq, then a deterministic local fallback.
    Returns (validated_result, provider_used) where provider_used is one of
    "gemini", "groq", or "local-fallback" — surfaced in the UI so the user
    knows when a result was degraded.
    """
    result = _try_gemini(prompt, schema, system_prompt)
    if result is not None:
        return result, "gemini"

    result = _try_groq(prompt, schema, system_prompt)
    if result is not None:
        return result, "groq"

    if local_fallback_fn is not None:
        print("[ai_provider] Falling back to local deterministic generation.", file=sys.stderr)
        return local_fallback_fn(), "local-fallback"

    raise RuntimeError(
        "All AI providers failed and no local fallback was available. "
        "Check GEMINI_API_KEY / GROQ_API_KEY in your .env file."
    )
