# Spec A — Data Fetching Layer
> **For Claude Code / Codex** — Phase 3a  
> Scope: database setup, data fetching, APScheduler  
> API is out of scope for this phase — see Spec B

---

## Context

The pricing engine is complete (Phases 1 & 2, 47 passing tests) in `src/pricing/`. Do not modify it.  
All new code for this phase goes in `src/data/`.

> **For Codex users:** provide the full repo as context. Do not touch `src/pricing/`.

### Deployment target
Professor's Linux server. SQLite file on the same machine — no external database.

### What this phase delivers
At the end of this phase, running `python -m src.data.scheduler` should:
1. Create the database and all tables
2. Backfill 1 year of daily prices for all watched tickers
3. Fetch live prices, risk-free rate
4. Log each job as it runs
5. Keep running and refreshing on schedule

A manual test script (`scripts/test_data.py`) should verify that data is present and correctly shaped for the pricing engine.

---

## Data Sources

| Data | Source | Used for |
|---|---|---|
| Historical daily prices (adj close) | yfinance | σ annualizzata (input BS/MC/BT) |
| Live spot price | yfinance | S spot (input BS/MC/BT) |
| Risk-free rate | FRED API | r (input BS/MC/BT) |
| Implied vol surface | WRDS OptionMetrics | IV surface — **stub only this phase** |

---

## Timezone

**All scheduling and market-hours logic uses `America/New_York` (ET) explicitly.**  
Never rely on the server's local timezone. Use `pytz.timezone("America/New_York")` for all time comparisons and APScheduler job definitions.

```python
import pytz
ET = pytz.timezone("America/New_York")

def is_market_open() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close
```

---

## 1. Database — `src/data/database.py`

**SQLite** via **SQLAlchemy** (sync).  
File path: `DB_PATH` env var, default `data/market_data.db`.  
Create `data/` folder at runtime. Add to `.gitignore`.

### Tables

#### `daily_prices`
One row per ticker per trading day. Full history for vol calculation.  
**Strategy: append.** Unique constraint on `(ticker, date)` prevents duplicates.  
**Retention: 1 year** (cleanup job).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `ticker` | TEXT | e.g. `"AAPL"` |
| `date` | TEXT | ISO date `"2025-05-06"` |
| `adj_close` | REAL | adjusted closing price |
| `source` | TEXT | `"yfinance"` |

Index on `(ticker, date)`.

#### `live_price`
Latest intraday spot price. One row per ticker, overwritten on each refresh.  
**Strategy: upsert** (INSERT OR REPLACE).  
Rows deleted when ticker is removed from watched registry.

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT PRIMARY KEY | |
| `spot_price` | REAL | |
| `dividend_yield` | REAL | trailing 12m yield, e.g. 0.005 |
| `updated_at` | TEXT | UTC ISO datetime |

#### `vol_surface`
> All vol surface details deferred to Spec C.

Implied vol from WRDS OptionMetrics. 
**Empty this phase** — populated only when WRDS integration is implemented (Spec C).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `ticker` | TEXT | |
| `expiry` | TEXT | ISO date |
| `strike` | REAL | |
| `implied_vol` | REAL | from WRDS OptionMetrics |
| `fetched_at` | TEXT | UTC ISO datetime |

Index on `(ticker, fetched_at)`.

#### `risk_free_rate`
Single row, upserted on every refresh. No retention — always 1 row.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | always 1 |
| `rate` | REAL | decimal e.g. `0.043` |
| `updated_at` | TEXT | UTC ISO datetime |

---

### Retention policy (enforced by daily cleanup job)

| Table | Keep |
|---|---|
| `daily_prices` | 1 year |
| `live_price` | Keep only latest per ticker (upsert — no cleanup job needed) |
| `vol_surface` | TBD |
| `risk_free_rate` | Keep only latest (upsert — no cleanup job needed)|

---

## 2. Fetcher — `src/data/fetcher.py`

### `backfill_daily_prices(ticker: str) -> int`
Called once per ticker on first startup.  
Skipped if the ticker already has ≥ 252 rows in `daily_prices`.  
Returns number of rows inserted.

```python
yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)["Close"]
```

Insert each row into `daily_prices`. Skip if `(ticker, date)` already exists (unique constraint).

### `refresh_daily_price(ticker: str) -> None`
Called **once daily at 18:00 ET** after market close.  
Fetches only the latest trading day:
```python
yf.Ticker(ticker).history(period="1d", auto_adjust=True)["Close"]
```
Insert single row, skip if already present.

### `refresh_live_price(ticker: str) -> None`
Called **every 60 minutes during market hours only**.  
```python
yf.Ticker(ticker).fast_info["last_price"]
dividend_yield = yf.Ticker(ticker).info.get("dividendYield", 0.0)
```
Upsert into `live_price`. If `is_market_open()` returns False, skip entirely.
Also fetches dividends and upserts into dividend_yield column.

### `calculate_historical_vol(ticker: str) -> float`
Pure calculation — no external calls. Reads last 252 rows of `daily_prices` for ticker:
```python
returns = np.log(prices / prices.shift(1)).dropna()
sigma = returns.std() * np.sqrt(252)
```
Returns annualised σ as float. Raises `ValueError` if fewer than 252 rows available.

### `fetch_risk_free_rate() -> float`
```
GET https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10
```
Parse CSV, take last non-null value, divide by 100. Upsert into `risk_free_rate`. Returns rate as float.

### `fetch_vol_surface_wrds(ticker: str) -> None` — STUB
> All vol surface details deferred to Spec C.
```python
def fetch_vol_surface_wrds(ticker: str) -> None:
    raise NotImplementedError(
        "WRDS OptionMetrics integration pending — data format to be inspected first"
    )
```
Do not implement. Do not call from scheduler.

---

## 3. Scheduler — `src/data/scheduler.py`

Use `APScheduler` `BackgroundScheduler` with `timezone="America/New_York"` set globally.

```python
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler(timezone="America/New_York")
```

### Jobs

| Job | Schedule (ET) | Notes |
|---|---|---|
| `backfill_all_tickers()` | Once at startup | Skips tickers with existing data |
| `refresh_all_live_prices()` | Every 60 min | Calls `is_market_open()` — skips if closed |
| `refresh_all_daily_prices()` | Daily at 18:30 ET | After market close + 30 min buffer |
|`fetch_risk_free_rate()`| Once at startup | |
| `refresh_risk_free_rate()` | Daily at 08:00 ET | Before market open |
| `cleanup_old_rows()` | Daily at 02:00 ET | Enforces retention policy |

### Ticker registry

```python
import os
WATCHED_TICKERS: set[str] = set(os.getenv("WATCHED_TICKERS", "AAPL,SPY,TSLA").split(","))
```

**Adding a ticker at runtime:** add to `WATCHED_TICKERS`, immediately run `backfill_daily_prices()` and `refresh_live_price()` for that ticker.  
**Removing a ticker:** remove from set, delete its row from `live_price`.

### Startup sequence
```
1. init_db()               — create all tables if not exist
2. backfill_all_tickers()  — fetch 1yr history for each watched ticker
3. refresh_risk_free_rate() — get current rate
4. refresh_all_live_prices() — only if market is open
5. scheduler.start()       — begin scheduled jobs
```

### Entry point
Running `python -m src.data.scheduler` should execute the startup sequence and then block (scheduler runs in background, main thread sleeps).

---

## 4. Folder Structure

```
src/
└── data/
    ├── __init__.py
    ├── database.py     ← SQLAlchemy engine + table definitions + init_db()
    ├── fetcher.py      ← all fetch and calculation functions
    └── scheduler.py    ← APScheduler setup, jobs, ticker registry, entry point

data/                   ← created at runtime, gitignored
    market_data.db

scripts/
    test_data.py        ← manual test: verify DB contents after startup
```

---

## 5. Test Script — `scripts/test_data.py`

After running the scheduler once, this script should pass all checks:

```python
# Checks to implement:
# 1. daily_prices has >= 252 rows for each watched ticker
# 2. most recent daily_prices date is within 5 trading days of today
# 3. live_price has a row for each watched ticker (if market was open)
# 4. risk_free_rate has 1 row and rate is between 0.01 and 0.15
# 5. calculate_historical_vol() returns a float between 0.05 and 1.5 for each ticker
# 6. vol_surface table exists and is empty (WRDS not yet integrated)
```

---

## 6. Dependencies

```
sqlalchemy
apscheduler
yfinance
pandas
numpy
requests      # FRED fetch
python-dotenv
pytz          # timezone handling
```

---

## 7. Environment Variables

```
WATCHED_TICKERS=AAPL,SPY,TSLA
DB_PATH=data/market_data.db
```

---

## Out of Scope for This Phase
- FastAPI and all endpoints → Spec B
- WRDS OptionMetrics integration → Spec C
- Frontend 
