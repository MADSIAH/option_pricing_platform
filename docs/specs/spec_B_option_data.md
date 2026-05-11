# Spec B — Option Data & Vol Surface Integration
> **For Claude Code / Codex** — Phase 3b  
> Scope: option chain fetching, implied volatility surface, scheduler integration  
> Builds on Spec A (database, daily prices, live prices, risk-free rate — all working)

---

## Context

Spec A is implemented and tested. This spec adds the missing piece: **option chain data and implied volatility surface**.

The existing pricing code lives in `src/pricing/`. Do not modify it.

---

## Key Decision

We read **implied volatility directly from yfinance** (`impliedVolatility` column in the option chain). We do **not** use `build_vol_surface()` from `src/pricing/vol_surface.py` for this purpose.

Rationale:
- yfinance already provides IV pre-computed on each contract
- Avoids the European/American style ambiguity
- The working implementation is validated in `notebooks/pricing.ipynb` (static reference)

`build_vol_surface()` remains available for other uses (e.g. research, backtesting) but is not part of the data pipeline.

---

## Architecture

```
yfinance option chains ──► APScheduler ──► option_chain table (upsert)
                                      ──► vol_surface table (upsert)
                                                │
                                           FastAPI (Spec C)
```

---

## 1. Database Changes — `src/data/database.py`

### New table: `option_chain`
Raw option chain per ticker.  
**Strategy: upsert** — always replaces existing rows for that ticker. Only the latest fetch is kept.  
Useful for price path plots.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `ticker` | TEXT | |
| `expiry` | TEXT | ISO date e.g. `"2026-06-20"` |
| `strike` | REAL | |
| `option_type` | TEXT | `"call"` or `"put"` |
| `bid` | REAL | |
| `ask` | REAL | |
| `mid_price` | REAL | `ask` when `bid=0`, else `(bid+ask)/2` |
| `volume` | INTEGER | |
| `open_interest` | INTEGER | |
| `implied_vol` | REAL | `impliedVolatility` from yfinance |
| `T` | REAL | time to expiry in years |
| `fetched_at` | TEXT | UTC ISO datetime |

Index on `(ticker, expiry, option_type)`.

### Existing table: `vol_surface`
Already defined in Spec A, currently empty. **Strategy: upsert** — always replaces existing rows for that ticker. Only the latest surface is kept.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `ticker` | TEXT | |
| `expiry` | TEXT | ISO date |
| `strike` | REAL | |
| `implied_vol` | REAL | from yfinance `impliedVolatility` |
| `T` | REAL | time to expiry in years |
| `fetched_at` | TEXT | UTC ISO datetime |

Only insert rows where `T > 30/365` (drop near-expiry options — IV inherently unstable).  
Index on `(ticker, fetched_at)`.

### Updated retention policy

| Table | Policy |
|---|---|
| `daily_prices` | 1 year |
| `live_price` | Upsert — keep only latest per ticker |
| `option_chain` | Upsert — keep only latest fetch per ticker |
| `vol_surface` | Upsert — keep only latest fetch per ticker |
| `risk_free_rate` | Upsert — keep only latest |

---

## 2. New Fetcher Functions — `src/data/fetcher.py`

### `fetch_and_store_option_data(ticker: str) -> bool`

Fetches the full option chain from yfinance for all available expiries, reads IV directly from `impliedVolatility`, and stores both the raw chain and the vol surface.

**Filtering logic** (see `notebooks/pricing.ipynb` for the validated reference implementation):
- Drop expiries with `T < 30/365`
- Require `ask > 0`
- `mid_price = ask` when `bid=0`, else `(bid+ask)/2`
- Drop rows where `impliedVolatility` is null, zero, or > 2.0
- Apply moneyness filter: `0.7 * S <= strike <= 1.3 * S`

**Error handling:** if yfinance returns empty data or throws an exception, log the error and return `False`. The scheduler retains the last successful data in the DB — since both tables use upsert, nothing is overwritten on failure.

**Returns** `True` on success, `False` on failure.

### Helper functions (add to `fetcher.py`)
```
store_option_chain(ticker, df) → upserts rows into option_chain table (replaces previous fetch)
store_vol_surface(ticker, df)  → upserts rows into vol_surface table (replaces previous fetch)
```

---

## 3. Error Handling — `safe_job` decorator

Add to `src/data/scheduler.py`. Wraps every scheduler job in a try/except so that:
- A single job failure never crashes the scheduler process
- Errors are logged with enough detail to debug
- The DB retains the last successful data — jobs that fail simply skip their write

```python
def safe_job(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Job {func.__name__} failed: {e}")
            return None
    return wrapper
```

Apply `@safe_job` to all scheduler jobs.

---

## 4. Scheduler Updates — `src/data/scheduler.py`

### New job

| Job | Schedule (ET) | Notes |
|---|---|---|
| `refresh_all_option_data()` | Every 60 min, market hours only | Calls `fetch_and_store_option_data()` per ticker |

### Updated startup sequence
Add refresh_all_option_data() to the startup sequence after refresh_all_live_prices().

### Complete job table

| Job | Schedule (ET) | Notes |
|---|---|---|
| `refresh_all_live_prices()` | Every 60 min | Market hours only |
| `refresh_all_daily_prices()` | Daily at 18:30 | After market close |
| `refresh_all_option_data()` | Every 60 min | Market hours only |
| `refresh_risk_free_rate()` | Daily at 08:00 | Before market open |
| `cleanup_old_rows()` | Daily at 02:00 | Only applies to `daily_prices` (2yr retention) |

---

## 5. Updated Test Script — `scripts/test_data.py`

Add to existing checks from Spec A:

```python
# 7. option_chain has rows for each watched ticker
# 8. option_chain rows have non-null implied_vol, strike, expiry, T
# 9. vol_surface has rows for each watched ticker
# 10. vol_surface implied_vol values are between 0.01 and 2.0
# 11. vol_surface has no NaN in implied_vol
# 12. vol_surface only contains rows with T > 30/365
```

---

## Out of Scope
- FastAPI endpoints → Spec C
- WRDS integration → dropped
- `build_vol_surface()` is not used in this pipeline