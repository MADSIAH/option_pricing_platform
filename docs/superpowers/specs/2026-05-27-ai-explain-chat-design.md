# AI Explain & Chat — Design Spec
> Date: 2026-05-27
> Branch: `feature/ai-explain-chat`
> Status: approved, pending implementation

---

## Overview

Two AI features added to the Option Pricing Platform:

1. **Explain button** — interprets a pricing result (prices + Greeks) in plain language, adapted to the user's stated level.
2. **Chat panel** — a slide-in sidebar for free-form questions about options, Greeks, pricing models, and the vol surface.

Both features use the Google Gemini API (`gemini-2.0-flash`). Neither makes buy/sell recommendations. Both adapt their language depth to a user-selected level chosen per interaction.

---

## Constraints

- Model: `gemini-2.0-flash`
- API key: read from environment variable `GEMINI_API_KEY` at startup
- No buy/sell recommendations under any circumstances
- On-topic scope for chat: options pricing, Greeks, pricing models (BS, MC, BT, BAW, LS), volatility surface
- Off-topic questions: politely redirected, not refused harshly
- System prompts are plain `.txt` files — swappable without touching any logic
- Backend remains stateless — no session or conversation storage server-side

---

## User Level

Three levels selectable per interaction (not stored globally):

| Key | Label |
|-----|-------|
| `beginner` | Beginner |
| `finance_student` | Student |
| `professional` | Professional |

Default: `finance_student`. The level is included in every API request and used to adjust the tone and depth of the Gemini response.

---

## File Map

### Backend (new)

```
src/ai/
  __init__.py
  client.py              # Gemini client — reads GEMINI_API_KEY, exposes generate()
  prompts.py             # loads .txt files into EXPLAIN_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
  prompts/
    explain_system.txt   # explain system prompt — swap this file to change behaviour
    chat_system.txt      # chat system prompt — topic scope, no-recommendations rule
  explain.py             # build_explain_message(result, level) + call_explain()
  chat.py                # call_chat(messages, level)

src/api/routes/
  ai.py                  # POST /api/v1/ai/explain, POST /api/v1/ai/chat
```

### Backend (modified)

```
src/api/schemas.py          # + ExplainRequest, ExplainResponse,
                            #   ChatMessage, ChatRequest, ChatResponse
src/api/routes/__init__.py  # + ai_router
src/api/main.py             # + app.include_router(ai_router, prefix="/api/v1")
```

### Frontend (new)

```
frontend/src/components/
  ChatPanel.vue          # slide-in right panel, toggled from NavBar
```

### Frontend (modified)

```
frontend/src/App.vue                  # + chatOpen ref, passed to NavBar + ChatPanel
frontend/src/components/NavBar.vue    # + "Ask AI" toggle button
frontend/src/components/PriceDisplay.vue  # + level pills, Explain button, explanation display
frontend/src/lib/api.js               # + explainResult(), sendChat()
```

---

## Backend Design

### `src/ai/client.py`

```python
API_KEY = os.environ["GEMINI_API_KEY"]  # raises KeyError at import if missing — fails loudly
MODEL   = "gemini-2.0-flash"
```

Exposes a single function:
```python
def generate(system_instruction: str, contents: list[dict]) -> str
```
Calls `google-generativeai`, returns the text of the first candidate. Raises `GeminiError`
(custom exception) on API failure so routes can catch it cleanly.

### `src/ai/prompts.py`

```python
from pathlib import Path
_DIR = Path(__file__).parent / "prompts"
EXPLAIN_SYSTEM_PROMPT = (_DIR / "explain_system.txt").read_text(encoding="utf-8")
CHAT_SYSTEM_PROMPT    = (_DIR / "chat_system.txt").read_text(encoding="utf-8")
```

No logic — purely loads the files. To swap a prompt: replace the `.txt` file.

### `src/ai/prompts/explain_system.txt`

Placeholder — content to be provided separately. Expected structure:
- Role definition (educational assistant, options domain)
- Depth rules per level (`beginner` / `finance_student` / `professional`)
- Explicit prohibition on buy/sell recommendations
- Tone and length guidelines

### `src/ai/prompts/chat_system.txt`

Content defined at implementation time:
- Role: educational assistant for options pricing
- Topic scope: options, Greeks (delta/gamma/vega/theta/rho), pricing models, implied vol, vol surface
- Off-topic handling: acknowledge the question, politely redirect to options topics
- No buy/sell recommendations
- Adapt depth to the `user_level` passed in the user turn

### `src/ai/explain.py`

```python
def call_explain(request: ExplainRequest) -> str:
    user_message = build_explain_message(request)
    return generate(EXPLAIN_SYSTEM_PROMPT, [{"role": "user", "parts": [user_message]}])
```

`build_explain_message` serialises the full pricing context — S, K, T, r, sigma, q,
option_type, style, method, all prices and all Greeks — plus the user_level into a
structured text block. This is the only place numbers flow into the prompt; the system
prompt is purely about how to explain.

### `src/ai/chat.py`

```python
def call_chat(messages: list[ChatMessage], user_level: str) -> str:
    contents = [{"role": m.role, "parts": [m.content]} for m in messages]
    contents[-1]["parts"][0] = f"[Level: {user_level}]\n{contents[-1]['parts'][0]}"
    return generate(CHAT_SYSTEM_PROMPT, contents)
```

The level is injected into the last user turn so the model can adapt mid-conversation
if the user switches levels.

### `src/api/routes/ai.py`

Two thin route handlers:

```
POST /api/v1/ai/explain
  body:     ExplainRequest
  response: ExplainResponse { explanation: str }
  errors:   500 if GEMINI_API_KEY missing, 502 on Gemini API failure

POST /api/v1/ai/chat
  body:     ChatRequest
  response: ChatResponse { reply: str }
  errors:   500 if GEMINI_API_KEY missing, 502 on Gemini API failure, 422 if messages empty
```

### Schemas (additions to `schemas.py`)

```python
class UserLevel(str, Enum):
    beginner        = "beginner"
    finance_student = "finance_student"
    professional    = "professional"

class ExplainRequest(BaseModel):
    user_level:  UserLevel
    option_type: OptionType
    style:       OptionStyle
    method:      str
    S: float; K: float; T: float; r: float; sigma: float; q: float
    prices: dict[str, PriceModelOutput]

class ExplainResponse(BaseModel):
    explanation: str

class ChatMessage(BaseModel):
    role:    Literal["user", "model"]
    content: str

class ChatRequest(BaseModel):
    user_level: UserLevel
    messages:   list[ChatMessage] = Field(..., min_length=1)

class ChatResponse(BaseModel):
    reply: str
```

---

## Frontend Design

### `App.vue`

Adds `chatOpen = ref(false)`. Passes it to `NavBar` (to drive the toggle button active
state) and to `ChatPanel` (as the `v-if` / transition guard).

### `NavBar.vue`

Adds a small "Ask AI" button to the right side of the nav bar, next to the existing
theme toggle. Clicking emits `toggle-chat`, which flips `chatOpen` in `App.vue`.

### `PriceDisplay.vue`

Below the existing put-call parity note, rendered only when `result` is set:

1. **Level pills row** — `Beginner` · `Student` · `Professional`, defaults to `Student`
2. **Explain button** — triggers `explainResult()`, disabled while loading
3. **Explanation block** — styled text area that appears after the API response
4. **Error message** — shown inline if the call fails

The entire explain section is hidden when `result` is null (nothing priced yet).
The Explain button does **not** fire automatically on re-price — the user clicks it
deliberately to avoid burning API quota on every parameter change.

### `ChatPanel.vue`

Fixed right panel (`position: fixed`, full viewport height, right edge), `w-96`,
slides in with a CSS `transform: translateX` transition. Sits above all content (`z-50`).

Structure top to bottom:
- **Header**: "Options Assistant" title + level pills + close (×) button
- **Message list**: scrollable, auto-scrolls to bottom on new message; `user` bubbles
  right-aligned, `model` bubbles left-aligned; styled with dark slate theme
- **Clear button**: resets `messages` to `[]`
- **Input row**: `<textarea>` (auto-grows, 1–3 rows) + Send button;
  Enter sends, Shift+Enter inserts newline

Chat history (`messages`) is a `ref([])` local to this component — reset on clear,
lost on page reload. Nothing is sent to or stored by the server.

### `lib/api.js`

```js
export async function explainResult(payload) {
  // POST /api/v1/ai/explain — returns { explanation }
}

export async function sendChat(messages, userLevel) {
  // POST /api/v1/ai/chat — returns { reply }
}
```

---

## Error Handling

| Condition | HTTP | Behaviour |
|---|---|---|
| `GEMINI_API_KEY` not set | 500 | Both endpoints return `{"error": "AI service not configured"}` |
| Gemini API call fails | 502 | `{"error": "AI service unavailable", "detail": "..."}` |
| Empty messages list | 422 | Pydantic validation rejects the request |
| Off-topic question | 200 | Gemini redirects politely (handled by `chat_system.txt`) |
| No pricing result yet | — | Explain section not rendered (frontend guard on `result`) |

---

## Scope Clarification

- The **Explain button** covers the output of `POST /price` only: option prices and all
  Greeks for the selected method. It does not appear on the Surfaces tab.
- The **Chat panel** answers questions about any options topic — including Greeks
  interpretation, vol surface behaviour, and pricing model differences — regardless of
  which tab is active.
- Out of scope: streaming responses, server-side conversation storage,
  authentication / rate limiting, trading strategy suggestions.
