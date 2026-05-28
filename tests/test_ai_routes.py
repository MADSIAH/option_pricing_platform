"""Integration tests for AI endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.ai.client import GeminiError
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
    with patch("src.api.routes.ai.call_explain", side_effect=GeminiError("quota exceeded")):
        response = client.post("/api/v1/ai/explain", json=EXPLAIN_PAYLOAD)
    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]


def test_explain_returns_500_on_missing_key():
    with patch("src.api.routes.ai.call_explain", side_effect=GeminiError("GEMINI_API_KEY not configured")):
        response = client.post("/api/v1/ai/explain", json=EXPLAIN_PAYLOAD)
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]


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
    with patch("src.api.routes.ai.call_chat", side_effect=GeminiError("model overloaded")):
        response = client.post("/api/v1/ai/chat", json=CHAT_PAYLOAD)
    assert response.status_code == 502


SURFACE_EXPLAIN_PAYLOAD = {
    "user_level": "finance_student",
    "ticker": "AAPL",
    "option_type": "call",
    "smile_intensity": 0.12,
    "put_skew": 0.08,
    "deep_itm_bias": -0.15,
    "divergence_threshold": 0.25,
    "buckets": [
        {
            "t_label": "0.25–0.50",
            "m_label": "0.90–1.00",
            "spike_count": 2,
            "mean_signed_div": 0.05,
            "mean_abs_div": 0.08,
            "pct_large_div": 0.03,
            "count_large_div": 1,
            "volume": 1200,
            "open_interest": 5000,
        }
    ],
}


def test_explain_surfaces_returns_explanation():
    with patch("src.api.routes.ai.call_explain_surfaces", return_value="Surface looks healthy."):
        response = client.post("/api/v1/ai/explain_surfaces", json=SURFACE_EXPLAIN_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["explanation"] == "Surface looks healthy."


def test_explain_surfaces_returns_502_on_gemini_error():
    with patch("src.api.routes.ai.call_explain_surfaces", side_effect=GeminiError("quota")):
        response = client.post("/api/v1/ai/explain_surfaces", json=SURFACE_EXPLAIN_PAYLOAD)
    assert response.status_code == 502


def test_explain_surfaces_returns_422_on_missing_field():
    payload = {**SURFACE_EXPLAIN_PAYLOAD}
    del payload["smile_intensity"]
    response = client.post("/api/v1/ai/explain_surfaces", json=payload)
    assert response.status_code == 422
