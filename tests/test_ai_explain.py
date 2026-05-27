"""Tests for src/ai/explain.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest


SAMPLE_DATA = {
    "user_level": "finance_student",
    "option_type": "call",
    "style": "european",
    "method": "black_scholes",
    "S": 150.0,
    "K": 155.0,
    "T": 0.5,
    "r": 0.05,
    "sigma": 0.22,
    "q": 0.0,
    "prices": {
        "black_scholes": {
            "price": 4.23,
            "greeks": {
                "delta": 0.42,
                "gamma": 0.05,
                "vega": 0.30,
                "theta": -0.15,
                "rho": 0.10,
            },
        }
    },
}


def test_build_explain_message_contains_key_fields():
    from src.ai.explain import build_explain_message

    msg = build_explain_message(SAMPLE_DATA)

    assert "Finance Student" in msg
    assert "150" in msg
    assert "155" in msg
    assert "call" in msg
    assert "european" in msg
    assert "4.23" in msg
    assert "0.42" in msg
    assert "black_scholes" in msg
    assert "0.5000" in msg   # T
    assert "0.0500" in msg   # r
    assert "0.2200" in msg   # sigma
    assert "0.0000" in msg   # q
    assert "0.0500" in msg   # gamma
    assert "0.3000" in msg   # vega
    assert "-0.1500" in msg  # theta
    assert "0.1000" in msg   # rho


def test_build_explain_message_beginner_label():
    from src.ai.explain import build_explain_message

    data = {**SAMPLE_DATA, "user_level": "beginner"}
    msg = build_explain_message(data)
    assert "Beginner" in msg


def test_build_explain_message_professional_label():
    from src.ai.explain import build_explain_message

    data = {**SAMPLE_DATA, "user_level": "professional"}
    msg = build_explain_message(data)
    assert "Professional" in msg


def test_build_explain_message_unknown_level_falls_back_to_raw_key():
    from src.ai.explain import build_explain_message
    data = {**SAMPLE_DATA, "user_level": "expert"}
    msg = build_explain_message(data)
    assert "expert" in msg


def test_call_explain_calls_generate_with_system_prompt():
    from src.ai.explain import call_explain
    from src.ai.prompts import EXPLAIN_SYSTEM_PROMPT

    with patch("src.ai.explain.generate", return_value="The option is priced at $4.23.") as mock_gen:
        result = call_explain(SAMPLE_DATA)

    mock_gen.assert_called_once()
    args = mock_gen.call_args
    assert args[0][0] == EXPLAIN_SYSTEM_PROMPT
    assert args[0][1][0]["role"] == "user"
    assert result == "The option is priced at $4.23."
