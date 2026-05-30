# API Reference — OptionDesk

**Base URL (production):** `https://option-pricing-platform.vercel.app/api/v1`  
**Base URL (local):** `http://localhost:8000/api/v1`

All endpoints return JSON. POST endpoints accept `application/json`.

---

## Table of Contents

1. [Health](#1-health)
2. [Market Data](#2-market-data)
3. [Price & Greeks](#3-price--greeks)
4. [Implied Volatility Surface](#4-implied-volatility-surface)
5. [Price Surface](#5-price-surface)
6. [AI — Explain](#6-ai--explain)
7. [AI — Chat](#7-ai--chat)
8. [Enumerations](#enumerations)
9. [Error Responses](#error-responses)
10. [Python Examples](#python-examples)

---

## 1. Health

### `GET /health`

Returns backend status and database connectivity.

**Response**

```json
{
  "status": "ok",
  "db_reachable": true
}
```

---

## 2. Market Data

### `GET /market/{ticker}`

Returns live market data for a given ticker, sourced from the database (updated hourly by the background scheduler).

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticker` | string | Stock ticker symbol (e.g. `AAPL`, `SPY`, `TSLA`) |

**Response**

```json
{
  "ticker": "AAPL",
  "spot_price": 213.49,
  "historical_vol": 0.2831,
  "historical_vol_warning": null,
  "atm_implied_vol": 0.2514,
  "risk_free_rate": 0.0442,
  "risk_free_rate_warning": null,
  "dividend_yield": 0.0051,
  "updated_at": "2026-05-30T14:23:11Z",
  "stale": false,
  "data_source": "database"
}
```

**Notes**
- All rate/vol fields are in **decimal** form (e.g. `0.045` = 4.5%).
- `stale: true` means the data is older than 15 minutes.
- `historical_vol` is 30-day realised volatility computed from daily log returns.
- `atm_implied_vol` is the at-the-money implied vol from the nearest expiry option chain.
- `dividend_yield` is the continuous annualised dividend yield.

---

## 3. Price & Greeks

### `POST /price`

Prices a European or American option and returns Greeks. When `method = "all"`, all models valid for the requested style are computed in a single call.

**Request body**

```json
{
  "ticker": "AAPL",
  "S": 213.49,
  "K": 215.0,
  "T": 0.25,
  "r": 0.0442,
  "q": 0.0051,
  "sigma": 0.2514,
  "option_type": "call",
  "style": "european",
  "method": "all",
  "mc_paths": 50000
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ticker` | string | No | `null` | If provided, S/r/q/sigma may be omitted and resolved from the database |
| `S` | float | Yes* | — | Spot price of the underlying |
| `K` | float | Yes | — | Strike price (must be > 0) |
| `T` | float | Yes | — | Time to maturity in **years** (must be > 0) |
| `r` | float | Yes* | — | Risk-free rate in decimal (e.g. `0.045`) |
| `q` | float | Yes* | — | Continuous dividend yield in decimal |
| `sigma` | float | Yes* | — | Annualised volatility in decimal |
| `sigma_type` | string | No | `"historical"` | `"implied"` or `"historical"` — used when sigma is omitted |
| `option_type` | string | Yes | — | `"call"` or `"put"` |
| `style` | string | Yes | — | `"european"` or `"american"` |
| `method` | string | No | `"all"` | See [Enumerations](#enumerations) |
| `mc_paths` | int | No | `50000` | Monte Carlo path count (max 100 000) |

\* Required when `ticker` is not provided.

**Response**

```json
{
  "ticker": "AAPL",
  "option_type": "call",
  "style": "european",
  "method": "all",
  "S": 213.49,
  "K": 215.0,
  "T": 0.25,
  "r": 0.0442,
  "q": 0.0051,
  "sigma": 0.2514,
  "sigma_source": "provided",
  "sigma_fallback": false,
  "prices": {
    "black_scholes": {
      "price": 12.34,
      "greeks": {
        "delta": 0.4821,
        "gamma": 0.0134,
        "vega": 0.2891,
        "theta": -0.0512,
        "rho": 0.1923
      }
    },
    "monte_carlo": {
      "price": 12.29,
      "greeks": { "delta": 0.481, "gamma": 0.013, "vega": 0.288, "theta": -0.051, "rho": 0.191 }
    },
    "binomial_tree": {
      "price": 12.33,
      "greeks": { "delta": 0.482, "gamma": 0.013, "vega": 0.289, "theta": -0.051, "rho": 0.192 }
    }
  },
  "data_source": "provided",
  "updated_at": null,
  "stale": false
}
```

**Available methods by style**

| Style | Methods |
|-------|---------|
| `european` | `black_scholes`, `monte_carlo`, `binomial_tree` |
| `american` | `baw`, `longstaff_schwartz`, `binomial_tree` |

**Notes on Greeks**
- Delta: dimensionless, range approximately [0, 1] for calls and [-1, 0] for puts.
- Gamma: in units of Δ per dollar move in S.
- Vega: price change per 1 percentage point move in σ (i.e. per 0.01 in decimal).
- Theta: price change **per calendar day** (negative for long positions).
- Rho: price change per 1 percentage point move in r.

---

## 4. Implied Volatility Surface

### `GET /vol_surface/{ticker}`

Returns the implied volatility surface for a ticker, built from the stored option chain.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticker` | string | `AAPL`, `SPY`, or `TSLA` |

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `option_type` | string | `"call"` | `"call"` or `"put"` |

**Response**

```json
{
  "ticker": "AAPL",
  "points": [
    { "expiry": "2026-06-20", "T": 0.056, "strike": 200.0, "implied_vol": 0.2812 },
    { "expiry": "2026-06-20", "T": 0.056, "strike": 210.0, "implied_vol": 0.2534 }
  ],
  "grid": {
    "T_values": [0.056, 0.139, 0.306, 0.556],
    "K_values": [190.0, 200.0, 210.0, 215.0, 220.0],
    "z": [
      [0.31, 0.29, 0.27, null, 0.26],
      [0.28, 0.26, 0.25, 0.24, 0.23]
    ]
  },
  "updated_at": "2026-05-30T14:23:11Z",
  "stale": false,
  "data_source": "database"
}
```

- `points`: flat list of all (expiry, strike, IV) triples after chain cleaning.
- `grid.z[K_idx][T_idx]`: implied vol in decimal; `null` where insufficient data.
- `implied_vol` values are in **decimal** (e.g. `0.28` = 28%).

---

## 5. Price Surface

### `POST /price_surface`

Computes a model price surface on a strike × maturity grid for a given ticker. Uses Black-Scholes. Also returns market mid-prices from the stored option chain for comparison.

**Request body**

```json
{
  "ticker": "AAPL",
  "option_type": "call",
  "style": "european",
  "sigma_type": "implied",
  "K_min_frac": 0.75,
  "K_max_frac": 1.25,
  "n_K": 60,
  "n_T": 45
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ticker` | string | Yes | — | Ticker symbol |
| `option_type` | string | Yes | — | `"call"` or `"put"` |
| `style` | string | Yes | — | `"european"` or `"american"` |
| `sigma` | float | No | `null` | Override vol in decimal; if omitted, resolved by `sigma_type` |
| `sigma_type` | string | No | `"historical"` | `"implied"` or `"historical"` |
| `S` | float | No | `null` | Override spot price |
| `r` | float | No | `null` | Override risk-free rate |
| `q` | float | No | `null` | Override dividend yield |
| `K_min_frac` | float | No | `0.75` | Minimum strike as fraction of spot (must be ≤ 1.0) |
| `K_max_frac` | float | No | `1.25` | Maximum strike as fraction of spot (must be ≥ 1.0) |
| `n_K` | int | No | `60` | Number of strike grid points (10–100) |
| `n_T` | int | int | No | `45` | Number of maturity grid points (10–80) |

**Response**

```json
{
  "ticker": "AAPL",
  "option_type": "call",
  "style": "european",
  "S_ref": 213.49,
  "sigma": 0.2514,
  "sigma_source": "implied",
  "sigma_fallback": false,
  "K_values": [160.12, 161.23, "..."],
  "T_values": [0.05, 0.10, "..."],
  "z": [[12.1, 11.8, "..."], ["..."]],
  "market_points": [
    { "K": 210.0, "T": 0.056, "mid_price": 8.45, "volume": 1203, "open_interest": 5421 }
  ],
  "data_source": "database",
  "updated_at": "2026-05-30T14:23:11Z",
  "stale": false
}
```

- `z[T_idx][K_idx]`: model price in dollars.
- `market_points`: actual market mid-prices from the option chain (may be sparse).

---

## 6. AI — Explain

### `POST /ai/explain`

Generates a natural-language explanation of a pricing result. Powered by Gemini 2.5 Flash.

**Request body**

```json
{
  "user_level": "finance_student",
  "option_type": "call",
  "style": "european",
  "method": "black_scholes",
  "S": 213.49,
  "K": 215.0,
  "T": 0.25,
  "r": 0.0442,
  "sigma": 0.2514,
  "q": 0.0051,
  "prices": {
    "black_scholes": {
      "price": 12.34,
      "greeks": {
        "delta": 0.4821,
        "gamma": 0.0134,
        "vega": 0.2891,
        "theta": -0.0512,
        "rho": 0.1923
      }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_level` | string | `"beginner"`, `"finance_student"`, or `"professional"` |
| `option_type` | string | `"call"` or `"put"` |
| `style` | string | `"european"` or `"american"` |
| `method` | string | Pricing method used |
| `S`, `K`, `T`, `r`, `sigma`, `q` | float | Option parameters |
| `prices` | object | Map of method name → `{ price, greeks }` |

**Response**

```json
{
  "explanation": "## What the price means\n\nYour call option is worth **$12.34** ..."
}
```

The explanation is a Markdown-formatted string. The depth and terminology are adapted to `user_level`.

> **Note:** For educational purposes only. Not investment advice.

---

## 7. AI — Chat

### `POST /ai/chat`

Multi-turn conversational assistant specialised in options and derivatives. Powered by Gemini 2.5 Flash.

**Request body**

```json
{
  "user_level": "finance_student",
  "messages": [
    { "role": "user", "content": "What does a delta of 0.5 mean?" },
    { "role": "model", "content": "A delta of 0.5 means that for every $1 move in the underlying..." },
    { "role": "user", "content": "And how does gamma relate to that?" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_level` | string | `"beginner"`, `"finance_student"`, or `"professional"` |
| `messages` | array | Conversation history, alternating `user` / `model` roles |

The last message in `messages` must have `role: "user"`.

**Response**

```json
{
  "reply": "Gamma measures how fast delta changes as the stock moves..."
}
```

---

## Enumerations

### `option_type`
| Value | Description |
|-------|-------------|
| `call` | Call option |
| `put` | Put option |

### `style`
| Value | Description |
|-------|-------------|
| `european` | Exercise only at expiry |
| `american` | Exercise any time before expiry |

### `method`
| Value | Style | Description |
|-------|-------|-------------|
| `black_scholes` | European | Closed-form analytical |
| `monte_carlo` | European | GBM simulation with antithetic variates |
| `binomial_tree` | European & American | CRR lattice (500 steps) |
| `baw` | American | Barone-Adesi & Whaley approximation |
| `longstaff_schwartz` | American | Least-squares Monte Carlo (LSM) |
| `all` | Either | Returns all methods valid for the requested style |

### `sigma_type`
| Value | Description |
|-------|-------------|
| `implied` | ATM implied vol from option chain |
| `historical` | 30-day realised vol from daily log returns |

### `user_level`
| Value | Description |
|-------|-------------|
| `beginner` | Plain language, no formulas |
| `finance_student` | Includes model mechanics and formula intuition |
| `professional` | Concise, quantitative, practitioner-level |

---

## Error Responses

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| `400` | Bad request — invalid parameters (e.g. K ≤ 0, T ≤ 0) |
| `404` | Ticker not found or no data in database |
| `422` | Validation error — missing required fields or wrong types |
| `503` | Backend or AI service temporarily unavailable |

---

## Python Examples

### Price a European call (Black-Scholes)

```python
import requests

BASE = "https://option-pricing-platform.vercel.app/api/v1"

response = requests.post(f"{BASE}/price", json={
    "S": 213.49,
    "K": 215.0,
    "T": 0.25,        # years
    "r": 0.0442,
    "q": 0.0051,
    "sigma": 0.25,
    "option_type": "call",
    "style": "european",
    "method": "black_scholes",
})

data = response.json()
bs = data["prices"]["black_scholes"]
print(f"Call price: ${bs['price']:.4f}")
print(f"Delta: {bs['greeks']['delta']:.4f}")
```

### Price an American put with all methods

```python
response = requests.post(f"{BASE}/price", json={
    "ticker": "AAPL",      # S, r, q resolved from database
    "K": 210.0,
    "T": 0.5,
    "sigma": 0.28,
    "option_type": "put",
    "style": "american",
    "method": "all",       # BAW + Longstaff-Schwartz + Binomial Tree
    "mc_paths": 10000,
})

for method, output in response.json()["prices"].items():
    print(f"{method:25s}: ${output['price']:.4f}")
```

### Fetch live market data

```python
response = requests.get(f"{BASE}/market/AAPL")
market = response.json()
print(f"Spot:    ${market['spot_price']:.2f}")
print(f"IV ATM:  {market['atm_implied_vol'] * 100:.1f}%")
print(f"RFR:     {market['risk_free_rate'] * 100:.2f}%")
```

### Get the implied volatility surface

```python
response = requests.get(f"{BASE}/vol_surface/AAPL", params={"option_type": "call"})
surface = response.json()
print(f"Surface points: {len(surface['points'])}")
for pt in surface["points"][:5]:
    print(f"  K={pt['strike']:.0f}  T={pt['T']:.3f}y  IV={pt['implied_vol']*100:.1f}%")
```
