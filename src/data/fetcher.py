"""Fetching and calculation utilities for Spec B data layer."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import pytz
import requests
import yfinance as yf
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .database import DailyPrice, LivePrice, OptionChain, RiskFreeRate, VolSurface, session_scope

ET = pytz.timezone("America/New_York")
TRADING_DAYS_PER_YEAR = 252
FRED_DGS10_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
MIN_OPTION_T_YEARS = 30.0 / 365.0
MAX_REASONABLE_IV = 2.0

logger = logging.getLogger(__name__)


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _extract_spot_price(yf_ticker: Any) -> float | None:
    fast_info = getattr(yf_ticker, "fast_info", None)
    if fast_info is not None:
        try:
            spot = fast_info.get("last_price")
            if spot is not None:
                spot_value = float(spot)
                if spot_value > 0:
                    return spot_value
        except Exception:
            pass

    try:
        info = yf_ticker.info or {}
    except Exception:
        info = {}

    for key in ("regularMarketPrice", "currentPrice"):
        spot = info.get(key)
        if spot is not None:
            spot_value = _safe_float(spot, default=0.0)
            if spot_value > 0:
                return spot_value
    return None


def is_market_open() -> bool:
    """Return True only during regular US market hours in ET."""
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


def backfill_daily_prices(ticker: str) -> int:
    """
    Backfill 1 year of daily adjusted close prices if data is missing.

    Skips if ticker already has >= 252 rows.
    Returns the number of inserted rows.
    """
    ticker = _normalize_ticker(ticker)

    with session_scope() as session:
        existing = session.scalar(
            select(func.count()).select_from(DailyPrice).where(DailyPrice.ticker == ticker)
        ) or 0
        if existing >= TRADING_DAYS_PER_YEAR:
            return 0

    history = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
    if history.empty or "Close" not in history.columns:
        return 0

    close_series = history["Close"].dropna()
    if close_series.empty:
        return 0

    # Some 1y windows may return <252 rows depending on holidays/data gaps.
    # Fallback to a wider lookback, then keep only the most recent 252 points.
    if len(close_series) < TRADING_DAYS_PER_YEAR:
        for period in ("18mo", "2y"):
            fallback_history = yf.Ticker(ticker).history(
                period=period,
                interval="1d",
                auto_adjust=True,
            )
            if fallback_history.empty or "Close" not in fallback_history.columns:
                continue
            fallback_close = fallback_history["Close"].dropna()
            if len(fallback_close) >= TRADING_DAYS_PER_YEAR:
                close_series = fallback_close.tail(TRADING_DAYS_PER_YEAR)
                break

    if len(close_series) > TRADING_DAYS_PER_YEAR:
        close_series = close_series.tail(TRADING_DAYS_PER_YEAR)

    rows = [
        {
            "ticker": ticker,
            "date": pd.Timestamp(idx).date().isoformat(),
            "adj_close": float(price),
            "source": "yfinance",
        }
        for idx, price in close_series.items()
    ]

    with session_scope() as session:
        before = session.scalar(
            select(func.count()).select_from(DailyPrice).where(DailyPrice.ticker == ticker)
        ) or 0
        stmt = sqlite_insert(DailyPrice).values(rows).prefix_with("OR IGNORE")
        session.execute(stmt)
        after = session.scalar(
            select(func.count()).select_from(DailyPrice).where(DailyPrice.ticker == ticker)
        ) or 0

    return max(int(after - before), 0)


def refresh_daily_price(ticker: str) -> None:
    """
    Refresh latest daily adjusted close price (single row).

    Expected to run once daily after market close.
    """
    ticker = _normalize_ticker(ticker)
    history = yf.Ticker(ticker).history(period="1d", auto_adjust=True)
    if history.empty or "Close" not in history.columns:
        return

    close_series = history["Close"].dropna()
    if close_series.empty:
        return

    latest_idx = close_series.index[-1]
    latest_price = float(close_series.iloc[-1])
    latest_date = pd.Timestamp(latest_idx).date().isoformat()

    row = {
        "ticker": ticker,
        "date": latest_date,
        "adj_close": latest_price,
        "source": "yfinance",
    }
    with session_scope() as session:
        stmt = sqlite_insert(DailyPrice).values(row).prefix_with("OR IGNORE")
        session.execute(stmt)


def refresh_live_price(ticker: str) -> None:
    """
    Refresh latest intraday spot price and trailing dividend yield.

    Runs only during market hours (ET). Outside hours, the function no-ops.
    """
    if not is_market_open():
        return

    ticker = _normalize_ticker(ticker)
    yf_ticker = yf.Ticker(ticker)

    last_price = None
    fast_info = getattr(yf_ticker, "fast_info", None)
    if fast_info is not None:
        try:
            last_price = fast_info.get("last_price")
        except Exception:
            last_price = None

    info = yf_ticker.info or {}
    if last_price is None:
        last_price = info.get("regularMarketPrice")
    if last_price is None:
        return

    dividend_yield = info.get("dividendYield", 0.0)
    if dividend_yield is None:
        dividend_yield = 0.0

    now_utc = datetime.now(timezone.utc).isoformat()
    upsert_stmt = sqlite_insert(LivePrice).values(
        ticker=ticker,
        spot_price=float(last_price),
        dividend_yield=float(dividend_yield),
        updated_at=now_utc,
    )
    upsert_stmt = upsert_stmt.on_conflict_do_update(
        index_elements=["ticker"],
        set_={
            "spot_price": float(last_price),
            "dividend_yield": float(dividend_yield),
            "updated_at": now_utc,
        },
    )

    with session_scope() as session:
        session.execute(upsert_stmt)


def store_option_chain(ticker: str, df: pd.DataFrame) -> None:
    """
    Replace latest option_chain snapshot for one ticker.

    Strategy follows Spec B: delete previous rows for ticker, then insert new snapshot.
    """
    ticker = _normalize_ticker(ticker)
    if df.empty:
        return

    required = {
        "ticker",
        "expiry",
        "strike",
        "option_type",
        "bid",
        "ask",
        "mid_price",
        "volume",
        "open_interest",
        "implied_vol",
        "T",
        "fetched_at",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing option_chain columns: {sorted(missing)}")

    records = [
        {
            "ticker": ticker,
            "expiry": str(row["expiry"]),
            "strike": float(row["strike"]),
            "option_type": str(row["option_type"]),
            "bid": float(row["bid"]),
            "ask": float(row["ask"]),
            "mid_price": float(row["mid_price"]),
            "volume": _safe_int(row["volume"]),
            "open_interest": _safe_int(row["open_interest"]),
            "implied_vol": float(row["implied_vol"]),
            "T": float(row["T"]),
            "fetched_at": str(row["fetched_at"]),
        }
        for _, row in df.iterrows()
    ]

    with session_scope() as session:
        session.execute(delete(OptionChain).where(OptionChain.ticker == ticker))
        if records:
            session.execute(sqlite_insert(OptionChain).values(records))


def store_vol_surface(ticker: str, df: pd.DataFrame) -> None:
    """
    Replace latest vol_surface snapshot for one ticker.

    Strategy follows Spec B: delete previous rows for ticker, then insert new snapshot.
    """
    ticker = _normalize_ticker(ticker)
    if df.empty:
        return

    required = {"ticker", "expiry", "strike", "implied_vol", "T", "fetched_at"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing vol_surface columns: {sorted(missing)}")

    records = [
        {
            "ticker": ticker,
            "expiry": str(row["expiry"]),
            "strike": float(row["strike"]),
            "implied_vol": float(row["implied_vol"]),
            "T": float(row["T"]),
            "fetched_at": str(row["fetched_at"]),
        }
        for _, row in df.iterrows()
    ]

    with session_scope() as session:
        session.execute(delete(VolSurface).where(VolSurface.ticker == ticker))
        if records:
            session.execute(sqlite_insert(VolSurface).values(records))


def fetch_and_store_option_data(ticker: str) -> bool:
    """
    Fetch all option expiries from yfinance and persist option_chain + vol_surface.

    Returns True on success, False on any fetch/validation failure.
    """
    ticker = _normalize_ticker(ticker)
    try:
        yf_ticker = yf.Ticker(ticker)
        spot = _extract_spot_price(yf_ticker)
        if spot is None or spot <= 0:
            logger.error("option_data fetch failed | ticker=%s | missing spot", ticker)
            return False

        expiries = list(getattr(yf_ticker, "options", []) or [])
        if not expiries:
            logger.error("option_data fetch failed | ticker=%s | no expiries", ticker)
            return False

        today_et = datetime.now(ET).date()
        moneyness_min = spot * 0.7
        moneyness_max = spot * 1.3
        rows: list[pd.DataFrame] = []

        for expiry in expiries:
            try:
                expiry_date = pd.Timestamp(expiry).date()
            except Exception:
                continue

            T_exp = (expiry_date - today_et).days / 365.0
            if T_exp < MIN_OPTION_T_YEARS:
                continue

            try:
                chain = yf_ticker.option_chain(expiry)
            except Exception:
                logger.exception("option_chain fetch error | ticker=%s | expiry=%s", ticker, expiry)
                continue

            for option_type, contracts in (("call", chain.calls), ("put", chain.puts)):
                if contracts is None or contracts.empty:
                    continue

                df = contracts.copy()
                strike_series = (
                    pd.to_numeric(df["strike"], errors="coerce")
                    if "strike" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )
                bid_series = (
                    pd.to_numeric(df["bid"], errors="coerce")
                    if "bid" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )
                ask_series = (
                    pd.to_numeric(df["ask"], errors="coerce")
                    if "ask" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )
                iv_series = (
                    pd.to_numeric(df["impliedVolatility"], errors="coerce")
                    if "impliedVolatility" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )
                volume_series = (
                    pd.to_numeric(df["volume"], errors="coerce")
                    if "volume" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )
                oi_series = (
                    pd.to_numeric(df["openInterest"], errors="coerce")
                    if "openInterest" in df.columns
                    else pd.Series(np.nan, index=df.index)
                )

                df["strike"] = strike_series
                df["bid"] = bid_series.fillna(0.0)
                df["ask"] = ask_series
                df["implied_vol"] = iv_series
                df["volume"] = volume_series.fillna(0)
                df["open_interest"] = oi_series.fillna(0)

                df = df[
                    (df["ask"] > 0)
                    & (df["implied_vol"].notna())
                    & (df["implied_vol"] > 0.01)
                    & (df["implied_vol"] <= MAX_REASONABLE_IV)
                    & (df["strike"] >= moneyness_min)
                    & (df["strike"] <= moneyness_max)
                ].copy()

                if df.empty:
                    continue

                df["mid_price"] = np.where(df["bid"] == 0, df["ask"], (df["bid"] + df["ask"]) / 2.0)
                df["ticker"] = ticker
                df["expiry"] = expiry_date.isoformat()
                df["option_type"] = option_type
                df["T"] = float(T_exp)
                rows.append(
                    df[
                        [
                            "ticker",
                            "expiry",
                            "strike",
                            "option_type",
                            "bid",
                            "ask",
                            "mid_price",
                            "volume",
                            "open_interest",
                            "implied_vol",
                            "T",
                        ]
                    ]
                )

        if not rows:
            logger.error("option_data fetch failed | ticker=%s | no rows after filtering", ticker)
            return False

        snapshot = pd.concat(rows, ignore_index=True)
        fetched_at = datetime.now(timezone.utc).isoformat()
        snapshot["fetched_at"] = fetched_at

        # Keep raw chain for both calls and puts.
        store_option_chain(ticker, snapshot)

        # Keep vol surface from calls to avoid duplicated (expiry, strike) points.
        surface = snapshot[snapshot["option_type"] == "call"][
            ["ticker", "expiry", "strike", "implied_vol", "T", "fetched_at"]
        ].copy()
        if surface.empty:
            surface = snapshot[["ticker", "expiry", "strike", "implied_vol", "T", "fetched_at"]].copy()
        store_vol_surface(ticker, surface)
        return True
    except Exception:
        logger.exception("option_data fetch failed | ticker=%s", ticker)
        return False


def calculate_historical_vol(ticker: str) -> float:
    """
    Compute annualized historical volatility from last 252 daily prices.

    Raises:
        ValueError: if fewer than 252 rows are available.
    """
    ticker = _normalize_ticker(ticker)

    with session_scope() as session:
        rows = session.execute(
            select(DailyPrice.adj_close)
            .where(DailyPrice.ticker == ticker)
            .order_by(DailyPrice.date.desc())
            .limit(TRADING_DAYS_PER_YEAR)
        ).all()

    prices_desc = [float(row[0]) for row in rows]
    if len(prices_desc) < TRADING_DAYS_PER_YEAR:
        raise ValueError(
            f"Not enough daily price rows for {ticker}: "
            f"{len(prices_desc)} found, {TRADING_DAYS_PER_YEAR} required."
        )

    prices = pd.Series(list(reversed(prices_desc)), dtype=float)
    returns = np.log(prices / prices.shift(1)).dropna()
    sigma = float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
    return sigma


def fetch_risk_free_rate() -> float:
    """
    Fetch US 10Y yield from FRED (DGS10), convert to decimal, and upsert.
    """
    response = requests.get(FRED_DGS10_URL, timeout=20)
    response.raise_for_status()

    rows = list(csv.DictReader(StringIO(response.text)))
    dgs10_value = None
    for row in reversed(rows):
        value = row.get("DGS10")
        if value not in (None, "", "."):
            dgs10_value = float(value)
            break

    if dgs10_value is None:
        raise ValueError("No valid DGS10 value found in FRED response.")

    rate = dgs10_value / 100.0
    now_utc = datetime.now(timezone.utc).isoformat()

    upsert_stmt = sqlite_insert(RiskFreeRate).values(id=1, rate=rate, updated_at=now_utc)
    upsert_stmt = upsert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"rate": rate, "updated_at": now_utc},
    )

    with session_scope() as session:
        session.execute(upsert_stmt)

    return rate


def fetch_vol_surface_wrds(ticker: str) -> None:
    """Spec A stub. Implemented in Spec C."""
    _ = ticker
    raise NotImplementedError(
        "WRDS OptionMetrics integration pending — data format to be inspected first"
    )
