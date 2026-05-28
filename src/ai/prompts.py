"""Loads system prompt text files into module-level constants."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent / "prompts"

EXPLAIN_SYSTEM_PROMPT = (_DIR / "explain_system.txt").read_text(encoding="utf-8")
CHAT_SYSTEM_PROMPT = (_DIR / "chat_system.txt").read_text(encoding="utf-8")
EXPLAIN_SURFACES_SYSTEM_PROMPT = (_DIR / "explain_surfaces_system.txt").read_text(encoding="utf-8")
