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

The objective of this project is building an options pricing platform. The platform prices European options via Black-Scholes, Monte Carlo, and Binomial Tree methods; computes the full Greeks profile; constructs the implied volatility surface from live market data; and surfaces all of this through a web dashboard with an optional LLM explanation layer.

Currently at Phase 1: `notebooks/pricing.ipynb` implements Black-Scholes pricing on live AAPL data fetched from `yfinance` and FRED.

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

- Implied volatility extracted from live option chains
- Surface constructed across strike and maturity dimensions
- Interactive 3D visualization via the web frontend

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
- **American and crypto option extensions** — widen the financial scope beyond vanilla European contracts
- **Mobile-optimized experience** — full responsiveness beyond basic layout adaptation

---

## Pricing Methods

| Method | Type | Scope |
|--------|------|-------|
| Black-Scholes | Analytical (closed-form) | European options — reference baseline |
| Monte Carlo | Stochastic simulation | European; extensible to path-dependent payoffs |
| Binomial Tree | Lattice (discrete-time) | European and American options |

Black-Scholes serves as the benchmark: all numerical method outputs are validated against it wherever a closed-form solution exists.

---

## Tech Stack

> **Status: TBD** — final technology choices will be documented here as decisions are confirmed.

| Layer | Technology | Status |
|-------|-----------|--------|
| Pricing engine | Python (NumPy, SciPy) | Planned |
| Web framework | _TBD_ | — |
| Frontend | _TBD_ | — |
| API | _TBD_ | — |
| Data ingestion | `yfinance`, FRED API | Planned |
| Scheduling | `APScheduler` | Planned |
| LLM integration | _TBD_ | Nice to have |
| Database | _TBD_ | — |
| Deployment | _TBD_ | — |

---

## Repository Structure

```
option_pricing_platform/
├── README.md
└── notebooks/
    └── pricing.ipynb
```

---

## Roadmap

### Phase 1 — Core Engine
- [ ] Repository setup and project scaffolding
- [ ] Black-Scholes pricing for European calls and puts
- [ ] Greeks computation (all five)
- [ ] Baseline test suite

### Phase 2 — Numerical Methods & Data
- [ ] Monte Carlo pricing
- [ ] Binomial Tree pricing
- [ ] Volatility surface construction
- [ ] Market data ingestion (`yfinance`, FRED)

### Phase 3 — Frontend & AI
- [ ] Web dashboard with pricing workflows
- [ ] Interactive charts and volatility surface visualization
- [ ] LLM explanation module *(nice to have)*

### Phase 4 — API, Polish & Extensions
- [ ] Public-facing API with rate limiting
- [ ] Mobile UX refinement
- [ ] American options and/or crypto extensions *(nice to have)*
- [ ] Trading strategy assistant *(nice to have)*

---

## AI Contribution

The project will be developed on GitHub with regular commits and documentation updates. At least one AI-supported pull request is planned per course requirements. An `AGENTS.md` file describes how AI tools contribute to the development workflow.

---

*Work in progress — last updated April 2026.*
