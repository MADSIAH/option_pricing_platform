"""Handles multi-turn chat calls to Gemini."""
from __future__ import annotations

from src.ai.client import generate
from src.ai.prompts import CHAT_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def call_chat(messages: list[dict], user_level: str) -> str:
    """Send a multi-turn conversation to Gemini and return the reply.

    Args:
        messages: List of {role, content} dicts. role is "user" or "model".
        user_level: One of "beginner", "finance_student", "professional".
    """
    level = _LEVEL_LABELS.get(user_level, user_level)
    contents = [
        {"role": m["role"], "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    contents[-1]["parts"][0]["text"] = f"[User level: {level}]\n{contents[-1]['parts'][0]['text']}"
    return generate(CHAT_SYSTEM_PROMPT, contents)
