"""AI endpoints: explain and chat."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

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


def _gemini_error_response(exc: GeminiError) -> JSONResponse:
    msg = str(exc)
    if "not configured" in msg:
        return JSONResponse(status_code=500, content={"error": "AI service not configured"})
    return JSONResponse(status_code=502, content={"error": "AI service unavailable", "detail": msg})


@router.post("/ai/explain", response_model=ExplainResponse)
def explain(payload: ExplainRequest) -> ExplainResponse | JSONResponse:
    try:
        explanation = call_explain(payload.model_dump())
        return ExplainResponse(explanation=explanation)
    except GeminiError as exc:
        return _gemini_error_response(exc)


@router.post("/ai/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse | JSONResponse:
    try:
        reply = call_chat(
            [m.model_dump() for m in payload.messages],
            payload.user_level.value,
        )
        return ChatResponse(reply=reply)
    except GeminiError as exc:
        return _gemini_error_response(exc)
