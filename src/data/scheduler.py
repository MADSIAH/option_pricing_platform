"""APScheduler orchestration for Spec B data jobs."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete

from .database import DailyPrice, LivePrice, OptionChain, VolSurface, init_db, session_scope
from .fetcher import (
    ET,
    backfill_daily_prices,
    fetch_and_store_option_data,
    fetch_risk_free_rate,
    is_market_open,
    refresh_daily_price,
    refresh_live_price,
)

logger = logging.getLogger(__name__)

WATCHED_TICKERS: set[str] = {
    t.strip().upper()
    for t in os.getenv("WATCHED_TICKERS", "AAPL,SPY,TSLA").split(",")
    if t.strip()
}

scheduler = BackgroundScheduler(timezone="America/New_York")


def safe_job(func):
    """Prevent a single scheduler job failure from crashing the process."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Job %s failed", func.__name__)
            return None

    return wrapper


@safe_job
def backfill_all_tickers() -> None:
    for ticker in sorted(WATCHED_TICKERS):
        try:
            inserted = backfill_daily_prices(ticker)
            logger.info("backfill_daily_prices | ticker=%s inserted=%s", ticker, inserted)
        except Exception:
            logger.exception("backfill_daily_prices failed | ticker=%s", ticker)


@safe_job
def refresh_all_live_prices() -> None:
    if not is_market_open():
        logger.info("refresh_all_live_prices skipped: market closed (ET).")
        return

    for ticker in sorted(WATCHED_TICKERS):
        try:
            refresh_live_price(ticker)
            logger.info("refresh_live_price | ticker=%s", ticker)
        except Exception:
            logger.exception("refresh_live_price failed | ticker=%s", ticker)


@safe_job
def refresh_all_daily_prices() -> None:
    for ticker in sorted(WATCHED_TICKERS):
        try:
            refresh_daily_price(ticker)
            logger.info("refresh_daily_price | ticker=%s", ticker)
        except Exception:
            logger.exception("refresh_daily_price failed | ticker=%s", ticker)


@safe_job
def refresh_all_option_data() -> None:
    if not is_market_open():
        logger.info("refresh_all_option_data skipped: market closed (ET).")
        return

    for ticker in sorted(WATCHED_TICKERS):
        try:
            ok = fetch_and_store_option_data(ticker)
            if ok:
                logger.info("refresh_option_data | ticker=%s success=true", ticker)
            else:
                logger.error("refresh_option_data | ticker=%s success=false", ticker)
        except Exception:
            logger.exception("refresh_option_data failed | ticker=%s", ticker)


@safe_job
def refresh_risk_free_rate() -> None:
    try:
        rate = fetch_risk_free_rate()
        logger.info("refresh_risk_free_rate | rate=%.6f", rate)
    except Exception:
        logger.exception("refresh_risk_free_rate failed")


@safe_job
def cleanup_old_rows() -> None:
    cutoff_date = (datetime.now(ET).date() - timedelta(days=365)).isoformat()
    with session_scope() as session:
        result = session.execute(delete(DailyPrice).where(DailyPrice.date < cutoff_date))
        deleted = int(result.rowcount or 0)
    logger.info("cleanup_old_rows | daily_prices deleted=%s cutoff=%s", deleted, cutoff_date)
    if deleted > 0:
        backfill_all_tickers()


def add_ticker(ticker: str) -> None:
    norm = ticker.strip().upper()
    if not norm:
        raise ValueError("ticker cannot be empty")
    if norm in WATCHED_TICKERS:
        logger.info("add_ticker skipped: %s already watched", norm)
        return

    WATCHED_TICKERS.add(norm)
    inserted = backfill_daily_prices(norm)
    refresh_live_price(norm)
    logger.info("add_ticker complete | ticker=%s inserted_backfill=%s", norm, inserted)


def remove_ticker(ticker: str) -> None:
    norm = ticker.strip().upper()
    if not norm:
        raise ValueError("ticker cannot be empty")
    if norm not in WATCHED_TICKERS:
        logger.info("remove_ticker skipped: %s not watched", norm)
        return

    WATCHED_TICKERS.remove(norm)
    with session_scope() as session:
        session.execute(delete(LivePrice).where(LivePrice.ticker == norm))
        session.execute(delete(OptionChain).where(OptionChain.ticker == norm))
        session.execute(delete(VolSurface).where(VolSurface.ticker == norm))
    logger.info("remove_ticker complete | ticker=%s", norm)


def configure_jobs() -> None:
    scheduler.add_job(
        refresh_all_live_prices,
        trigger="interval",
        minutes=60,
        id="refresh_all_live_prices",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_all_daily_prices,
        trigger="cron",
        hour=18,
        minute=30,
        id="refresh_all_daily_prices",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_all_option_data,
        trigger="interval",
        minutes=60,
        id="refresh_all_option_data",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_risk_free_rate,
        trigger="cron",
        hour=8,
        minute=0,
        id="refresh_risk_free_rate",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_rows,
        trigger="cron",
        hour=2,
        minute=0,
        id="cleanup_old_rows",
        replace_existing=True,
    )


def startup_sequence() -> None:
    init_db()
    logger.info("init_db complete")
    backfill_all_tickers()
    refresh_risk_free_rate()
    refresh_all_live_prices()
    refresh_all_option_data()


def run_forever() -> None:
    configure_jobs()
    startup_sequence()
    scheduler.start()
    logger.info(
        "scheduler started | timezone=America/New_York | watched_tickers=%s",
        sorted(WATCHED_TICKERS),
    )

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler shutdown requested")
        scheduler.shutdown(wait=False)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    run_forever()


if __name__ == "__main__":
    main()
