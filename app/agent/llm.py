"""
app/agent/llm.py
----------------
Thin wrapper around Google Gemini (free tier) for structured JSON responses.

Exports:
    ask_llm(prompt: str) -> dict
        Sends a prompt and parses the response as JSON.
        Raises ValueError if the response is not valid JSON.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import google.generativeai as genai


# ── One-time configuration ──────────────────────────────────────────────────

def _configure() -> None:
    """Load API key and configure the Gemini SDK (runs once)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("GEMINI_API_KEY")
        except ImportError:
            pass
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set.  "
            "Add it to your .env file or export it as an environment variable."
        )
    genai.configure(api_key=api_key)


_configure()

# ── Model singleton ─────────────────────────────────────────────────────────
# Using gemini-3.1-flash-lite — fast, supports structured output.

_model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview",
    generation_config=genai.GenerationConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)


# ── Public API ──────────────────────────────────────────────────────────────

def ask_llm(prompt: str) -> dict:
    """
    Send *prompt* to Gemini and return the parsed JSON response.

    The function strips markdown fences (```json ... ```) if present,
    then parses the result as JSON.

    Raises
    ------
    ValueError
        If the response cannot be parsed as valid JSON.
    """
    response = _model.generate_content(prompt)
    raw_text = response.text.strip()

    # Strip markdown code fences that Gemini sometimes wraps around JSON.
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON response:\n{raw_text}"
        ) from exc
