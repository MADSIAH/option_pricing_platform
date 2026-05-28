# Option Pricing Platform

> **Programming in Finance II — Big Projects 2026**
> Project 2.7 · Università della Svizzera Italiana (USI)

![Status](https://img.shields.io/badge/status-work%20in%20progress-yellow)
![Stack](https://img.shields.io/badge/stack-Vue3%20%7C%20FastAPI%20%7C%20Python-blue)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

An educational, AI-enhanced platform for options pricing, Greeks analysis, volatility surface modeling, and interactive financial visualization — built for learners and practitioners alike.

---

## Table of Contents

- [Option Pricing Platform](#option-pricing-platform)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Target Users](#target-users)
  - [Core Features](#core-features)
    - [Option Pricing Engine](#option-pricing-engine)
    - [Greeks](#greeks)
    - [Volatility Surface](#volatility-surface)
    - [Price surface](#price-surface)
    - [Web Frontend \& Dashboards](#web-frontend--dashboards)
    - [Real-Time Data Ingestion](#real-time-data-ingestion)
    - [API Layer](#api-layer)
  - [Nice to Have](#nice-to-have)
  - [Tech Stack](#tech-stack)
  - [Repository Structure](#repository-structure)
  - [Roadmap](#roadmap)
    - [Phase 1 — Core Engine](#phase-1--core-engine)
    - [Phase 2 — Numerical Methods \& Data](#phase-2--numerical-methods--data)
    - [Phase 3 — Frontend \& API](#phase-3--frontend--api)
    - [Phase 4 — Polish \& Extensions](#phase-4--polish--extensions)
  - [AI Contribution](#ai-contribution)

---

## Overview

Options pricing sits at the intersection of mathematics, statistics, and market microstructure. Understanding it requires not just computing a number, but grasping how model inputs — spot price, strike, maturity, implied volatility, risk-free rate — interact and what each Greek reveals about risk exposure.

This platform makes that understanding tangible. It computes option prices using both analytical and numerical methods, calculates the full Greek profile, constructs and visualizes the implied volatility surface, and explains outputs in natural language adapted to the user's background.

---

## Target Users

The platform is primarily **didactic**. It is designed for:

| User | Goal |
|------|------|
| **Finance students** | Build intuition for derivatives pricing and risk sensitivities |
| **Course practitioners** | Validate theoretical models against live market data |
| **Self-learners** | Explore options mechanics through an interactive, guided interface |

---

## Core Features

### Option Pricing Engine

Available methods:

|  | **European options** | **American options** |
|---|---|---|
| Closed-form | Black-Scholes (BS) | Barone-Adesi-Whaley (BAW) |
| Simulations | Montecarlo (MC) | Longstaff-Schwartz |
| Binomial Trees | Cox-Ross-Rubinstein (CRR) | Cox-Ross-Rubinstein (CRR) |
### Greeks

All five main sensitivities computed for every pricing result:

| Greek | Sensitivity to |
|-------|---------------|
| Delta | Spot price |
| Gamma | Delta (second-order spot) |
| Vega  | Implied volatility |
| Theta | Time to expiry |
| Rho   | Risk-free interest rate |

### Volatility Surface

- Surface constructed across strike and maturity dimensions
- Interactive 3D visualization via the web frontend

### Price surface
- Surface constructed using closed-form solution.
- Interactive 3D visualization comparing model and market option prices.

### AI Features

Two AI-powered features powered by Gemini are available in the UI:

**Pricing & Greeks — AI Explanation**
- Triggered from the Pricing & Greeks tab after a result is computed
- Explains the option price and Greeks in natural language
- User selects their level (Beginner / Finance Student / Professional) to adapt depth and terminology
- Endpoint: `POST /api/v1/ai/explain`

**Surfaces — AI Surface Analysis**
- Triggered from the Surfaces tab once both the vol surface and price surface have loaded
- Frontend silently computes a set of metrics as soon as the charts render: volatility smile intensity, put-side skew, IV spike detection (z-score within adaptive maturity × moneyness buckets), model-vs-market price divergence per bucket, deep-ITM bias, and liquidity distribution
- These metrics are sent to the backend, which builds a structured prompt and calls Gemini
- Response is a plain-prose narrative: model fit, smile shape, irregular patches, liquidity caveats, and cross-surface observations
- Endpoint: `POST /api/v1/ai/explain_surfaces`

**Options Assistant (Chat)**
- Persistent chat panel accessible from the navigation bar
- Free-form Q&A about options, Greeks, and pricing models
- Maintains conversation history within the session
- Endpoint: `POST /api/v1/ai/chat`

### Web Frontend & Dashboards

- Responsive UI with dedicated pricing and Greeks workflows
- Users can select a ticker to load real market data (spot, rates, vol) or define a fully custom underlying
- Desktop-first; mobile-friendly target
- Advanced parameters expanded by default for faster input access
- Sensitivity chart legend displayed above the plot for clarity
- Current-spot marker label rendered above the plot with padding to avoid clipping
- Sensitivity chart x-axis locked to the computed range so curves reach both edges
- Light/dark mode toggle in the header with persisted preference
- Mobile header wraps pills and toggle with extra spacing on small screens
- Selecting “Other” refreshes the risk-free rate while keeping manual inputs open

### Real-Time Data Ingestion

- Equity and option data via `yfinance`
- Risk-free rates via the FRED API
- Scheduled refresh every 60 minutes via `APScheduler`

### API Layer

- Built with FastAPI
- Exposes pricing, market data, and visualization endpoints
- Serves market data from DB and runs all option pricing and Greeks computations
  
---

## Nice to Have

These are stretch goals — planned but not guaranteed for the final release:

- **Trading strategy assistant** — a conversational agent that maps pricing analysis to common option strategies (covered calls, straddles, spreads) based on user-defined objectives and risk tolerance
- **Advanced interactive visualization** — richer surface plots, payoff diagram builder, scenario analysis tools
- **Mobile-optimized experience** — full responsiveness beyond basic layout adaptation

---

## Tech Stack

> **Status: TBD** — final technology choices will be documented here as decisions are confirmed.

| Layer | Technology | Status |
|-------|-----------|--------|
| Pricing engine | Python (NumPy, SciPy) | Completed |
| API / Web framework | FastAPI + Uvicorn | Completed |
| Frontend framework | Vue 3 + Vite + Tailwind CSS | WIP |
| Data ingestion | `yfinance`, FRED API | Completed |
| Scheduling | `APScheduler` | Completed |
| LLM integration | Gemini (via Google AI API) | Completed |
| Database | SQLite | Completed |
| Deployment | _TBD_ | — |

---

## Repository Structure

```
├── docs/           # Design specs and system documentation
│
├── frontend/
│   └── src/
│       ├── components/         # UI components (inputs, charts, surfaces, AI panels)
│       └── lib/                # API client, composables (useSurfaceMetrics)
│
├── src/
│   ├── ai/                     # LLM integration (Gemini)
│   │   ├── prompts/            # System prompt text files
│   │   ├── client.py           # Gemini API wrapper
│   │   ├── explain.py          # Pricing result explanation
│   │   ├── explain_surfaces.py # Surface metrics explanation
│   │   └── chat.py             # Conversational assistant
│   ├── api/                    # FastAPI app, schemas, and route handlers
│   ├── data/                   # Data layer (DB access + schedulers)
│   └── pricing/                # Pricing engine (all models + Greeks)
│
├── scripts/        # Utility scripts
├── notebooks/      # Prototyping notebook
│
├── tests/          # Unit and integration tests
│
├── requirements.txt
└── README.md
```

---

## Roadmap

### Phase 1 — Core Engine
- [x] Repository setup
- [x] Black-Scholes, MonteCarlo and Binomial sample pricing for European options
- [x] Greeks computation
- [x] Baseline test suite

### Phase 2 — Numerical Methods & Data
- [x] Market data ingestion (`yfinance`, FRED)
- [x] Monte Carlo pricing
- [x] Binomial Tree pricing
- [x] Volatility surface construction

### Phase 3 — Frontend & API
- [x] Server setup
- [x] Data pipeline scheduler initialization
- [x] API layer (FastAPI — all endpoints running)
- [x] Web dashboard with pricing workflows
- [x] Interactive charts for pricing + Greeks
- [x] Volatility/price surface visualization in the UI

### Phase 4 — Polish & Extensions
- [x] Mobile UX refinement
- [x] Exotic options extensions
- [x] AI explanation for pricing results and Greeks
- [x] AI surface analysis (vol smile, model divergence, liquidity)
- [x] Interactive options assistant (chat)
- [ ] Trading strategy assistant *(nice to have)*

---

## AI Contribution

The project will be developed on GitHub with regular commits and documentation updates. At least one AI-supported pull request is planned per course requirements. An `AGENTS.md` file describes how AI tools contribute to the development workflow.

---

*Work in progress — last updated May 28, 2026.*
