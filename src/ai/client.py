"""Gemini API client for the AI features."""
from __future__ import annotations

import os

from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"


class GeminiError(Exception):
    """Raised when the Gemini API call fails or is not configured."""


def generate(system_instruction: str, contents: list[dict]) -> str:
    """Call Gemini and return the response text.

    Raises GeminiError if the API key is missing or the call fails.
    """
    if not API_KEY:
        raise GeminiError("GEMINI_API_KEY not configured")
    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model=MODEL,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            contents=contents,
        )
        return response.text
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(str(exc)) from exc
