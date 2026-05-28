"""Tests for src/ai/explain_surfaces.py."""
from __future__ import annotations

from unittest.mock import patch


SAMPLE_BUCKET = {
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

SAMPLE_DATA = {
    "user_level": "finance_student",
    "ticker": "AAPL",
    "option_type": "call",
    "smile_intensity": 0.12,
    "put_skew": 0.08,
    "deep_itm_bias": -0.15,
    "divergence_threshold": 0.25,
    "buckets": [SAMPLE_BUCKET],
}


def test_message_contains_ticker_and_level():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "AAPL" in msg
    assert "Finance Student" in msg
    assert "call" in msg


def test_message_contains_vol_scalars():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "0.1200" in msg
    assert "0.0800" in msg


def test_message_contains_price_scalars():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "-0.1500" in msg
    assert "0.2500" in msg


def test_message_contains_bucket_row():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "0.25" in msg
    assert "0.90" in msg
    assert "1200" in msg


def test_message_null_deep_itm_bias():
    from src.ai.explain_surfaces import build_surface_explain_message
    data = {**SAMPLE_DATA, "deep_itm_bias": None}
    msg = build_surface_explain_message(data)
    assert "n/a" in msg


def test_call_explain_surfaces_calls_generate():
    from src.ai.explain_surfaces import call_explain_surfaces
    from src.ai.prompts import EXPLAIN_SURFACES_SYSTEM_PROMPT

    with patch("src.ai.explain_surfaces.generate", return_value="Surface looks fine.") as mock_gen:
        result = call_explain_surfaces(SAMPLE_DATA)

    mock_gen.assert_called_once()
    args = mock_gen.call_args[0]
    assert args[0] == EXPLAIN_SURFACES_SYSTEM_PROMPT
    assert args[1][0]["role"] == "user"
    assert result == "Surface looks fine."
