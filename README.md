# OptionDesk — AI-Enhanced Options Pricing Platform

> **Programming in Finance II — Big Projects 2026**  
> Project 2.7 · Università della Svizzera Italiana (USI)  
> Mantovani Sara · Nicol Massimiliano · Pescio Vittoria · Rocco Elena

![Status](https://img.shields.io/badge/status-complete-brightgreen)
![Tests](https://img.shields.io/badge/tests-127%20passing-brightgreen)
![Stack](https://img.shields.io/badge/stack-Vue3%20%7C%20FastAPI%20%7C%20Python-blue)
![Live](https://img.shields.io/badge/live-option--pricing--platform.vercel.app-emerald)

An educational, AI-enhanced platform for options pricing, Greeks analysis, volatility surface modeling, and natural-language explanation of results — built for students and practitioners alike.

**Live demo:** [option-pricing-platform.vercel.app](https://option-pricing-platform.vercel.app)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Criteria](#project-criteria)
- [Documentation](#documentation)
- [AI Contribution](#ai-contribution)

---

## Overview

Options pricing sits at the intersection of mathematics, statistics, and market microstructure. This platform makes it tangible: it prices European, American, and exotic options using both closed-form and numerical methods, computes the full Greek profile, constructs the implied volatility surface from live market data, and explains every result in natural language adapted to the user's background.

---

## Features

### Pricing Engine

Six models covering European, American, and stochastic-volatility pricing:

| Model | Type | Options |
|-------|------|---------|
| Black-Scholes (BS) | Closed-form analytical | European |
| Monte Carlo (MC) | GBM simulation, antithetic variates, 50 000 paths | European |
| Cox-Ross-Rubinstein (CRR) | Binomial lattice | European + American |
| Longstaff-Schwartz (LSM) | Monte Carlo + OLS regression | American |
| Barone-Adesi-Whaley (BAW) | Analytical approximation | American |
| Heston | Correlated CIR variance, Euler-Maruyama | European (stochastic vol) |

All numerical models are cross-validated against Black-Scholes and converge within 1% ATM. Continuous dividend yield `q` is supported across all models.

### Exotic Options

Priced via full GBM path simulation (`GBMPathSimulator`, antithetic variates):

| Type | Payoff | Key property |
|------|--------|--------------|
| Asian (arithmetic avg) | max(A − K, 0) | Price < vanilla |
| Barrier (knock-in / knock-out) | Conditional on barrier crossing | Out + In = Vanilla |
| Lookback (fixed strike) | max(S_max − K, 0) | Price ≥ vanilla |
| Digital (cash-or-nothing) | 1 if S_T > K, else 0 | Call + Put = e^(−rT) |

### Greeks

Five sensitivities for every pricing result:

| Greek | Symbol | Sensitivity to | Method |
|-------|--------|---------------|--------|
| Delta | Δ | Spot price | Analytical (BS) / central differences |
| Gamma | Γ | Delta (2nd-order spot) | Analytical (BS) / central differences |
| Vega | ν | Implied volatility | Analytical (BS) / central differences |
| Theta | Θ | Time to expiry | Analytical (BS) / central differences |
| Rho | ρ | Risk-free rate | Analytical (BS) / central differences |

Analytical formulas used for Black-Scholes; numerical central differences as fallback for MC and BT.

### Volatility Surface

- Implied volatility extracted from live AAPL option chain via `scipy.optimize.brentq` (Brent's root-finding)
- Chain cleaning: minimum TTM cutoff, bid-ask spread filter, moneyness range [0.7, 1.3], liquidity filter
- Interactive 3D surface visualization in the web frontend

### AI Features

Two AI-powered features (Gemini 2.5 Flash):

**Pricing Explanation** (`POST /api/v1/ai/explain`)  
- Triggered after any pricing result
- Explains price and Greeks in natural language
- Depth adapts to user level: Beginner / Finance Student / Professional

**Options Assistant — Chat** (`POST /api/v1/ai/chat`)  
- Persistent chat panel, accessible from the navbar ("Ask AI")
- Free-form Q&A about options, pricing models, and Greeks
- Maintains conversation history within the session

### Web Frontend

- Vue 3 + Vite + Tailwind CSS, deployed on Vercel
- Tabs: **Pricing & Greeks** and **Surfaces**
- Stock selector: AAPL, MSFT, TSLA, SPY, QQQ or manual input
- European / American style toggle
- Method selector with real-time comparison table
- Interactive sensitivity chart (price vs spot)
- Implied volatility surface (3D) and price surface (3D)
- Light / Dark mode with persisted preference
- Responsive layout (desktop-first, mobile-friendly)

### Real-Time Market Data

- Equity prices and option chains via `yfinance`
- Risk-free rates via FRED API (TB3MS — 3-Month Treasury Bill)
- Scheduled refresh via `APScheduler` (every 60 minutes)
- Data cached in SQLite for fast API responses

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Pricing engine | Python 3.13, NumPy, SciPy |
| API | FastAPI + Uvicorn |
| Frontend | Vue 3 + Vite + Tailwind CSS |
| Data ingestion | `yfinance`, FRED API, `requests` |
| Scheduling | `APScheduler` |
| LLM integration | Google Gemini 2.5 Flash (via `google-genai`) |
| Database | SQLite (via `src/data/database.py`) |
| Frontend deployment | Vercel |
| Backend deployment | VPS (Ubuntu, Uvicorn) |

---

## Repository Structure

```
option_pricing_platform/
│
├── frontend/                       # Vue 3 web application
│   ├── src/
│   │   ├── components/             # UI components
│   │   │   ├── NavBar.vue          # Header with market pills and AI toggle
│   │   │   ├── InputPanel.vue      # Parameter inputs, stock selector, method picker
│   │   │   ├── PriceDisplay.vue    # Option prices and method comparison table
│   │   │   ├── GreeksGrid.vue      # Greeks cards (Δ, Γ, ν, Θ, ρ)
│   │   │   ├── SensitivityChart.vue # Price vs spot plot
│   │   │   ├── VolSurface.vue      # Implied vol surface (3D)
│   │   │   ├── PriceSurface.vue    # Price surface (3D)
│   │   │   ├── ExplainPanel.vue    # AI explanation panel
│   │   │   └── ChatPanel.vue       # AI chat assistant
│   │   └── lib/
│   │       ├── api.js              # API client (fetch wrappers)
│   │       ├── blackScholes.js     # Client-side BS for sensitivity chart
│   │       └── markdown.js         # Markdown + KaTeX rendering
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── vercel.json                 # Vercel config + API proxy rewrite
│
├── src/
│   ├── ai/                         # LLM integration
│   │   ├── prompts/                # System prompt text files
│   │   │   ├── explain_system.txt
│   │   │   └── chat_system.txt
│   │   ├── client.py               # Gemini API wrapper
│   │   ├── explain.py              # Pricing result explainer
│   │   └── chat.py                 # Conversational assistant
│   │
│   ├── api/                        # FastAPI application
│   │   ├── routes/
│   │   │   ├── health.py           # GET /api/v1/health
│   │   │   ├── market.py           # GET /api/v1/market/{ticker}
│   │   │   ├── pricing.py          # POST /api/v1/price, /price_surface
│   │   │   ├── surface.py          # GET /api/v1/vol_surface/{ticker}
│   │   │   └── ai.py               # POST /api/v1/ai/explain, /ai/chat
│   │   ├── main.py                 # FastAPI app, CORS, lifespan
│   │   └── schemas.py              # Pydantic request/response models
│   │
│   ├── data/                       # Data layer
│   │   ├── database.py             # SQLite setup and queries
│   │   ├── fetcher.py              # yfinance + FRED data fetching
│   │   └── scheduler.py            # APScheduler refresh jobs
│   │
│   └── pricing/                    # Pricing engine
│       ├── base.py                 # OptionParams, PricingResult, PricingModel ABC
│       ├── utils.py                # d1(), d2() helpers
│       ├── black_scholes.py        # Analytical BS (benchmark)
│       ├── monte_carlo.py          # MC with antithetic variates
│       ├── binomial_tree.py        # CRR lattice (European + American)
│       ├── longstaff_schwartz.py   # LSM American MC
│       ├── baw.py                  # Barone-Adesi-Whaley approximation
│       ├── heston.py               # Heston stochastic volatility MC
│       ├── greeks.py               # AnalyticalGreeks + NumericalGreeks
│       ├── vol_surface.py          # implied_vol(), build_vol_surface()
│       ├── exotics.py              # Asian, Barrier, Lookback, Digital
│       ├── path_simulator.py       # GBMPathSimulator (shared)
│       └── __init__.py
│
├── tests/                          # pytest test suite (127 passing)
│   ├── test_monte_carlo.py
│   ├── test_binomial_tree.py
│   ├── test_greeks.py
│   ├── test_vol_surface.py
│   ├── test_exotics.py
│   ├── test_longstaff_schwartz.py
│   ├── test_heston.py
│   ├── test_baw.py
│   ├── test_ai_explain.py
│   ├── test_ai_chat.py
│   ├── test_ai_client.py
│   └── test_ai_routes.py
│
├── notebooks/
│   └── pricing.ipynb               # Full demo: live data → pricing → Greeks → vol surface
│
├── docs/
│   └── specs/                      # Design specs (Spec A/B/C, AI design)
│
├── scripts/
│   └── test_data.py                # Data pipeline validation script
│
├── AGENTS.md                       # AI agent contribution guidelines
├── CLAUDE.md                       # Claude Code project context
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key (free tier) for AI features

### Backend

```bash
git clone https://github.com/MADSIAH/option_pricing_platform.git
cd option_pricing_platform

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

---

## Running Locally

### 1. Set environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Start the backend API

```bash
# From the project root
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Start the frontend

```bash
cd frontend
npm run dev
```

The app will be available at `http://localhost:5173`.

> **Note:** For local development, the frontend reads `VITE_API_URL`. Set it to `http://localhost:8000/api/v1` in `frontend/.env.local` if needed.

### 4. (Optional) Run the data scheduler

```bash
python -m src.data.scheduler
```

This initialises the SQLite database and starts the 60-minute refresh cycle for market data.

---

## API Documentation

Full interactive documentation is available at `/docs` (Swagger UI) when the backend is running.

### Endpoints

#### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health check |

#### Market Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/market/{ticker}` | Spot price, risk-free rate, historical vol, dividend yield |

**Response example:**
```json
{
  "ticker": "AAPL",
  "spot": 213.45,
  "risk_free_rate": 0.0527,
  "sigma": 0.2341,
  "dividend_yield": 0.0044
}
```

#### Pricing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/price` | Price an option with all available models |
| `POST` | `/api/v1/price_surface` | Compute a price surface over (S, T) grid |

**Request body (`/api/v1/price`):**
```json
{
  "S": 213.45,
  "K": 215.0,
  "T": 0.25,
  "r": 0.0527,
  "sigma": 0.23,
  "q": 0.0044,
  "option_type": "call",
  "style": "european",
  "method": "all",
  "mc_paths": 50000
}
```

**Response:**
```json
{
  "prices": {
    "black_scholes": { "price": 8.42, "greeks": { "delta": 0.521, "gamma": 0.018, "vega": 0.421, "theta": -0.042, "rho": 0.231 } },
    "monte_carlo":   { "price": 8.38, "greeks": { ... } },
    "binomial_tree": { "price": 8.41, "greeks": { ... } },
    "baw":           { "price": 8.42, "greeks": { ... } }
  },
  "sigma": 0.23
}
```

#### Volatility Surface

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/vol_surface/{ticker}` | Implied vol surface for a ticker |

**Query parameters:** `option_type` (default: `call`)

#### AI Features

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ai/explain` | Explain a pricing result in natural language |
| `POST` | `/api/v1/ai/chat` | Send a message to the options assistant |

**Request body (`/api/v1/ai/explain`):**
```json
{
  "result": { "call_price": 8.42, "greeks": { "delta": 0.52, ... } },
  "level": "beginner"
}
```

**Request body (`/api/v1/ai/chat`):**
```json
{
  "messages": [
    { "role": "user", "content": "What does a delta of 0.52 mean?" }
  ],
  "level": "student"
}
```

---

## Usage Examples

### Python — pricing engine directly

```python
from src.pricing.base import OptionParams
from src.pricing.black_scholes import BlackScholes
from src.pricing.monte_carlo import MonteCarlo
from src.pricing.greeks import AnalyticalGreeks

params = OptionParams(S=100, K=105, T=0.5, r=0.05, sigma=0.20, option_type="call")

# Black-Scholes
bs = BlackScholes()
print(bs.price(params).price)      # e.g. 4.07

# Monte Carlo
mc = MonteCarlo(n_paths=50_000, seed=42)
print(mc.price(params).price)      # e.g. 4.05

# Greeks
g = AnalyticalGreeks().compute(params)
print(g.delta, g.gamma, g.vega)    # e.g. 0.40  0.034  0.274
```

### Python — American option (Longstaff-Schwartz)

```python
from src.pricing.longstaff_schwartz import LongstaffSchwartz

ls = LongstaffSchwartz(n_paths=50_000, n_steps=252, seed=42)
put = OptionParams(S=100, K=105, T=1.0, r=0.05, sigma=0.20, option_type="put")
print(ls.price(put).price)   # American put > European put (early exercise premium)
```

### Python — Heston stochastic volatility

```python
from src.pricing.heston import HestonMC, HestonParams

params = HestonParams(
    S=100, K=100, T=0.5, r=0.05,
    v0=0.04, kappa=2.0, theta=0.04, xi=0.30, rho=-0.70,
    option_type="call"
)
mc = HestonMC(n_paths=50_000, n_steps=252, seed=42)
print(mc.price(params).price)   # generates volatility smile
```

### Python — Implied volatility surface

```python
from src.pricing.vol_surface import implied_vol, build_vol_surface

# Single IV extraction
iv = implied_vol(market_price=4.07, S=100, K=105, T=0.5, r=0.05, option_type="call")
print(f"Implied vol: {iv:.2%}")   # e.g. 20.00%
```

### REST API — curl

```bash
# Price a call option
curl -X POST http://localhost:8000/api/v1/price \
  -H "Content-Type: application/json" \
  -d '{"S": 100, "K": 105, "T": 0.5, "r": 0.05, "sigma": 0.20, "q": 0, "option_type": "call", "style": "european", "method": "all"}'

# Get market data
curl http://localhost:8000/api/v1/market/AAPL

# AI explanation
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Content-Type: application/json" \
  -d '{"result": {"call_price": 4.07, "greeks": {"delta": 0.40}}, "level": "beginner"}'
```

---

## Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run only the pricing engine tests
python -m pytest tests/test_black_scholes.py tests/test_monte_carlo.py tests/test_binomial_tree.py tests/test_greeks.py tests/test_vol_surface.py tests/test_exotics.py tests/test_longstaff_schwartz.py tests/test_heston.py tests/test_baw.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

**Test coverage:**

| Module | Tests | Key properties verified |
|--------|-------|------------------------|
| Monte Carlo | 8 | BS convergence < 1% ATM, put-call parity, antithetic symmetry |
| Binomial Tree | 8 | BS convergence, American ≥ European, dividend effect |
| Greeks | 21 | ATM delta ≈ 0.5, parity, gamma/vega symmetry, theta < 0 |
| Vol Surface | 11 | IV roundtrip, surface shape, cleaning filters |
| Exotics | 28 | Asian < vanilla, Barrier parity, Lookback ≥ vanilla, digital bond |
| Longstaff-Schwartz | 13 | American ≥ European put, call ≈ European (no div), BT agreement |
| Heston | 21 | BS collapse (ξ→0), put-call parity, Feller warning, smile |
| BAW | varies | BAW ≥ European, American put early exercise |
| AI (explain, chat) | 16 | Message structure, level injection, system prompt usage |

---

## Deployment

### Frontend (Vercel)

The `frontend/` directory is deployed automatically on every push to `main`:

```bash
cd frontend
npm run build   # produces dist/
```

`vercel.json` rewrites `/api/v1/*` requests to the backend VPS.

### Backend (VPS)

```bash
# On the server (Ubuntu)
git pull origin main
pip install -r requirements.txt

# Start with uvicorn (production)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Or with a process manager (recommended)
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Set the `GEMINI_API_KEY` environment variable on the server before starting.

---

## Project Criteria

This project satisfies the generic 2026 criteria (≥ 3 elements, ≥ 1 advanced):

| Criterion | Implementation |
|-----------|---------------|
| ★ **LLM integration** | Gemini 2.5 Flash — pricing explanation and options assistant |
| **Cloud infrastructure** | Backend on VPS; frontend on Vercel |
| **Real-time data** | Live equity prices, option chains (yfinance), risk-free rates (FRED) |
| **Non-trivial database** | SQLite with market data caching and scheduled refresh |
| **Own API** | FastAPI with CORS, Pydantic schemas, rate-limit-ready architecture |
| **Web frontend / UX** | Vue 3 responsive dashboard with 3D surfaces, dark mode, AI panels |
| **Advanced visualization** | Interactive implied vol surface, price surface, sensitivity chart |

Project 2.7 requirements:

| Requirement | Status |
|-------------|--------|
| Volatility surface modeling | ✅ Complete — live AAPL chain, Brent's root-finding, 3D plot |
| All Greeks | ✅ Complete — Δ, Γ, ν, Θ, ρ analytical + numerical fallback |
| Advanced pricing method | ✅ Complete — Monte Carlo, Binomial Tree, Longstaff-Schwartz, Heston, BAW |
| LLM explanation (nice to have) | ✅ Complete — Gemini, level-adaptive |
| Web dashboard (nice to have) | ✅ Complete — Vue 3 on Vercel |
| Vol surface visualization (nice to have) | ✅ Complete — interactive 3D |

---

## AI Contribution

This project was developed as an agentic project. AI tools contributed throughout:

- **Claude Code (Anthropic)** — pricing engine implementation, Greeks, exotic options, Longstaff-Schwartz, Heston, test suite, API design, documentation
- **Gemini 2.5 Flash (Google)** — in-app AI explanation and chat features
- **GitHub Copilot** — code completion during frontend development

See [`AGENTS.md`](AGENTS.md) for the full description of how AI agents contributed to the development workflow. All AI-assisted pull requests are documented in the commit history.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/user-guide.md`](docs/user-guide.md) | Step-by-step guide to the web app — inputs, outputs, AI features, surfaces |
| [`docs/api.md`](docs/api.md) | Full REST API reference — all endpoints, request/response schemas, examples |
| [`docs/specs/`](docs/specs/) | Internal design specs used during development |

---

*Last updated: May 2026 · [GitHub](https://github.com/MADSIAH/option_pricing_platform) · [Live App](https://option-pricing-platform.vercel.app)*
