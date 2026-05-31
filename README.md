# OptionDesk — AI-Enhanced Options Pricing Platform

> **Programming in Finance II — Big Projects 2026**  
> Project 2.7 · Università della Svizzera Italiana (USI)  
> Mantovani Sara · Nicol Massimiliano · Pescio Vittoria · Rocco Elena

![Status](https://img.shields.io/badge/status-complete-brightgreen)
![Tests](https://img.shields.io/badge/tests-97%20passing-brightgreen)
![Stack](https://img.shields.io/badge/stack-Vue3%20%7C%20FastAPI%20%7C%20Python-blue)
![Live](https://img.shields.io/badge/live-option--pricing--platform.vercel.app-emerald)

An educational, AI-enhanced platform for options pricing, Greeks analysis, volatility surface modeling, and natural-language explanation of results — built for students and practitioners alike.

**Live demo:** [option-pricing-platform.vercel.app](https://option-pricing-platform.vercel.app)  
**How to use the platform:** [User Guide](docs/user-guide.md)

---

## Why this platform?

Standard finance courses cover derivatives pricing thoroughly — but less attention is given to how models behave when applied to real market data. OptionDesk bridges that gap: state-of-the-art pricing on real companies, paired with live market data visualisations that make the divergence between model and market visible and instructive. An AI assistant helps interpret every result, adapting to the user's level — a platform built for anyone who wants to understand options.

---

## Overview

OptionDesk is a full-stack options pricing platform built around five models — Black-Scholes, Monte Carlo (GBM, antithetic variates), Cox-Ross-Rubinstein binomial tree, Longstaff-Schwartz (Monte Carlo + OLS regression for American early exercise), and Barone-Adesi-Whaley — each returning a complete Greek profile (Δ, Γ, ν, Θ, ρ) via analytical formulas or numerical central differences.

The data layer (SQLite + APScheduler) fetches live spot prices, dividend yields, and full option chains with implied volatilities from Yahoo Finance, plus the risk-free rate from FRED (TB3MS). Intraday data refreshes hourly and the risk-free rate daily, with snapshots persisted in a local database.

The FastAPI backend exposes a REST API consumed by a Vue 3 frontend deployed on Vercel. The UI renders interactive pricing tables, Greek sensitivity charts, and 3D volatility and price surfaces that juxtapose model output against live market quotes — making model-market divergence directly visible.

A Gemini-powered AI assistant interprets every pricing result in natural language, adapting its explanation depth to the user's declared level (beginner, finance student, professional), and supports open-ended follow-up via a persistent chat interface.

---

## Features

### Pricing Engine

Five models covering European and American options

| Model | Type | Options |
|-------|------|---------|
| Black-Scholes (BS) | Closed-form analytical | European |
| Monte Carlo (MC) | GBM simulation, antithetic variates, 50 000 paths | European |
| Cox-Ross-Rubinstein (CRR) | Binomial lattice | European + American |
| Longstaff-Schwartz (LSM) | Monte Carlo + OLS regression | American |
| Barone-Adesi-Whaley (BAW) | Analytical approximation | American |

All numerical models are cross-validated against Black-Scholes and converge within 1% ATM. Continuous dividend yield `q` is supported across all models.

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

Two AI-powered features (Gemini 3.1 Lite Flash):

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
- Stock selector: AAPL, TSLA, SPY or manual input
- European / American style toggle
- Method selector with real-time comparison table
- Interactive sensitivity chart (price vs spot)
- Implied volatility surface (3D) and price surface vs market data(3D)
- Light / Dark mode with persisted preference
- Responsive layout (desktop-first, mobile-friendly)

### Real-Time Market Data

- Equity prices and option chains via `yfinance`
- Risk-free rates via FRED API (TB3MS — 3-Month Treasury Bill)
- Scheduled refresh via `APScheduler` (intraday data hourly; risk-free rate and daily closes once a day)
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
│       ├── greeks.py               # AnalyticalGreeks + NumericalGreeks
│       ├── vol_surface.py          # implied_vol(), build_vol_surface()
│       ├── path_simulator.py       # GBMPathSimulator (Longstaff-Schwartz)
│       └── __init__.py
│
├── tests/                          # pytest test suite (97 passing)
│   ├── test_monte_carlo.py
│   ├── test_binomial_tree.py
│   ├── test_greeks.py
│   ├── test_vol_surface.py
│   ├── test_longstaff_schwartz.py
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


## API Documentation

Interactive docs (Swagger UI): [http://209.38.239.83:8000/docs](http://209.38.239.83:8000/docs) — full reference: [`docs/api.md`](docs/api.md)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health check |
| `GET` | `/api/v1/market/{ticker}` | Spot price, risk-free rate, historical vol, dividend yield |
| `GET` | `/api/v1/option_chain/{ticker}` | Full option chain |
| `GET` | `/api/v1/vol_surface/{ticker}` | Implied volatility surface |
| `POST` | `/api/v1/price` | Price an option with any model, returns Greeks |
| `POST` | `/api/v1/price_surface` | Price surface over a K × T grid |
| `POST` | `/api/v1/greeks_profile` | Greeks swept over a range of S or T |
| `POST` | `/api/v1/ai/explain` | Explain a pricing result in natural language |
| `POST` | `/api/v1/ai/chat` | Options assistant chat |

---

## Usage Examples

### Web interface

Open [option-pricing-platform.vercel.app](https://option-pricing-platform.vercel.app) — no setup required. A full walkthrough of every feature is in the [User Guide](docs/user-guide.md).

### Check the API is running

```bash
curl http://209.38.239.83:8000/api/v1/health
# {"status":"ok","db_reachable":true}
```

### REST API — curl

```bash
# Get live market data for a ticker
curl http://209.38.239.83:8000/api/v1/market/AAPL

# Price a European call with all models
curl -X POST http://209.38.239.83:8000/api/v1/price \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "K": 215, "T": 0.25, "option_type": "call", "style": "european", "method": "all"}'

# Get the implied volatility surface
curl http://209.38.239.83:8000/api/v1/vol_surface/AAPL
```

---

## Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run only the pricing engine tests
python -m pytest tests/test_monte_carlo.py tests/test_binomial_tree.py tests/test_greeks.py tests/test_vol_surface.py tests/test_longstaff_schwartz.py tests/test_baw.py -v

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
| Longstaff-Schwartz | 13 | American ≥ European put, call ≈ European (no div), BT agreement |
| BAW | varies | BAW ≥ European, American put early exercise |
| AI (explain, chat) | 16 | Message structure, level injection, system prompt usage |

---

## Deployment

There are three levels of deployment, depending on how much you want to run yourself.

### Level 1 — Use the live platform

Everything is already running. Just open the app:

- **Frontend:** [option-pricing-platform.vercel.app](https://option-pricing-platform.vercel.app)
- **API:** `http://209.38.239.83:8000/api/v1`

No setup required.

### Level 2 — Redeploy the frontend only

Fork the repository and deploy `frontend/` to Vercel. The frontend will point at our live API automatically via the existing `vercel.json` rewrite rules. No API key or server needed.

```bash
cd frontend
npm run build   # produces dist/
```

To point at a different API, set `VITE_API_URL` in `frontend/.env.local`:

```env
VITE_API_URL=http://your-api-host/api/v1
```

### Level 3 — Full self-hosting (own VPS + own API key)

**Prerequisites:** Python 3.11 or 3.12, Node.js 18+, a Google Gemini API key (free tier).

The backend runs as two separate persistent processes on an Ubuntu VPS, each in its own `screen` session.

```bash
# Clone, create venv, and install
git clone https://github.com/MADSIAH/option_pricing_platform.git
cd option_pricing_platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Scheduler screen — populates and refreshes the SQLite database
screen -S scheduler
cd ~/option_pricing_platform
source venv/bin/activate
python3 -m src.data.scheduler
# Ctrl+A D to detach (Ctrl+C to stop)

# API screen — serves the FastAPI application
screen -S api
cd ~/option_pricing_platform
source venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# Ctrl+A D to detach (Ctrl+C to stop)
```

To reattach to a running session: `screen -r scheduler` or `screen -r api`.

> Both processes must run concurrently. The scheduler populates the database on startup and keeps it fresh; without it the API returns 404 for every ticker.

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
| Advanced pricing method | ✅ Complete — Monte Carlo, Binomial Tree, Longstaff-Schwartz, BAW |
| LLM explanation (nice to have) | ✅ Complete — Gemini, level-adaptive |
| Web dashboard (nice to have) | ✅ Complete — Vue 3 on Vercel |
| Vol surface visualization (nice to have) | ✅ Complete — interactive 3D |

---

## AI Contribution

This project was developed as an agentic project. AI tools contributed throughout:

- **Claude Code (Anthropic)** — pricing engine implementation, Greeks, Longstaff-Schwartz, test suite, API design, documentation
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
