# AI-Enhanced Options Pricing Platform

> **Programming in Finance II — Big Projects 2026**
> Project 2.7 · Università della Svizzera italiana (USI)

A production-grade platform for advanced options pricing, volatility surface modeling, and AI-assisted analysis. Built as an agentic project where AI agents contribute meaningfully to development and user interaction.

---

## Overview

This platform implements state-of-the-art options pricing models alongside machine learning tools for volatility surface calibration and an LLM-powered explanation layer. It is designed for quantitative analysts, students, and practitioners who want both rigorous pricing and intuitive interpretation of results.

**Core capabilities:**

- Options pricing via Monte Carlo simulations, Binomial Trees, and FFT-based methods (Carr-Madan)
- Full Greeks calculation (Delta, Gamma, Vega, Theta, Rho)
- Volatility surface modeling and visualization (implied volatility, local vol, SVI parametrization)
- LLM-powered natural language explanations of pricing results and risk metrics
- Interactive web dashboard with real-time market data integration
- REST API with authentication and rate limiting

---

## Project Structure

```
option_pricing_platform/
├── AGENTS.md                  # AI agent instructions and contribution rules
├── README.md
├── requirements.txt
├── .env.example
│
├── api/                       # REST API (FastAPI)
│   ├── main.py
│   ├── auth.py
│   ├── routes/
│   │   ├── pricing.py
│   │   ├── volatility.py
│   │   └── explain.py
│   └── models/
│
├── core/                      # Pricing engine
│   ├── black_scholes.py       # Closed-form BS model
│   ├── monte_carlo.py         # Monte Carlo simulations
│   ├── binomial_tree.py       # CRR binomial tree
│   ├── fft_pricing.py         # Carr-Madan FFT method
│   ├── greeks.py              # Greeks computation
│   └── volatility/
│       ├── implied_vol.py     # IV solver (Brent's method)
│       ├── surface.py         # Volatility surface construction
│       └── svi.py             # SVI parametrization
│
├── ml/                        # Machine learning models
│   ├── vol_surface_ml.py      # ML-based vol surface fitting
│   └── calibration.py        # Model calibration utilities
│
├── llm/                       # LLM integration layer
│   ├── explainer.py           # Natural language explanations
│   └── prompts/               # Prompt templates
│
├── data/                      # Market data ingestion
│   ├── fetcher.py             # Live data via yfinance / IBKR
│   └── database.py            # PostgreSQL + vector store
│
├── frontend/                  # Web dashboard (Streamlit / React)
│   ├── app.py
│   └── components/
│
├── tests/
│   ├── test_pricing.py
│   ├── test_greeks.py
│   └── test_api.py
│
└── docs/                      # Additional technical documentation
```

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- An API key for an LLM provider (OpenAI, Anthropic, or local Ollama)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/option_pricing_platform.git
cd option_pricing_platform
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

Required variables:

```
DATABASE_URL=postgresql://user:password@localhost:5432/options_db
LLM_PROVIDER=anthropic          # or openai / ollama
LLM_API_KEY=your_key_here
MARKET_DATA_SOURCE=yfinance     # or ibkr
API_SECRET_KEY=your_secret
```

### 5. Initialize the database

```bash
python -m data.database --init
```

### 6. Run the platform

```bash
# Start the API server
uvicorn api.main:app --reload --port 8000

# Start the web dashboard (separate terminal)
streamlit run frontend/app.py
```

---

## Usage

### Web Dashboard

Navigate to `http://localhost:8501` after starting the frontend. You can:

- Enter an underlying ticker and option parameters
- Select a pricing model (Monte Carlo, Binomial Tree, FFT)
- View the full volatility surface in 3D
- Read AI-generated explanations of the pricing output and Greeks

### REST API

Base URL: `http://localhost:8000`

#### Price an option

```http
POST /api/v1/price
Authorization: Bearer <token>
Content-Type: application/json

{
  "ticker": "AAPL",
  "option_type": "call",
  "strike": 200.0,
  "expiry": "2025-06-20",
  "method": "monte_carlo",
  "n_simulations": 100000
}
```

Response:

```json
{
  "price": 12.45,
  "greeks": {
    "delta": 0.623,
    "gamma": 0.031,
    "vega": 0.184,
    "theta": -0.052,
    "rho": 0.089
  },
  "implied_volatility": 0.28,
  "explanation": "The call option is priced at $12.45 with a delta of 0.62, meaning..."
}
```

#### Get volatility surface

```http
GET /api/v1/volatility/surface?ticker=AAPL
Authorization: Bearer <token>
```

#### Authenticate

```http
POST /api/v1/auth/token
Content-Type: application/json

{ "username": "user", "password": "password" }
```

### Python API

```python
from core.monte_carlo import MonteCarloEngine
from core.greeks import compute_greeks

engine = MonteCarloEngine(S=180, K=200, T=0.25, r=0.05, sigma=0.28)
price = engine.price(option_type="call", n_simulations=100_000)
greeks = compute_greeks(S=180, K=200, T=0.25, r=0.05, sigma=0.28)
print(f"Price: {price:.4f} | Delta: {greeks['delta']:.4f}")
```

---

## Pricing Methods

| Method | Description | Best For |
|---|---|---|
| Black-Scholes | Closed-form analytical solution | European vanilla options, benchmarking |
| Monte Carlo | GBM path simulation with variance reduction | Exotic options, path-dependent payoffs |
| Binomial Tree | CRR discrete lattice | American options, dividends |
| FFT (Carr-Madan) | Fast Fourier Transform in characteristic function space | Lévy process models (Heston, VG) |

---

## Volatility Surface

The platform constructs the implied volatility surface from market option chains:

1. **Data ingestion** — fetch live option chain quotes for multiple expiries
2. **IV solver** — invert option prices using Brent's root-finding method
3. **Surface interpolation** — SVI parametrization for arbitrage-free interpolation
4. **ML calibration** — neural network for fast re-calibration on new market data

---

## AI Features

- **LLM explanations** — after every pricing call, the platform generates a plain-language summary of the result, contextualizing the Greeks and model assumptions
- **Agentic development** — see `AGENTS.md` for how AI agents contribute to this repository via pull requests

---

## Testing

```bash
pytest tests/ -v --cov=core --cov=api
```

---

## Technical Stack

| Layer | Technology |
|---|---|
| Pricing engine | Python, NumPy, SciPy |
| API | FastAPI, Pydantic |
| Database | PostgreSQL, pgvector |
| LLM | Anthropic Claude / OpenAI GPT |
| Market data | yfinance, Interactive Brokers API |
| Frontend | Streamlit (or React + Plotly) |
| Deployment | Docker, cloud VPS |

---

## Academic Context

This project is submitted for **Programming in Finance II (2026)** at USI, supervised by Prof. Peter H. Gruber. It satisfies the advanced component requirements by integrating:

- A large language model (LLM) for AI-enhanced explanations
- A non-trivial database (PostgreSQL with vector store)
- Real-time market data processing
- A web frontend with focus on user experience

Use of generative AI tools is acknowledged in the academic PDF documentation.

---

## License

MIT License — see `LICENSE` for details.
