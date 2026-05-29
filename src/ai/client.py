"""Gemini API client for the AI features."""
from __future__ import annotations

import os

from google import genai
from google.genai import types

MODEL = "gemini-3.1-flash-lite"
MODEL_SURFACES = "gemini-2.5-flash"


class GeminiError(Exception):
    """Raised when the Gemini API call fails or is not configured."""


def generate(system_instruction: str, contents: list[dict], model: str = MODEL) -> str:
    """Call Gemini and return the response text.

    Raises GeminiError if the API key is missing or the call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY not configured")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            contents=contents,
        )
        return response.text
    except Exception as exc:
        raise GeminiError(str(exc)) from exc
