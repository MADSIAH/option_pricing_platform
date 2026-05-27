"""Integration tests for AI endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

EXPLAIN_PAYLOAD = {
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

CHAT_PAYLOAD = {
    "user_level": "beginner",
    "messages": [{"role": "user", "content": "What is delta?"}],
}


def test_explain_returns_explanation():
    with patch("src.api.routes.ai.call_explain", return_value="The call costs $4.23."):
        response = client.post("/api/v1/ai/explain", json=EXPLAIN_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["explanation"] == "The call costs $4.23."


def test_explain_returns_502_on_gemini_error():
    from src.ai.client import GeminiError
    with patch("src.api.routes.ai.call_explain", side_effect=GeminiError("quota exceeded")):
        response = client.post("/api/v1/ai/explain", json=EXPLAIN_PAYLOAD)
    assert response.status_code == 502
    assert "unavailable" in response.json()["error"]


def test_explain_returns_500_on_missing_key():
    from src.ai.client import GeminiError
    with patch("src.api.routes.ai.call_explain", side_effect=GeminiError("GEMINI_API_KEY not configured")):
        response = client.post("/api/v1/ai/explain", json=EXPLAIN_PAYLOAD)
    assert response.status_code == 500
    assert "not configured" in response.json()["error"]


def test_chat_returns_reply():
    with patch("src.api.routes.ai.call_chat", return_value="Delta measures directional exposure."):
        response = client.post("/api/v1/ai/chat", json=CHAT_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["reply"] == "Delta measures directional exposure."


def test_chat_returns_422_on_empty_messages():
    payload = {**CHAT_PAYLOAD, "messages": []}
    response = client.post("/api/v1/ai/chat", json=payload)
    assert response.status_code == 422


def test_chat_returns_502_on_gemini_error():
    from src.ai.client import GeminiError
    with patch("src.api.routes.ai.call_chat", side_effect=GeminiError("model overloaded")):
        response = client.post("/api/v1/ai/chat", json=CHAT_PAYLOAD)
    assert response.status_code == 502
