"""Manual validation script for Spec B data layer."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import func, or_, select

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.database import (
    DailyPrice,
    LivePrice,
    OptionChain,
    RiskFreeRate,
    VolSurface,
    init_db,
    session_scope,
)
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

        # 7) option_chain has rows for each watched ticker
        for ticker in tickers:
            chain_count = session.scalar(
                select(func.count()).select_from(OptionChain).where(OptionChain.ticker == ticker)
            ) or 0
            assert chain_count > 0, f"[FAIL] option_chain has no rows for {ticker}"
            print(f"[OK] option_chain rows for {ticker}: {chain_count}")

        # 8) option_chain rows have non-null implied_vol, strike, expiry, T
        for ticker in tickers:
            invalid_chain_rows = session.scalar(
                select(func.count())
                .select_from(OptionChain)
                .where(
                    OptionChain.ticker == ticker,
                    or_(
                        OptionChain.implied_vol.is_(None),
                        OptionChain.strike.is_(None),
                        OptionChain.expiry.is_(None),
                        OptionChain.expiry == "",
                        OptionChain.T.is_(None),
                    ),
                )
            ) or 0
            assert invalid_chain_rows == 0, (
                f"[FAIL] option_chain has {invalid_chain_rows} rows with null required fields for {ticker}"
            )
            print(f"[OK] option_chain required fields are non-null for {ticker}")

        # 9) vol_surface has rows for each watched ticker
        for ticker in tickers:
            surface_count = session.scalar(
                select(func.count()).select_from(VolSurface).where(VolSurface.ticker == ticker)
            ) or 0
            assert surface_count > 0, f"[FAIL] vol_surface has no rows for {ticker}"
            print(f"[OK] vol_surface rows for {ticker}: {surface_count}")

        # 10) vol_surface implied_vol values are between 0.01 and 2.0
        for ticker in tickers:
            bad_iv_count = session.scalar(
                select(func.count())
                .select_from(VolSurface)
                .where(
                    VolSurface.ticker == ticker,
                    or_(VolSurface.implied_vol < 0.01, VolSurface.implied_vol > 2.0),
                )
            ) or 0
            assert bad_iv_count == 0, (
                f"[FAIL] vol_surface has {bad_iv_count} out-of-range implied_vol rows for {ticker}"
            )
            print(f"[OK] vol_surface implied_vol range valid for {ticker}")

        # 11) vol_surface has no NaN/NULL implied_vol
        for ticker in tickers:
            null_iv_count = session.scalar(
                select(func.count())
                .select_from(VolSurface)
                .where(VolSurface.ticker == ticker, VolSurface.implied_vol.is_(None))
            ) or 0
            assert null_iv_count == 0, (
                f"[FAIL] vol_surface has {null_iv_count} NULL implied_vol rows for {ticker}"
            )
            print(f"[OK] vol_surface implied_vol non-null for {ticker}")

        # 12) vol_surface only contains rows with T > 30/365
        for ticker in tickers:
            bad_t_count = session.scalar(
                select(func.count())
                .select_from(VolSurface)
                .where(
                    VolSurface.ticker == ticker,
                    or_(VolSurface.T.is_(None), VolSurface.T <= (30.0 / 365.0)),
                )
            ) or 0
            assert bad_t_count == 0, f"[FAIL] vol_surface has {bad_t_count} rows with T <= 30/365 for {ticker}"
            print(f"[OK] vol_surface maturity filter valid for {ticker}")

    # 5) calculate_historical_vol returns reasonable float for each ticker
    for ticker in tickers:
        sigma = calculate_historical_vol(ticker)
        assert isinstance(sigma, float), f"[FAIL] sigma for {ticker} is not float: {type(sigma)}"
        assert 0.05 <= sigma <= 1.5, f"[FAIL] sigma for {ticker} out of range: {sigma}"
        print(f"[OK] historical volatility for {ticker}: {sigma:.6f}")

    print("\nAll Spec B data checks passed.")


if __name__ == "__main__":
    main()
