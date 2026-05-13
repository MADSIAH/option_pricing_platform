# Spec C — API Layer
> **For Claude Code** — Phase 3c  
> Scope: FastAPI endpoints  
> Builds on Spec A + B — read the full repo before starting
---

## Context

- Pricing engine: `src/pricing/` — do not modify
- Data layer: `src/data/` — do not modify
- DB helpers in `src/data/fetcher.py`: `get_latest_live_price()`, `get_latest_risk_free_rate()`, `calculate_historical_vol()`, `get_atm_vol()`
- All new code goes in `src/api/`

---

## System Overview

- **Backend**:
  - periodically fetches market data in DB (hourly/daily updates)
  - computes option prices and Greeks
  - provides IV and option chain data for plots
  - stateless computation engine for all pricing endpoints

- **Frontend**:
  - maintains UI state between API calls
  - owns all intermediate pricing inputs (S, K, T, σ, r, q)
  - does NOT perform any financial computation
  - visualizes all outputs using Plotly.js (prices, surfaces, Greeks)

---

### User Flow

1. User selects ticker or custom inputs

2. If ticker:
   GET /market/{ticker}
   → frontend receives market inputs (S, r, q, vol)

3. User adjusts parameters (K, T, σ, etc.)

4. User triggers pricing:
   POST /price
   → backend returns prices + Greeks for all valid models and surface data

5. Frontend visualizes results (Plotly.js)

## Frontend Interaction Contract

### 1. Data layer
- Backend automatically ingests and updates market data into DB. 
- Frontend never triggers data ingestion
- No external market calls are made at request time

### 2. Stateless API rule:
- Backend is stateless
- DB is persistent storage only
- Every request must be self-contained

### 3. Market initilization (optional)
- GET `/api/v1/market/{ticker}`
-  Frontend responsibility is to store values in UI state and allow user to override any parameter

### 4. Pricing execution
- If ticker exists → parameters may be initialized from `/market`
- If custom stock → all parameters must be explicitly provided
- Backend performs all computations (pricing + Greeks)

### 5. Sigma resolution priority

Backend resolves sigma in this order:

1. `sigma` explicitly provided → use directly
2. `sigma_type="implied"` → use vol surface
3. `sigma_type="historical"` → use historical volatility
4. if implied unavailable → fallback to historical (`sigma_fallback = true`)
5. if no valid sigma → error

### 6. Visualization Surfaces

- Backend:
  - provides vol surface data from DB via `/vol_surface/{ticker}`
  - generates price surface grid via `/price_surface` (Black-Scholes only)
  - does not couple these outputs with `/price`

- Frontend:
  - uses `/vol_surface` to build volatility surface plots (3D IV surface, smile, term structure)
  - uses `/price_surface` to build price surface plots (Price vs S vs T)
  - uses `/price` only for single-option pricing + Greeks
  - 
---

## Available Pricing Models

From `src/pricing/__init__.py`:

| Model | Class | Style | Notes |
|---|---|---|---|
| Black-Scholes | `BlackScholes` | European only | Formula closed-form |
| Monte Carlo | `MonteCarlo` | European only | GBM with antithetic variates |
| Binomial Tree | `BinomialTree` | European + American | CRR, `american=True` for American |
| Barone-Adesi-Whaley | `BaroneAdesiWhaley`|American only | Formula closed-form |
| Longstaff-Schwartz | `LongstaffSchwartz` | American only | LSM algorithm |


Greeks:
- `AnalyticalGreeks` — closed-form BS Greeks
- `NumericalGreeks(model)` — central differences, works with any model

**Method/style rules for the API:**
- `style="european"` → BS, MC, BT (european)
- `style="american"` → BAW, BT (american) , LongstaffSchwartz
- `method="all"` → all valid models for the chosen style
- Heston is excluded from standard pricing endpoints

---

## Critical Instructions

- Enable **CORS** for all origins (`allow_origins=["*"]`) — required for browser frontend
- Use **Pydantic** schemas for all request/response validation
- The API **never calls yfinance directly** — always reads from DB
- All endpoints must handle DB errors gracefully — never crash, return appropriate HTTP status
- **Custom stock** (ticker not in DB): all params (`S`, `r`, `q`, `sigma`) become mandatory. Include `"data_source": "user_provided"` in response instead of `"data_source": "database"`

---

## Sigma Selection

Every pricing endpoint must support two sigma sources:
- `sigma_type: "historical"` → use `calculate_historical_vol()` from DB
- `sigma_type: "implied"` → use ATM implied vol from `vol_surface` table

If `sigma` is provided explicitly by the user, use it directly and ignore `sigma_type`.  
If `sigma` is not provided and `sigma_type="implied"` but vol surface is unavailable, fall back to historical and include `"sigma_fallback": true` in response.

Default: suggest both in `GET /market/{ticker}` response so frontend can offer the choice.

---

## Stale Data

Every response that reads from DB must include:
- `updated_at`: UTC timestamp of last DB update
- `stale`: `true` if `updated_at` is older than 90 minutes

---

## Folder Structure

```
src/api/
├── __init__.py
├── main.py           ← FastAPI app, CORS, lifespan
├── schemas.py        ← all Pydantic models
└── routes/
    ├── __init__.py
    ├── market.py
    ├── surface.py
    ├── pricing.py
    └── health.py
```

---

## Enums (in schemas.py)

- `OptionType`: `"call"` | `"put"`
- `OptionStyle`: `"european"` | `"american"`
- `PricingMethod`: `"black_scholes"` | `"monte_carlo"` | `"binomial_tree"` | `"longstaff_schwartz"` | `"all"`
- `SigmaType`: `"historical"` | `"implied"`
- `VaryBy`: `"S"` | `"T"`

---

## Endpoints

### `GET /api/v1/health`
```json
{"status": "ok", "db_reachable": true}
```

---

### `GET /api/v1/market/{ticker}`
Purpose: pre-populates the pricer form when the user selects a ticker.

Response:

- spot price
- historical vol
- ATM implied vol (if available)
- dividend yield
- risk-free rate
- metadata (updated_at, stale, data_source)

Rules:

- return 404 if ticker not in DB
- atm_implied_vol = null if missing

---

### `GET /api/v1/vol_surface/{ticker}`
Vol surface data for 3D plotting.

Returns
- expiry
- T
- strike
- implied_vol

If missing:503 "Vol surface not yet computed"

---

### `GET /api/v1/option_chain/{ticker}`

**Query params:** `option_type`: `"call"` | `"put"` | `"both"` (default: `"both"`)

Returns raw option chains from DB

---

### `POST /api/v1/price`

Prices a single option with all valid models for the chosen style.

Input:

- S, K, T
- sigma (optional)
- sigma_type
- r, q
- option_type
- style
- mc_paths (optional)

Rules:

- DB ticker → S/r/q optional
- custom stock → all required

Output:

- prices per model (by style)
- Greeks per model
- sigma_source + fallback info
- data_source

---

### `POST /api/v1/price_surface`
Returns a grid of BS option prices for 3D visualization (price vs S vs T-t).  
Black-Scholes for European, BAW for American.

Uses:

- Spot price
- T_range
- r, q always from DB.

Returns grid of prices.

---

### `POST /api/v1/greeks_profile`
Returns Greeks varying over S (spot price) or T (time-to-maturity) for plotting.

Vary:
- S or T

Returns:

- delta, gamma, vega, theta, rho curves

---

## Error Handling

| Condition | Status | Response |
|---|---|---|
| Ticker not in DB and params missing | 422 | `{"error": "Custom stock requires S, r, q, sigma"}` |
| Ticker not in DB | 404 | `{"error": "Ticker not found"}` |
| Vol surface unavailable | 503 | `{"status": "unavailable", "reason": "..."}` |
| Sigma implied requested but unavailable, no fallback possible | 422 | `{"error": "Implied vol unavailable and no fallback sigma provided"}` |
| Invalid params (Pydantic) | 422 | FastAPI default |
| Pricing engine error | 500 | `{"error": "Pricing failed", "detail": "..."}` |

---

## Running the API

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Auto-generated docs at: `http://SERVER_IP:8000/docs`

---

## Dependencies (add to requirements.txt if missing)
```
fastapi
uvicorn[standard]
```

---

## Out of Scope
- Authentication
- WebSocket / streaming
- Frontend
- Heston model in standard pricing endpoints (requires different params schema)
