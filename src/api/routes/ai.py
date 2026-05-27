"""AI endpoints: explain and chat."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.ai.chat import call_chat
from src.ai.client import GeminiError
from src.ai.explain import call_explain
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    ExplainRequest,
    ExplainResponse,
)

router = APIRouter(tags=["ai"])


def _raise_gemini_error(exc: GeminiError) -> None:
    msg = str(exc)
    if "not configured" in msg:
        raise HTTPException(status_code=500, detail="AI service not configured")
    raise HTTPException(status_code=502, detail=f"AI service unavailable: {msg}")


@router.post("/ai/explain", response_model=ExplainResponse)
def explain(payload: ExplainRequest) -> ExplainResponse:
    try:
        explanation = call_explain(payload.model_dump())
        return ExplainResponse(explanation=explanation)
    except GeminiError as exc:
        _raise_gemini_error(exc)


@router.post("/ai/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        reply = call_chat(
            [m.model_dump() for m in payload.messages],
            payload.user_level.value,
        )
        return ChatResponse(reply=reply)
    except GeminiError as exc:
        _raise_gemini_error(exc)
