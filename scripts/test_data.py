"""Manual validation script for Spec A data layer."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.database import DailyPrice, LivePrice, RiskFreeRate, VolSurface, init_db, session_scope
from src.data.fetcher import ET, TRADING_DAYS_PER_YEAR, calculate_historical_vol, is_market_open


def _watched_tickers() -> list[str]:
    raw = os.getenv("WATCHED_TICKERS", "AAPL,SPY,TSLA")
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def _business_day_distance(start_date: str, end_date: str) -> int:
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if end < start:
        return 10**9
    # Inclusive range -> subtract 1 to get elapsed business days.
    return max(len(pd.bdate_range(start=start, end=end)) - 1, 0)


def main() -> None:
    tickers = _watched_tickers()
    if not tickers:
        raise ValueError("WATCHED_TICKERS resolved to empty list.")

    init_db()
    today_et = datetime.now(ET).date().isoformat()
    market_open_now = is_market_open()

    with session_scope() as session:
        # 1) daily_prices has >=252 rows for each watched ticker
        for ticker in tickers:
            count_rows = session.scalar(
                select(func.count()).select_from(DailyPrice).where(DailyPrice.ticker == ticker)
            ) or 0
            assert count_rows >= TRADING_DAYS_PER_YEAR, (
                f"[FAIL] daily_prices rows for {ticker}: {count_rows} "
                f"(expected >= {TRADING_DAYS_PER_YEAR})"
            )
            print(f"[OK] daily_prices rows for {ticker}: {count_rows}")

        # 2) most recent daily_prices date is within 5 trading days of today
        for ticker in tickers:
            latest_date = session.scalar(
                select(func.max(DailyPrice.date)).where(DailyPrice.ticker == ticker)
            )
            assert latest_date is not None, f"[FAIL] no latest date for {ticker} in daily_prices"
            bday_gap = _business_day_distance(latest_date, today_et)
            assert bday_gap <= 5, (
                f"[FAIL] latest daily_prices date for {ticker} is too old: "
                f"{latest_date} (business days gap={bday_gap})"
            )
            print(f"[OK] latest daily_prices date for {ticker}: {latest_date} (bdays gap={bday_gap})")

        # 3) live_price has a row per watched ticker only if market is open
        if market_open_now:
            for ticker in tickers:
                row_count = session.scalar(
                    select(func.count()).select_from(LivePrice).where(LivePrice.ticker == ticker)
                ) or 0
                assert row_count == 1, f"[FAIL] live_price missing row for {ticker} while market open"
                print(f"[OK] live_price row present for {ticker}")
        else:
            print("[INFO] market is closed (ET): skipping strict live_price row check")

        # 4) risk_free_rate has one row and a reasonable range
        rate_rows = session.scalars(select(RiskFreeRate)).all()
        assert len(rate_rows) == 1, f"[FAIL] risk_free_rate row count={len(rate_rows)} (expected 1)"
        rate = float(rate_rows[0].rate)
        assert 0.01 <= rate <= 0.15, f"[FAIL] risk_free_rate out of expected range: {rate}"
        print(f"[OK] risk_free_rate present and in range: {rate:.6f}")

        # 6) vol_surface table exists and is empty in this phase
        vol_surface_count = session.scalar(select(func.count()).select_from(VolSurface)) or 0
        assert vol_surface_count == 0, (
            f"[FAIL] vol_surface should be empty in Spec A, found {vol_surface_count} rows"
        )
        print("[OK] vol_surface exists and is empty")

    # 5) calculate_historical_vol returns reasonable float for each ticker
    for ticker in tickers:
        sigma = calculate_historical_vol(ticker)
        assert isinstance(sigma, float), f"[FAIL] sigma for {ticker} is not float: {type(sigma)}"
        assert 0.05 <= sigma <= 1.5, f"[FAIL] sigma for {ticker} out of range: {sigma}"
        print(f"[OK] historical volatility for {ticker}: {sigma:.6f}")

    print("\nAll Spec A data checks passed.")


if __name__ == "__main__":
    main()
