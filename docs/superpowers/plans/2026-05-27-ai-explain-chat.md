# AI Explain & Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Gemini-powered Explain button (interprets a pricing result) and a Chat panel (free-form options Q&A) to the Option Pricing Platform.

**Architecture:** A new `src/ai/` package holds the Gemini client, system prompts (plain `.txt` files), and one pure function each for explain and chat. A thin `src/api/routes/ai.py` file exposes two endpoints. The frontend adds an explain section to `PriceDisplay.vue` and a new `ChatPanel.vue` slide-in sidebar toggled from `NavBar.vue`.

**Tech Stack:** Python `google-generativeai`, FastAPI, Pydantic, Vue 3, Tailwind CSS.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/ai/__init__.py` | Package marker |
| Create | `src/ai/client.py` | Gemini API wrapper; reads `GEMINI_API_KEY` from env |
| Create | `src/ai/prompts.py` | Loads `.txt` files into module-level constants |
| Create | `src/ai/prompts/explain_system.txt` | Explain system prompt (stub — to be replaced) |
| Create | `src/ai/prompts/chat_system.txt` | Chat system prompt (on-topic guard, no recommendations) |
| Create | `src/ai/explain.py` | `build_explain_message()` + `call_explain()` |
| Create | `src/ai/chat.py` | `call_chat()` |
| Create | `src/api/routes/ai.py` | `POST /ai/explain`, `POST /ai/chat` |
| Modify | `src/api/schemas.py` | Add `UserLevel`, `ExplainRequest/Response`, `ChatMessage`, `ChatRequest/Response` |
| Modify | `src/api/routes/__init__.py` | Export `ai_router` |
| Modify | `src/api/main.py` | Register `ai_router` |
| Modify | `requirements.txt` | Add `google-generativeai` |
| Create | `tests/test_ai_client.py` | Tests for `GeminiError` on missing key and API failure |
| Create | `tests/test_ai_explain.py` | Tests for `build_explain_message` and `call_explain` |
| Create | `tests/test_ai_chat.py` | Tests for `call_chat` level injection |
| Create | `tests/test_ai_routes.py` | Integration tests for both endpoints via `TestClient` |
| Create | `frontend/src/components/ChatPanel.vue` | Slide-in chat sidebar |
| Modify | `frontend/src/components/PriceDisplay.vue` | Add explain section |
| Modify | `frontend/src/components/NavBar.vue` | Add "Ask AI" toggle button |
| Modify | `frontend/src/App.vue` | Add `chatOpen` ref, pass to `NavBar` + `ChatPanel` |
| Modify | `frontend/src/lib/api.js` | Add `explainResult()`, `sendChat()` |

---

## Task 1: Add dependency and scaffold `src/ai/`

**Files:**
- Modify: `requirements.txt`
- Create: `src/ai/__init__.py`
- Create: `src/ai/prompts/explain_system.txt`
- Create: `src/ai/prompts/chat_system.txt`

- [ ] **Step 1: Add `google-generativeai` to requirements**

Open `requirements.txt` and append:
```
google-generativeai
```

- [ ] **Step 2: Install the new dependency**

```bash
pip install google-generativeai
```
Expected: package installs without error.

- [ ] **Step 3: Create `src/ai/__init__.py`**

```python
```
(Empty file — marks `src/ai` as a Python package.)

- [ ] **Step 4: Create `src/ai/prompts/` directory and `explain_system.txt` stub**

Create `src/ai/prompts/explain_system.txt` with this stub (will be replaced with the real prompt):
```
You are an educational options pricing assistant. You will receive option pricing results including prices and Greeks (delta, gamma, vega, theta, rho). Explain the results clearly and accurately, adapting your depth and language to the user level indicated at the start of the message. Do not make buy or sell recommendations of any kind.
```

- [ ] **Step 5: Create `src/ai/prompts/chat_system.txt`**

Create `src/ai/prompts/chat_system.txt`:
```
You are an educational assistant specialising in options pricing. Your knowledge covers:
- Options theory: calls, puts, moneyness, payoff profiles, put-call parity
- Pricing models: Black-Scholes, Monte Carlo simulation, Cox-Ross-Rubinstein binomial tree, Barone-Adesi-Whaley, Longstaff-Schwartz
- Greeks: delta, gamma, vega, theta, rho — their meaning, behaviour, and use in risk management
- Implied volatility, volatility surface, volatility smile and term structure

Adapt your response to the user level indicated in square brackets at the start of each message:
- Beginner: plain language, no formulas, focus on intuition and real-world meaning
- Finance Student: standard financial terminology, include key formulas where helpful, explain assumptions
- Professional: concise, assume deep domain knowledge, focus on nuance and edge cases

Rules:
- Never make buy or sell recommendations of any kind
- Never advise on specific trading positions or strategies
- If asked about topics outside options pricing (general stocks, crypto, macroeconomics, programming, etc.), respond: "I'm focused on options pricing and related topics. Is there something about options, Greeks, or pricing models I can help with?"
- Stay factual and educational at all times
```

- [ ] **Step 6: Commit scaffold**

```bash
git add requirements.txt src/ai/
git commit -m "feat: scaffold src/ai package with prompt files"
```

---

## Task 2: `src/ai/client.py` — Gemini wrapper

**Files:**
- Create: `src/ai/client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai_client.py`:
```python
"""Tests for src/ai/client.py."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


def test_generate_raises_gemini_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Re-import so the module-level API_KEY re-reads the env
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    with pytest.raises(client_mod.GeminiError, match="not configured"):
        client_mod.generate("system", [{"role": "user", "parts": ["hello"]}])


def test_generate_raises_gemini_error_on_api_failure(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("quota exceeded")

    with patch("src.ai.client.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        with pytest.raises(client_mod.GeminiError, match="quota exceeded"):
            client_mod.generate("system", [{"role": "user", "parts": ["hello"]}])


def test_generate_returns_text_on_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    import importlib
    import src.ai.client as client_mod
    importlib.reload(client_mod)

    mock_response = MagicMock()
    mock_response.text = "Delta measures directional exposure."
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("src.ai.client.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        result = client_mod.generate("system", [{"role": "user", "parts": ["What is delta?"]}])

    assert result == "Delta measures directional exposure."
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ai_client.py -v
```
Expected: all three tests fail with `ModuleNotFoundError` or `ImportError` (module not created yet).

- [ ] **Step 3: Implement `src/ai/client.py`**

```python
"""Gemini API client for the AI features."""
from __future__ import annotations

import os

import google.generativeai as genai

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-2.0-flash"


class GeminiError(Exception):
    """Raised when the Gemini API call fails or is not configured."""


def generate(system_instruction: str, contents: list[dict]) -> str:
    """Call Gemini and return the response text.

    Args:
        system_instruction: The system prompt text.
        contents: List of {role, parts} dicts representing the conversation.

    Raises:
        GeminiError: If the API key is missing or the API call fails.
    """
    if not API_KEY:
        raise GeminiError("GEMINI_API_KEY not configured")
    genai.configure(api_key=API_KEY)
    try:
        model = genai.GenerativeModel(MODEL, system_instruction=system_instruction)
        response = model.generate_content(contents)
        return response.text
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(str(exc)) from exc
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_ai_client.py -v
```
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ai/client.py tests/test_ai_client.py
git commit -m "feat: add Gemini client wrapper with GeminiError"
```

---

## Task 3: `src/ai/prompts.py` and `src/ai/explain.py`

**Files:**
- Create: `src/ai/prompts.py`
- Create: `src/ai/explain.py`
- Create: `tests/test_ai_explain.py`

- [ ] **Step 1: Create `src/ai/prompts.py`**

```python
"""Loads system prompt text files into module-level constants."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent / "prompts"

EXPLAIN_SYSTEM_PROMPT = (_DIR / "explain_system.txt").read_text(encoding="utf-8")
CHAT_SYSTEM_PROMPT = (_DIR / "chat_system.txt").read_text(encoding="utf-8")
```

- [ ] **Step 2: Write failing tests for `explain.py`**

Create `tests/test_ai_explain.py`:
```python
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
    assert "150" in msg       # S
    assert "155" in msg       # K
    assert "call" in msg
    assert "european" in msg
    assert "4.23" in msg      # price
    assert "0.42" in msg      # delta
    assert "black_scholes" in msg


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


def test_call_explain_calls_generate_with_system_prompt():
    from src.ai.explain import call_explain
    from src.ai.prompts import EXPLAIN_SYSTEM_PROMPT

    with patch("src.ai.explain.generate", return_value="The option is priced at $4.23.") as mock_gen:
        result = call_explain(SAMPLE_DATA)

    mock_gen.assert_called_once()
    args = mock_gen.call_args
    assert args[0][0] == EXPLAIN_SYSTEM_PROMPT     # system_instruction
    assert args[0][1][0]["role"] == "user"          # single user turn
    assert result == "The option is priced at $4.23."
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ai_explain.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.ai.explain'`.

- [ ] **Step 4: Implement `src/ai/explain.py`**

```python
"""Builds the explain prompt and calls Gemini for pricing result explanations."""
from __future__ import annotations

from src.ai.client import generate
from src.ai.prompts import EXPLAIN_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def build_explain_message(data: dict) -> str:
    """Serialise a pricing result dict into a structured user-turn message."""
    level = _LEVEL_LABELS.get(data["user_level"], data["user_level"])

    price_lines = []
    for method, output in data["prices"].items():
        g = output["greeks"]
        price_lines.append(
            f"  {method}:\n"
            f"    price  = {output['price']:.4f}\n"
            f"    delta  = {g['delta']:.4f}\n"
            f"    gamma  = {g['gamma']:.4f}\n"
            f"    vega   = {g['vega']:.4f}\n"
            f"    theta  = {g['theta']:.4f}\n"
            f"    rho    = {g['rho']:.4f}"
        )

    return (
        f"User level: {level}\n\n"
        f"Option parameters:\n"
        f"  Type:              {data['option_type']} ({data['style']})\n"
        f"  Spot price (S):    {data['S']}\n"
        f"  Strike (K):        {data['K']}\n"
        f"  Time to expiry (T):{data['T']:.4f} years\n"
        f"  Risk-free rate (r):{data['r']:.4f}\n"
        f"  Volatility (σ):    {data['sigma']:.4f}\n"
        f"  Dividend yield (q):{data['q']:.4f}\n\n"
        f"Pricing results:\n" + "\n".join(price_lines) + "\n\n"
        f"Active method: {data['method']}\n\n"
        "Please explain these results."
    )


def call_explain(data: dict) -> str:
    """Generate a plain-language explanation for the given pricing result."""
    message = build_explain_message(data)
    return generate(EXPLAIN_SYSTEM_PROMPT, [{"role": "user", "parts": [message]}])
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_ai_explain.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ai/prompts.py src/ai/explain.py tests/test_ai_explain.py
git commit -m "feat: add prompts loader and explain logic"
```

---

## Task 4: `src/ai/chat.py`

**Files:**
- Create: `src/ai/chat.py`
- Create: `tests/test_ai_chat.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai_chat.py`:
```python
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
    # Last turn is user, should have level prefix
    last_parts = contents[-1]["parts"][0]
    assert "[User level: Beginner]" in last_parts
    assert "And gamma?" in last_parts


def test_call_chat_does_not_modify_earlier_turns():
    from src.ai.chat import call_chat

    with patch("src.ai.chat.generate", return_value="ok") as mock_gen:
        call_chat(MESSAGES, "finance_student")

    contents = mock_gen.call_args[0][1]
    assert contents[0]["parts"][0] == "What is delta?"
    assert contents[1]["parts"][0] == "Delta measures directional exposure."


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ai_chat.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.ai.chat'`.

- [ ] **Step 3: Implement `src/ai/chat.py`**

```python
"""Handles multi-turn chat calls to Gemini."""
from __future__ import annotations

from src.ai.client import generate
from src.ai.prompts import CHAT_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def call_chat(messages: list[dict], user_level: str) -> str:
    """Send a multi-turn conversation to Gemini and return the reply.

    Args:
        messages: List of {role, content} dicts. role is "user" or "model".
        user_level: One of "beginner", "finance_student", "professional".
    """
    level = _LEVEL_LABELS.get(user_level, user_level)
    contents = [{"role": m["role"], "parts": [m["content"]]} for m in messages]
    contents[-1]["parts"][0] = f"[User level: {level}]\n{contents[-1]['parts'][0]}"
    return generate(CHAT_SYSTEM_PROMPT, contents)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_ai_chat.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ai/chat.py tests/test_ai_chat.py
git commit -m "feat: add chat logic with level injection"
```

---

## Task 5: Schema additions

**Files:**
- Modify: `src/api/schemas.py`

- [ ] **Step 1: Add new schemas to `src/api/schemas.py`**

Open `src/api/schemas.py`. After the existing `GreeksProfileResponse` class (end of file), add:

```python
# ── AI feature schemas ─────────────────────────────────────────────────────

from typing import Literal


class UserLevel(str, Enum):
    beginner = "beginner"
    finance_student = "finance_student"
    professional = "professional"


class ExplainRequest(BaseModel):
    user_level: UserLevel
    option_type: OptionType
    style: OptionStyle
    method: str
    S: float
    K: float
    T: float
    r: float
    sigma: float
    q: float
    prices: dict[str, PriceModelOutput]


class ExplainResponse(BaseModel):
    explanation: str


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    user_level: UserLevel
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
```

Note: `Literal` must be imported. Add it to the existing imports at the top of `schemas.py`:

```python
from typing import Literal
```

- [ ] **Step 2: Verify schemas parse correctly**

```bash
python -c "from src.api.schemas import ExplainRequest, ChatRequest, ChatResponse; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/api/schemas.py
git commit -m "feat: add AI request/response schemas"
```

---

## Task 6: `src/api/routes/ai.py` and route tests

**Files:**
- Create: `src/api/routes/ai.py`
- Create: `tests/test_ai_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_ai_routes.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ai_routes.py -v
```
Expected: tests fail because `/api/v1/ai/explain` and `/api/v1/ai/chat` return 404 (routes not registered yet).

- [ ] **Step 3: Implement `src/api/routes/ai.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect most to pass, 404s should be gone (routes not wired yet is OK for now)**

```bash
python -m pytest tests/test_ai_routes.py -v
```
The tests will still fail because the router is not registered in `main.py` yet. That happens in Task 7.

- [ ] **Step 5: Commit the route file**

```bash
git add src/api/routes/ai.py tests/test_ai_routes.py
git commit -m "feat: add AI route handlers for explain and chat"
```

---

## Task 7: Wire routes into the app

**Files:**
- Modify: `src/api/routes/__init__.py`
- Modify: `src/api/main.py`

- [ ] **Step 1: Export `ai_router` from `src/api/routes/__init__.py`**

Replace the contents of `src/api/routes/__init__.py` with:
```python
"""Route modules for Spec C API."""

from .ai import router as ai_router
from .health import router as health_router
from .market import router as market_router
from .pricing import router as pricing_router
from .surface import router as surface_router

__all__ = [
    "ai_router",
    "health_router",
    "market_router",
    "pricing_router",
    "surface_router",
]
```

- [ ] **Step 2: Register the AI router in `src/api/main.py`**

Open `src/api/main.py`. Add `ai_router` to the import and add the `include_router` call:

```python
"""FastAPI entrypoint for Spec C API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import ai_router, health_router, market_router, pricing_router, surface_router
from src.data.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Option Pricing Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(surface_router, prefix="/api/v1")
app.include_router(pricing_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
```

- [ ] **Step 3: Run all AI route tests — they should now pass**

```bash
python -m pytest tests/test_ai_routes.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 4: Run the full test suite to check for regressions**

```bash
python -m pytest tests/ -v
```
Expected: all existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/__init__.py src/api/main.py
git commit -m "feat: register AI router in FastAPI app"
```

---

## Task 8: Frontend — `lib/api.js` additions

**Files:**
- Modify: `frontend/src/lib/api.js`

- [ ] **Step 1: Add `explainResult` and `sendChat` to `frontend/src/lib/api.js`**

Open `frontend/src/lib/api.js` and append the two functions at the end of the file:

```js
export async function explainResult(payload) {
  const res = await fetch(`${BASE}/ai/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.error || `Explain failed: ${res.status}`)
  }
  return res.json() // { explanation: string }
}

export async function sendChat(messages, userLevel) {
  const res = await fetch(`${BASE}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, user_level: userLevel }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.error || `Chat failed: ${res.status}`)
  }
  return res.json() // { reply: string }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "feat: add explainResult and sendChat to frontend API client"
```

---

## Task 9: Frontend — `PriceDisplay.vue` explain section

**Files:**
- Modify: `frontend/src/components/PriceDisplay.vue`

- [ ] **Step 1: Add explain section to `PriceDisplay.vue`**

Replace the entire contents of `frontend/src/components/PriceDisplay.vue` with:

```vue
<script setup>
import { ref } from 'vue'
import { explainResult } from '../lib/api.js'

const props = defineProps({
  result:  { type: Object,  default: null },
  inputs:  { type: Object,  required: true },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})

const METHOD_LABELS = {
  black_scholes:      'Black-Scholes',
  monte_carlo:        'Monte Carlo',
  binomial_tree:      'Binomial Tree',
  baw:                'BAW',
  longstaff_schwartz: 'Longstaff-Schwartz',
}

const LEVELS = [
  { key: 'beginner',        label: 'Beginner' },
  { key: 'finance_student', label: 'Student' },
  { key: 'professional',    label: 'Professional' },
]

const explainLevel    = ref('finance_student')
const explanation     = ref(null)
const explainLoading  = ref(false)
const explainError    = ref(null)

async function runExplain() {
  if (!props.result) return
  explainLoading.value = true
  explainError.value   = null
  explanation.value    = null
  try {
    const payload = {
      user_level:  explainLevel.value,
      option_type: 'call',
      style:       props.result.style,
      method:      props.result.method,
      S:           props.inputs.S,
      K:           props.inputs.K,
      T:           props.inputs.T / 365,
      r:           props.inputs.r / 100,
      sigma:       props.inputs.sigma / 100,
      q:           props.inputs.q / 100,
      prices: {
        [props.result.method]: {
          price: props.result.call.price,
          greeks: {
            delta: props.result.call.delta,
            gamma: props.result.call.gamma,
            vega:  props.result.call.vega,
            theta: props.result.call.theta,
            rho:   props.result.call.rho,
          },
        },
      },
    }
    const data = await explainResult(payload)
    explanation.value = data.explanation
  } catch (e) {
    explainError.value = e.message
  } finally {
    explainLoading.value = false
  }
}

function fmt6(val) {
  if (val == null || isNaN(val)) return '—'
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function moneynessBadge(S, K, isCall) {
  if (!S || !K) return null
  const ratio = S / K
  const atm = Math.abs(ratio - 1) <= 0.005
  if (atm) return { label: 'ATM', cls: 'text-blue-400' }
  const itm = isCall ? ratio > 1 : ratio < 1
  return itm ? { label: 'ITM', cls: 'text-emerald-400' } : { label: 'OTM', cls: 'text-slate-500' }
}
</script>

<template>
  <div class="card">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">Option Prices</h2>
      <div v-if="result" class="flex items-center gap-2">
        <span class="text-[10px] font-semibold border border-blue-800/60 bg-blue-900/20 text-blue-300 rounded-full px-2.5 py-0.5 capitalize">
          {{ result.style }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-28 gap-2 text-slate-500 text-sm">
      <span class="w-2 h-2 rounded-full bg-violet-400 animate-pulse"></span>
      Computing…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex items-center justify-center h-28 text-rose-400 text-sm px-4 text-center">
      {{ error }}
    </div>

    <template v-else-if="result">

      <!-- Primary price cards (selected method) -->
      <div class="grid grid-cols-2 gap-4 mb-5">

        <!-- Call -->
        <div class="bg-slate-950 rounded-xl border border-emerald-900/40 p-4 sm:p-5">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold text-emerald-500 uppercase tracking-widest">Call</span>
            <span v-if="moneynessBadge(inputs.S, inputs.K, true)"
              :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, true).cls]">
              {{ moneynessBadge(inputs.S, inputs.K, true).label }}
            </span>
          </div>
          <div class="text-xl sm:text-2xl font-mono font-bold text-emerald-400 leading-none">
            ${{ fmt6(result.call.price) }}
          </div>
          <div class="mt-1.5 text-[10px] text-violet-400 font-semibold">
            {{ METHOD_LABELS[result.method] }}
          </div>
        </div>

        <!-- Put -->
        <div class="bg-slate-950 rounded-xl border border-rose-900/40 p-4 sm:p-5">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold text-rose-500 uppercase tracking-widest">Put</span>
            <span v-if="moneynessBadge(inputs.S, inputs.K, false)"
              :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, false).cls]">
              {{ moneynessBadge(inputs.S, inputs.K, false).label }}
            </span>
          </div>
          <div class="text-xl sm:text-2xl font-mono font-bold text-rose-400 leading-none">
            ${{ fmt6(result.put.price) }}
          </div>
          <div class="mt-1.5 text-[10px] text-violet-400 font-semibold">
            {{ METHOD_LABELS[result.method] }}
          </div>
        </div>

      </div>

      <!-- Method comparison table -->
      <div class="border-t border-slate-800 pt-4">
        <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold mb-3">Method Comparison</p>
        <table class="w-full text-xs">
          <thead>
            <tr class="text-[10px] text-slate-600 uppercase tracking-wider">
              <th class="text-left font-semibold pb-2 pr-4">Method</th>
              <th class="text-right font-semibold pb-2 pr-4">Call</th>
              <th class="text-right font-semibold pb-2">Put</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(prices, mKey) in result.allPrices"
              :key="mKey"
              :class="[
                'border-t border-slate-800/60 transition-colors',
                mKey === result.method ? 'bg-violet-900/10' : ''
              ]"
            >
              <td class="py-2 pr-4">
                <div class="flex items-center gap-2">
                  <span :class="[
                    'font-medium',
                    mKey === result.method ? 'text-violet-300' : 'text-slate-400'
                  ]">{{ METHOD_LABELS[mKey] }}</span>
                  <span v-if="mKey === result.method"
                    class="text-[9px] font-bold text-violet-400 border border-violet-700/50 rounded-full px-1.5 py-0.5">
                    active
                  </span>
                </div>
              </td>
              <td :class="[
                'py-2 pr-4 text-right font-mono',
                mKey === result.method ? 'text-emerald-400 font-bold' : 'text-slate-400'
              ]">
                ${{ fmt6(prices.call) }}
              </td>
              <td :class="[
                'py-2 text-right font-mono',
                mKey === result.method ? 'text-rose-400 font-bold' : 'text-slate-400'
              ]">
                ${{ fmt6(prices.put) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Put-call parity note (European only) -->
      <div v-if="result.style === 'european'" class="mt-3 pt-3 border-t border-slate-800">
        <div class="hint font-mono">
          Put-Call Parity: C − P = Se^(−qT) − Ke^(−rT)
        </div>
      </div>

      <!-- ── Explain section ──────────────────────────────────────────── -->
      <div class="mt-4 pt-4 border-t border-slate-800">

        <!-- Level pills + Explain button -->
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Explain as:</span>
          <button
            v-for="lvl in LEVELS"
            :key="lvl.key"
            @click="explainLevel = lvl.key"
            :class="[
              'text-[10px] font-semibold rounded-full px-2.5 py-0.5 border transition-colors',
              explainLevel === lvl.key
                ? 'bg-violet-900/40 border-violet-600 text-violet-300'
                : 'border-slate-700 text-slate-500 hover:text-slate-300'
            ]"
          >{{ lvl.label }}</button>
          <button
            @click="runExplain"
            :disabled="explainLoading"
            class="ml-auto text-[10px] font-semibold rounded-full px-3 py-1 border border-violet-700 text-violet-300 hover:bg-violet-900/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {{ explainLoading ? 'Explaining…' : 'Explain' }}
          </button>
        </div>

        <!-- Explanation output -->
        <div v-if="explanation" class="mt-3 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap bg-slate-900/60 rounded-lg p-3 border border-slate-800">
          {{ explanation }}
        </div>
        <div v-if="explainError" class="mt-2 text-xs text-rose-400">
          {{ explainError }}
        </div>

      </div>

    </template>

    <!-- Empty state -->
    <div v-else class="flex items-center justify-center h-28 text-slate-600 text-sm">
      Enter valid parameters to see prices
    </div>

  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PriceDisplay.vue
git commit -m "feat: add explain button and explanation panel to PriceDisplay"
```

---

## Task 10: Frontend — `ChatPanel.vue` (new component)

**Files:**
- Create: `frontend/src/components/ChatPanel.vue`

- [ ] **Step 1: Create `frontend/src/components/ChatPanel.vue`**

```vue
<script setup>
import { ref, nextTick, watch } from 'vue'
import { sendChat } from '../lib/api.js'

const props = defineProps({
  open: { type: Boolean, required: true },
})
const emit = defineEmits(['close'])

const LEVELS = [
  { key: 'beginner',        label: 'Beginner' },
  { key: 'finance_student', label: 'Student' },
  { key: 'professional',    label: 'Professional' },
]

const level    = ref('finance_student')
const messages = ref([])   // { role: 'user'|'model', content: string }
const input    = ref('')
const loading  = ref(false)
const error    = ref(null)
const listEl   = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollTop = listEl.value.scrollHeight
}

watch(() => messages.value.length, scrollToBottom)

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  error.value = null
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  try {
    const data = await sendChat(messages.value, level.value)
    messages.value.push({ role: 'model', content: data.reply })
  } catch (e) {
    error.value = e.message
    messages.value.pop() // remove the user message so it can be retried
    input.value = text
  } finally {
    loading.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function clear() {
  messages.value = []
  error.value = null
}
</script>

<template>
  <!-- Backdrop (mobile) -->
  <div
    v-if="open"
    class="fixed inset-0 bg-black/40 z-40 lg:hidden"
    @click="emit('close')"
  />

  <!-- Panel -->
  <div
    :class="[
      'fixed inset-y-0 right-0 z-50 w-96 max-w-full flex flex-col',
      'bg-slate-900 border-l border-slate-800 shadow-2xl',
      'transition-transform duration-300',
      open ? 'translate-x-0' : 'translate-x-full',
    ]"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
      <span class="text-sm font-semibold text-slate-200">Options Assistant</span>
      <div class="flex items-center gap-1.5">
        <button
          v-for="lvl in LEVELS"
          :key="lvl.key"
          @click="level = lvl.key"
          :class="[
            'text-[10px] font-semibold rounded-full px-2 py-0.5 border transition-colors',
            level === lvl.key
              ? 'bg-violet-900/40 border-violet-600 text-violet-300'
              : 'border-slate-700 text-slate-500 hover:text-slate-300'
          ]"
        >{{ lvl.label }}</button>
        <button
          @click="emit('close')"
          class="ml-2 text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
          aria-label="Close"
        >×</button>
      </div>
    </div>

    <!-- Message list -->
    <div ref="listEl" class="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
      <div v-if="messages.length === 0" class="text-center text-xs text-slate-600 mt-8">
        Ask anything about options, Greeks, or pricing models.
      </div>
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="[
          'max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap',
          msg.role === 'user'
            ? 'self-end bg-violet-900/50 border border-violet-800/60 text-violet-100'
            : 'self-start bg-slate-800 border border-slate-700 text-slate-200'
        ]"
      >{{ msg.content }}</div>

      <!-- Typing indicator -->
      <div v-if="loading" class="self-start flex items-center gap-1 px-3 py-2">
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:0ms"/>
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:150ms"/>
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:300ms"/>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="px-4 pb-2 text-xs text-rose-400 shrink-0">{{ error }}</div>

    <!-- Footer: clear + input -->
    <div class="px-4 py-3 border-t border-slate-800 flex flex-col gap-2 shrink-0">
      <div class="flex justify-end">
        <button
          @click="clear"
          class="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
        >Clear conversation</button>
      </div>
      <div class="flex gap-2 items-end">
        <textarea
          v-model="input"
          @keydown="onKeydown"
          rows="1"
          placeholder="Ask about options…"
          class="flex-1 resize-none bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-600 transition-colors"
          style="max-height: 6rem; overflow-y: auto;"
          :disabled="loading"
        />
        <button
          @click="send"
          :disabled="loading || !input.trim()"
          class="px-3 py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
        >Send</button>
      </div>
      <p class="text-[9px] text-slate-700 text-center">Enter to send · Shift+Enter for new line</p>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatPanel.vue
git commit -m "feat: add ChatPanel slide-in sidebar component"
```

---

## Task 11: Frontend — wire `App.vue` + `NavBar.vue`

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/NavBar.vue`

- [ ] **Step 1: Add `chatOpen` ref and `ChatPanel` to `App.vue`**

Replace the full contents of `frontend/src/App.vue` with:

```vue
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { computeRange } from './lib/blackScholes.js'
import { fetchRFR, priceOption } from './lib/api.js'
import NavBar from './components/NavBar.vue'
import InputPanel from './components/InputPanel.vue'
import PriceDisplay from './components/PriceDisplay.vue'
import GreeksGrid from './components/GreeksGrid.vue'
import SensitivityChart from './components/SensitivityChart.vue'
import VolSurface from './components/VolSurface.vue'
import PriceSurface from './components/PriceSurface.vue'
import ChatPanel from './components/ChatPanel.vue'

const ticker = ref(null)
const method = ref('black_scholes')
const optionStyle = ref('european')
const sigmaType = ref('implied')
const view = ref('pricing')
const isStale = ref(false)
const marketUpdatedAt = ref(null)
const chatOpen = ref(false)

const inputs = ref({ S: 0, K: 0, T: 0, r: 0, sigma: 0, q: 0 })

const result = ref(null)
const priceLoading = ref(false)
const priceError = ref(null)

const theme = ref('dark')

function applyTheme(value) {
  const root = document.documentElement
  root.classList.toggle('theme-light', value === 'light')
  localStorage.setItem('theme', value)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  applyTheme(theme.value)
}

onMounted(async () => {
  const storedTheme = localStorage.getItem('theme')
  if (storedTheme === 'light' || storedTheme === 'dark') {
    theme.value = storedTheme
  } else {
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
    if (prefersLight) theme.value = 'light'
  }
  applyTheme(theme.value)
  try { inputs.value.r = await fetchRFR() } catch { /* leave at 0 */ }
})

const canPrice = computed(() => {
  const { S, K, T, sigma } = inputs.value
  return S > 0 && K > 0 && T > 0 && sigma > 0
})

const chartData = computed(() => {
  const { S, K, T, r, sigma, q } = inputs.value
  if (!canPrice.value) return null
  const sMin = S * 0.55
  const sMax = S * 1.45
  return computeRange(K, T / 365, r / 100, sigma / 100, q / 100, sMin, sMax)
})

let debounceTimer = null

async function loadPrices() {
  if (!canPrice.value) { result.value = null; return }
  priceLoading.value = true
  priceError.value = null
  try {
    const base = {
      S: inputs.value.S,
      K: inputs.value.K,
      T: inputs.value.T / 365,
      r: inputs.value.r != null ? inputs.value.r / 100 : null,
      q: inputs.value.q / 100,
      sigma: inputs.value.sigma / 100,
      style: optionStyle.value,
      method: 'all',
      mc_paths: optionStyle.value === 'european' ? 50000 : 5000,
    }
    const [callRes, putRes] = await Promise.all([
      priceOption({ ...base, option_type: 'call' }),
      priceOption({ ...base, option_type: 'put' }),
    ])

    const mKey = method.value
    const cm = callRes.prices[mKey]
    const pm = putRes.prices[mKey]

    result.value = {
      call: { price: cm.price, ...cm.greeks },
      put:  { price: pm.price, ...pm.greeks },
      allPrices: Object.fromEntries(
        Object.entries(callRes.prices).map(([k, v]) => [k, { call: v.price, put: putRes.prices[k].price }])
      ),
      sigma: callRes.sigma,
      method: method.value,
      style: optionStyle.value,
    }
  } catch (e) {
    priceError.value = e.message
    result.value = null
  } finally {
    priceLoading.value = false
  }
}

watch([inputs, method, optionStyle], () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadPrices, 500)
}, { deep: true })
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100" style="font-family: Inter, system-ui, sans-serif;">
    <NavBar
      :r="inputs.r"
      :sigma="inputs.sigma"
      :ticker="ticker"
      :theme="theme"
      :chat-open="chatOpen"
      @toggle-theme="toggleTheme"
      @toggle-chat="chatOpen = !chatOpen"
    />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">

      <!-- Tab navigation -->
      <div class="flex gap-1 mb-6 border-b border-slate-800">
        <button
          v-for="tab in [{ key: 'pricing', label: 'Pricing & Greeks' }, { key: 'surfaces', label: 'Surfaces' }]"
          :key="tab.key"
          @click="view = tab.key"
          :class="[
            'px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px',
            view === tab.key
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-300'
          ]"
        >{{ tab.label }}</button>
      </div>

      <!-- Pricing & Greeks view -->
      <div v-if="view === 'pricing'" class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-2">
          <InputPanel
            v-model="inputs"
            v-model:ticker="ticker"
            v-model:method="method"
            v-model:optionStyle="optionStyle"
            v-model:sigmaType="sigmaType"
            v-model:isStale="isStale"
            v-model:updatedAt="marketUpdatedAt"
          />
        </div>
        <div class="lg:col-span-3 flex flex-col gap-5">
          <PriceDisplay
            :result="result"
            :inputs="inputs"
            :loading="priceLoading"
            :error="priceError"
          />
          <GreeksGrid :result="result" />
          <SensitivityChart v-if="optionStyle === 'european'" :chart-data="chartData" :current-s="inputs.S" :current-k="inputs.K" :theme="theme" />
        </div>
      </div>

      <!-- Surfaces view -->
      <div v-else class="flex flex-col gap-6">
        <VolSurface :ticker="ticker" :theme="theme" />
        <PriceSurface
          :ticker="ticker"
          :inputs="inputs"
          :option-style="optionStyle"
          :sigma-type="sigmaType"
          :theme="theme"
        />
      </div>

    </main>

    <footer class="mt-12 border-t border-slate-800 py-6 text-center text-xs text-slate-600">
      Option Pricing Platform · Black-Scholes · Monte Carlo · Binomial Tree · BAW · For educational purposes
    </footer>

    <!-- Chat panel (rendered outside main flow, fixed positioned) -->
    <ChatPanel :open="chatOpen" @close="chatOpen = false" />
  </div>
</template>
```

- [ ] **Step 2: Replace `frontend/src/components/NavBar.vue` with the following**

```vue
<script setup>
defineProps({
  r:        { type: Number,  default: 4.5 },
  sigma:    { type: Number,  default: 20 },
  ticker:   { type: String,  default: null },
  theme:    { type: String,  default: 'dark' },
  chatOpen: { type: Boolean, default: false },
})

defineEmits(['toggle-theme', 'toggle-chat'])

const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
</script>

<template>
  <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:h-16">

        <!-- Brand -->
        <div class="flex items-center gap-3 shrink-0">
          <div class="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center font-bold text-slate-950 text-base select-none">
            Δ
          </div>
          <div>
            <div class="font-semibold text-slate-100 text-base leading-none tracking-tight">OptionDesk</div>
            <div class="text-[10px] text-slate-500 leading-none mt-0.5 hidden sm:block">
              Black-Scholes · European Options
            </div>
          </div>
        </div>

        <!-- Market data pills + controls -->
        <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto sm:justify-end">
          <div v-if="ticker" class="flex items-center gap-1.5 bg-emerald-900/30 border border-emerald-700/50 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span class="text-xs font-mono font-semibold text-emerald-300">{{ ticker }}</span>
          </div>
          <div class="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="text-xs text-slate-400 hidden sm:inline">Risk-Free</span>
            <span class="text-xs font-mono font-semibold text-emerald-400">{{ r.toFixed(2) }}%</span>
          </div>
          <div class="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
            <span class="text-xs text-slate-400 hidden sm:inline">Vol</span>
            <span class="text-xs font-mono font-semibold text-blue-400">{{ sigma.toFixed(1) }}%</span>
          </div>
          <div class="hint hidden md:block">{{ today }}</div>

          <!-- Ask AI toggle -->
          <button
            @click="$emit('toggle-chat')"
            :class="[
              'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold transition-colors',
              chatOpen
                ? 'bg-violet-900/40 border-violet-600 text-violet-300'
                : 'border-slate-700 bg-slate-800 text-slate-400 hover:border-violet-600 hover:text-violet-300'
            ]"
            type="button"
            aria-label="Toggle AI chat panel"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
            <span class="hidden sm:inline">Ask AI</span>
          </button>

          <!-- Theme toggle -->
          <button
            class="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-colors hover:border-emerald-500 hover:text-emerald-400"
            @click="$emit('toggle-theme')"
            type="button"
            aria-label="Toggle light and dark mode"
          >
            <svg v-if="theme === 'light'" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.36 6.36-1.42-1.42M7.05 7.05 5.64 5.64m12.72 0-1.41 1.41M7.05 16.95l-1.41 1.41M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z" />
            </svg>
            <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 0 1 11.21 3 7 7 0 1 0 21 12.79z" />
            </svg>
            <span class="hidden sm:inline">{{ theme === 'light' ? 'Dark' : 'Light' }}</span>
          </button>
        </div>

      </div>
    </div>
  </header>
</template>
```

- [ ] **Step 3: Start the dev server and verify the UI**

```bash
cd frontend && npm run dev
```

Open the browser. Verify:
1. "Ask AI" button appears in the NavBar
2. Clicking it slides the chat panel in from the right
3. Clicking × or the backdrop closes it
4. Level pills in the panel switch correctly
5. "Clear conversation" empties the messages
6. The Explain section appears below prices once a result is loaded
7. Explain level pills and button are visible
8. Clicking Explain shows a loading state then the explanation text

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue frontend/src/components/NavBar.vue
git commit -m "feat: wire chat panel toggle into NavBar and App"
```

---

## Task 12: Final smoke test and full test run

- [ ] **Step 1: Run the full backend test suite**

```bash
python -m pytest tests/ -v
```
Expected: all tests pass (including the new AI tests).

- [ ] **Step 2: Set the API key and start the server**

```bash
set GEMINI_API_KEY=your_actual_key   # Windows
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 3: Smoke test the explain endpoint**

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Content-Type: application/json" \
  -d "{\"user_level\":\"beginner\",\"option_type\":\"call\",\"style\":\"european\",\"method\":\"black_scholes\",\"S\":150,\"K\":155,\"T\":0.5,\"r\":0.05,\"sigma\":0.22,\"q\":0.0,\"prices\":{\"black_scholes\":{\"price\":4.23,\"greeks\":{\"delta\":0.42,\"gamma\":0.05,\"vega\":0.30,\"theta\":-0.15,\"rho\":0.10}}}}"
```
Expected: `{"explanation": "..."}` with a non-empty string.

- [ ] **Step 4: Smoke test the chat endpoint**

```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_level\":\"finance_student\",\"messages\":[{\"role\":\"user\",\"content\":\"What is delta?\"}]}"
```
Expected: `{"reply": "..."}` with a non-empty string.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete AI explain and chat feature"
```
