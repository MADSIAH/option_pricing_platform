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
    - [Web Frontend \& Dashboards](#web-frontend--dashboards)
    - [Real-Time Data Ingestion](#real-time-data-ingestion)
    - [API Layer](#api-layer)
  - [Nice to Have](#nice-to-have)
  - [Pricing Methods](#pricing-methods)
  - [Tech Stack](#tech-stack)
  - [Repository Structure](#repository-structure)
  - [Roadmap](#roadmap)
    - [Phase 1 — Core Engine](#phase-1--core-engine)
    - [Phase 2 — Numerical Methods \& Data](#phase-2--numerical-methods--data)
    - [Phase 3 — Frontend \& AI](#phase-3--frontend--ai)
    - [Phase 4 — API, Polish \& Extensions](#phase-4--api-polish--extensions)
  - [AI Contribution](#ai-contribution)

---

## Overview

The objective of this project is building an options pricing platform. The platform prices options via Black-Scholes, Monte Carlo, and Binomial Tree methods; computes the full Greeks profile; constructs the implied volatility surface from live market data; and surfaces all of this through a web dashboard with an optional LLM explanation layer.

**Phases 1 & 2 complete.** The pricing engine, Greeks, and implied volatility surface are fully implemented and tested (47 passing tests). `notebooks/pricing.ipynb` demonstrates all three pricing methods on live AAPL data with convergence plots, a full Greeks table and delta-vs-spot chart, and a 3D implied volatility surface. Continuous dividend yield (`q`) is supported across all models via the Merton extension.

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

- Black-Scholes analytical pricing for European calls and puts (baseline benchmark)
- Monte Carlo simulation for path-dependent and European payoffs
- Binomial Tree pricing for European and American options
- Side-by-side comparison of results across methods

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

- Implied volatility extracted from live option chains via Brent's root-finding on the BS price
- Surface constructed across strike and maturity dimensions, interpolated to a continuous grid
- 3D visualization in the notebook; interactive dashboard planned for the web frontend

> **Update:** Option-chain cleaning is now part of the volatility pipeline (`src/pricing/vol_surface.py`) with default filters for minimum time-to-expiry, bid-ask relative spread, moneyness range, and liquidity (volume/open interest when available). A smoothing/arbitrage-free post-processing pass is still planned as a future improvement.

### Web Frontend & Dashboards

- Clean, responsive UI with dedicated pricing and Greeks workflows
- Interactive charts for sensitivity analysis and surface exploration
- Desktop-first; mobile-friendly target

### Real-Time Data Ingestion

- Equity and option data via `yfinance`
- Risk-free rates via the FRED API
- Scheduled refresh every 10–60 minutes via `APScheduler`

### API Layer

- Internal API exposing pricing and volatility endpoints
- Rate limiting as baseline protection
- Architecture kept open for future authentication

---

## Nice to Have

These are stretch goals — planned but not guaranteed for the final release:

- **AI-powered explanations** — an LLM agent that interprets pricing outputs and Greeks in natural language, adapting depth to the user's stated level (`beginner`, `finance student`, `professional trader`)
- **Trading strategy assistant** — a conversational agent that maps pricing analysis to common option strategies (covered calls, straddles, spreads) based on user-defined objectives and risk tolerance
- **Advanced interactive visualization** — richer surface plots, payoff diagram builder, scenario analysis tools
- **Dividend yield support** ✓ — all three pricing models, Greeks, and implied vol accept a continuous dividend yield `q` (Merton extension)
- **American options — full framework** *(TBD)* — Binomial Tree already prices American puts via early-exercise flag; planned extension covers BS approximations (e.g. Barone-Adesi-Whaley) and American calls on dividend-paying stocks
- **Crypto option extensions** — widen scope beyond vanilla equity contracts
- **Mobile-optimized experience** — full responsiveness beyond basic layout adaptation

---

## Pricing Methods

| Method | Type | Scope |
|--------|------|-------|
| Black-Scholes | Analytical (closed-form) | European options — reference baseline |
| Monte Carlo | Stochastic simulation | European; extensible to path-dependent payoffs |
| Binomial Tree | Lattice (discrete-time) | European options |

Black-Scholes serves as the benchmark: all numerical method outputs are validated against it wherever a closed-form solution exists.

---

## Tech Stack

> **Status: TBD** — final technology choices will be documented here as decisions are confirmed.

| Layer | Technology | Status |
|-------|-----------|--------|
| Pricing engine | Python (NumPy, SciPy) | **Done** |
| Testing | `pytest` | **Done** |
| Web framework | _TBD_ | — |
| Frontend | _TBD_ | — |
| API | _TBD_ | — |
| Data ingestion | `yfinance`, FRED API | Done (notebook) |
| Scheduling | `APScheduler` | Planned |
| LLM integration | _TBD_ | Nice to have |
| Database | _TBD_ | — |
| Deployment | _TBD_ | — |

---

## Repository Structure

```
option_pricing_platform/
├── CLAUDE.md                        ← AI contributor context
├── AGENTS.md                        ← AI usage policy and validation workflow
├── README.md
├── src/
│   └── pricing/
│       ├── base.py                  ← OptionParams, PricingResult, PricingModel ABC
│       ├── utils.py                 ← shared d1/d2 (with dividend yield q)
│       ├── black_scholes.py         ← BlackScholes (reference benchmark)
│       ├── monte_carlo.py           ← MonteCarlo (antithetic variates)
│       ├── binomial_tree.py         ← BinomialTree (CRR, American exercise)
│       ├── greeks.py                ← AnalyticalGreeks (BS), NumericalGreeks (central diff)
│       └── vol_surface.py           ← implied_vol (brentq), build_vol_surface
├── tests/
│   ├── test_monte_carlo.py
│   ├── test_binomial_tree.py
│   ├── test_greeks.py
│   └── test_vol_surface.py
├── notebooks/
│   └── pricing.ipynb                ← AAPL demo: pricing, Greeks, vol surface
├── .claude/
│   └── skills/
│       └── option-pricing-methods.md
└── docs/
    └── superpowers/specs/
        ├── 2026-04-22-option-pricing-skills-design.md
        └── 2026-04-26-dividend-yield-design.md
```

---

## Roadmap

### Phase 1 — Core Engine
- [x] Repository setup and project scaffolding
- [x] Black-Scholes pricing for European calls and puts (`src/pricing/black_scholes.py`)
- [x] Monte Carlo pricing with antithetic variates (`src/pricing/monte_carlo.py`)
- [x] Binomial Tree pricing — European + American (`src/pricing/binomial_tree.py`)
- [x] Notebook demo with plots and method comparison (`notebooks/pricing.ipynb`)
- [x] Baseline test suite (14 passing tests)

### Phase 2 — Numerical Methods & Data
- [x] Market data ingestion (`yfinance`, FRED)
- [x] Greeks: analytical BS (Merton) + central-difference fallback for MC/BT
- [x] Continuous dividend yield `q` across all models and Greeks
- [x] Volatility surface construction (implied vol via Brent's method, 47 passing tests)
- [x] Option chain cleaning before IV calculation — minimum T cutoff, spread threshold, moneyness range, and liquidity filters integrated in `src/pricing/vol_surface.py`
- [ ] American options — full framework beyond BT flag *(TBD)*

### Phase 3 — Frontend & AI
- [ ] Web dashboard with pricing workflows
- [ ] Interactive charts and volatility surface visualization
- [ ] LLM explanation module *(nice to have)*

### Phase 4 — API, Polish & Extensions
- [ ] Public-facing API with rate limiting
- [ ] Mobile UX refinement
- [ ] Crypto, American and Exotic option extensions *(nice to have)*
- [ ] Trading strategy assistant *(nice to have)*

---

## AI Contribution

The project will be developed on GitHub with regular commits and documentation updates. At least one AI-supported pull request is planned per course requirements. An `AGENTS.md` file describes how AI tools contribute to the development workflow.

---

*Work in progress — last updated April 2026.*
