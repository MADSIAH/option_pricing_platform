"""Database setup for Spec B data-fetching layer (SQLite + SQLAlchemy)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Float, Index, Integer, String, UniqueConstraint, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DEFAULT_DB_PATH = "data/market_data.db"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class DailyPrice(Base):
    """One row per ticker per trading day (append-only, 1y retention via cleanup job)."""

    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)  # ISO date, e.g. 2026-05-07
    adj_close: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="yfinance")

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_daily_prices_ticker_date"),
        Index("ix_daily_prices_ticker_date", "ticker", "date"),
    )


class LivePrice(Base):
    """Latest intraday spot price per ticker (upsert)."""

    __tablename__ = "live_price"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    spot_price: Mapped[float] = mapped_column(Float, nullable=False)
    dividend_yield: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)  # UTC ISO datetime


class OptionChain(Base):
    """Latest option-chain snapshot per ticker (replace-on-refresh)."""

    __tablename__ = "option_chain"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    expiry: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    strike: Mapped[float] = mapped_column(Float, nullable=False)
    option_type: Mapped[str] = mapped_column(String, nullable=False)  # call | put
    bid: Mapped[float] = mapped_column(Float, nullable=False)
    ask: Mapped[float] = mapped_column(Float, nullable=False)
    mid_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_interest: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    implied_vol: Mapped[float] = mapped_column(Float, nullable=False)
    T: Mapped[float] = mapped_column(Float, nullable=False)  # years to expiry
    fetched_at: Mapped[str] = mapped_column(String, nullable=False)  # UTC ISO datetime

    __table_args__ = (
        Index("ix_option_chain_ticker_expiry_type", "ticker", "expiry", "option_type"),
    )


class VolSurface(Base):
    """
    Latest implied-vol surface snapshot per ticker.

    Populated from yfinance option-chain impliedVolatility in Spec B.
    """

    __tablename__ = "vol_surface"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    expiry: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    strike: Mapped[float] = mapped_column(Float, nullable=False)
    implied_vol: Mapped[float] = mapped_column(Float, nullable=False)
    T: Mapped[float] = mapped_column(Float, nullable=False)  # years to expiry
    fetched_at: Mapped[str] = mapped_column(String, nullable=False)  # UTC ISO datetime

    __table_args__ = (
        Index("ix_vol_surface_ticker_fetched_at", "ticker", "fetched_at"),
    )


class RiskFreeRate(Base):
    """Single-row table (id=1), upserted on each refresh."""

    __tablename__ = "risk_free_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # decimal, e.g. 0.043
    updated_at: Mapped[str] = mapped_column(String, nullable=False)  # UTC ISO datetime


_ENGINE = None
_SESSION_FACTORY: sessionmaker[Session] | None = None


def _resolve_db_path() -> Path:
    raw = os.getenv("DB_PATH", DEFAULT_DB_PATH).strip() or DEFAULT_DB_PATH
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_engine():
    """Return singleton SQLAlchemy engine bound to SQLite DB_PATH."""
    global _ENGINE
    if _ENGINE is None:
        db_path = _resolve_db_path()
        _ENGINE = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            future=True,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _ENGINE


def get_session_factory() -> sessionmaker[Session]:
    """Return singleton Session factory."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True, expire_on_commit=False)
    return _SESSION_FACTORY


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session scope helper."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Create all tables if they do not already exist.

    Also applies lightweight SQLite schema evolution needed for Spec B.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # WAL mode allows concurrent readers + one writer without blocking.
        # busy_timeout gives readers up to 5 s to wait on a write lock instead of
        # immediately raising OperationalError("database is locked").
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))

        # SQLite create_all() does not ALTER existing tables; add new columns if needed.
        table_info = conn.execute(text("PRAGMA table_info(vol_surface)")).fetchall()
        existing_cols = {str(row[1]) for row in table_info}
        if "T" not in existing_cols:
            conn.execute(text("ALTER TABLE vol_surface ADD COLUMN T REAL"))
