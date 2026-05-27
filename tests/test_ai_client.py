"""Tests for src/ai/client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_generate_raises_gemini_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    with pytest.raises(client_mod.GeminiError, match="not configured"):
        client_mod.generate("system", [{"role": "user", "parts": [{"text": "hello"}]}])


def test_generate_raises_gemini_error_on_api_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("quota exceeded")

    with patch("src.ai.client.genai.Client", return_value=mock_client):
        with pytest.raises(client_mod.GeminiError, match="quota exceeded"):
            client_mod.generate("system", [{"role": "user", "parts": [{"text": "hello"}]}])


def test_generate_returns_text_on_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    mock_response = MagicMock()
    mock_response.text = "Delta measures directional exposure."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("src.ai.client.genai.Client", return_value=mock_client):
        result = client_mod.generate("system", [{"role": "user", "parts": [{"text": "What is delta?"}]}])

    assert result == "Delta measures directional exposure."
