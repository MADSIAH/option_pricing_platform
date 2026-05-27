"""Tests for src/ai/client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ai.client import GeminiError, generate


def test_generate_raises_gemini_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiError, match="not configured"):
        generate("system", [{"role": "user", "parts": [{"text": "hello"}]}])


def test_generate_raises_gemini_error_on_api_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("quota exceeded")
    with patch("src.ai.client.genai.Client", return_value=mock_client):
        with pytest.raises(GeminiError, match="quota exceeded"):
            generate("system", [{"role": "user", "parts": [{"text": "hello"}]}])


def test_generate_returns_text_on_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    mock_response = MagicMock()
    mock_response.text = "Delta measures directional exposure."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    with patch("src.ai.client.genai.Client", return_value=mock_client):
        result = generate("system", [{"role": "user", "parts": [{"text": "What is delta?"}]}])
    assert result == "Delta measures directional exposure."
