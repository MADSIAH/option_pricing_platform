"""Tests for src/ai/chat.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest


MESSAGES = [
    {"role": "user", "content": "What is delta?"},
    {"role": "model", "content": "Delta measures directional exposure."},
    {"role": "user", "content": "And gamma?"},
]


def test_call_chat_injects_level_into_last_user_turn():
    from src.ai.chat import call_chat

    with patch("src.ai.chat.generate", return_value="Gamma is the rate of change of delta.") as mock_gen:
        call_chat(MESSAGES, "beginner")

    contents = mock_gen.call_args[0][1]
    last_text = contents[-1]["parts"][0]["text"]
    assert "[User level: Beginner]" in last_text
    assert "And gamma?" in last_text


def test_call_chat_does_not_modify_earlier_turns():
    from src.ai.chat import call_chat

    with patch("src.ai.chat.generate", return_value="ok") as mock_gen:
        call_chat(MESSAGES, "finance_student")

    contents = mock_gen.call_args[0][1]
    assert contents[0]["parts"][0]["text"] == "What is delta?"
    assert contents[1]["parts"][0]["text"] == "Delta measures directional exposure."


def test_call_chat_uses_chat_system_prompt():
    from src.ai.chat import call_chat
    from src.ai.prompts import CHAT_SYSTEM_PROMPT

    with patch("src.ai.chat.generate", return_value="ok") as mock_gen:
        call_chat(MESSAGES, "professional")

    assert mock_gen.call_args[0][0] == CHAT_SYSTEM_PROMPT


def test_call_chat_returns_reply():
    from src.ai.chat import call_chat

    with patch("src.ai.chat.generate", return_value="Gamma accelerates delta."):
        result = call_chat(MESSAGES, "finance_student")

    assert result == "Gamma accelerates delta."
