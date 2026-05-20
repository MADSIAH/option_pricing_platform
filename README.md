# Option Pricing Platform

> **Programming in Finance II — Big Projects 2026**
> Project 2.7 · Università della Svizzera Italiana (USI)

![Status](https://img.shields.io/badge/status-work%20in%20progress-yellow)
![Stack](https://img.shields.io/badge/stack-TBD-lightgrey)
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

### Web Frontend & Dashboards

- Responsive UI with dedicated pricing and Greeks workflows
- Users can select a ticker to load real market data (spot, rates, vol) or define a fully custom underlying
- Desktop-first; mobile-friendly target
- Advanced parameters expanded by default for faster input access
- Sensitivity chart legend displayed above the plot for clarity
- Current-spot marker label rendered above the plot with padding to avoid clipping
- Sensitivity chart x-axis locked to the computed range so curves reach both edges
- Light/dark mode toggle in the header with persisted preference

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

- **AI-powered explanations** — an LLM agent that interprets pricing outputs and Greeks in natural language, adapting depth to the user's stated level (`beginner`, `finance student`, `professional trader`)
- **Trading strategy assistant** — a conversational agent that maps pricing analysis to common option strategies (covered calls, straddles, spreads) based on user-defined objectives and risk tolerance
- **Advanced interactive visualization** — richer surface plots, payoff diagram builder, scenario analysis tools
- **Exotic and crypto option extensions** — widen the financial scope beyond vanilla European contracts
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
| LLM integration | _TBD_ | Nice to have |
| Database | SQLite | Completed |
| Deployment | _TBD_ | — |

---

## Repository Structure

```

├── docs/           #  Design specs and system documentation
│
├── frontend/     
│ └── src/
│ ├── components/   # UI components (inputs, charts, displays)
│ └── lib/ 
│
├── src/
│ ├── api/          # FastAPI app, schemas, and route handlers
│ ├── data/         # Data layer (DB access + schedulers)
│ └── pricing/      # Pricing engine (all models + Greeks)
│
├── scripts/        # Utility scripts
├── notebooks/      # Prototyping notebook
│
├── tests/          # Unit tests for pricing models
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
- [ ] Web dashboard with pricing workflows
- [ ] Interactive charts and volatility surface visualization

### Phase 4 — Polish & Extensions
- [ ] Mobile UX refinement 
- [ ] LLM explanation module *(nice to have)*
- [ ] Exotic options or crypto extensions *(nice to have)*
- [ ] Trading strategy assistant *(nice to have)*

---

## AI Contribution

The project will be developed on GitHub with regular commits and documentation updates. At least one AI-supported pull request is planned per course requirements. An `AGENTS.md` file describes how AI tools contribute to the development workflow.

---

*Work in progress — last updated May 15, 2026.*
