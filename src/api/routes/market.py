"""Market-data endpoints for Spec C API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.api.schemas import (
    MarketResponse,
    OptionChainResponse,
    OptionChainRow,
    OptionChainType,
    OptionType,
)
from src.data.database import OptionChain, session_scope
from src.data.fetcher import (
    InsufficientDataError,
    calculate_historical_vol,
    get_atm_vol,
    get_latest_live_price,
    get_latest_risk_free_rate,
)

STALE_AFTER = timedelta(minutes=90)
STALE_RATE_AFTER = timedelta(days=7)

router = APIRouter(tags=["market"])


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _is_stale(updated_at: str) -> bool:
    return datetime.now(timezone.utc) - _parse_utc(updated_at) > STALE_AFTER


def _rate_is_stale(rate: dict) -> bool:
    return datetime.now(timezone.utc) - _parse_utc(str(rate["updated_at"])) > STALE_RATE_AFTER


def _error(status_code: int, message: str, detail: str | None = None) -> JSONResponse:
    payload: dict[str, str] = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/market/{ticker}", response_model=MarketResponse)
def get_market(ticker: str) -> MarketResponse | JSONResponse:
    norm_ticker = ticker.strip().upper()

    try:
        live = get_latest_live_price(norm_ticker)
        if live is None:
            return _error(404, "Ticker not found")

        rate = get_latest_risk_free_rate()
        if rate is None:
            risk_free_rate: float | None = None
            risk_free_rate_warning: str | None = "Risk-free rate not in DB; please enter manually"
            rate_stale = True
        else:
            risk_free_rate = float(rate["rate"])
            risk_free_rate_warning = None
            rate_stale = _rate_is_stale(rate)

        historical_vol_warning: str | None = None
        try:
            historical_vol: float | None = calculate_historical_vol(norm_ticker)
        except InsufficientDataError as exc:
            historical_vol = None
            historical_vol_warning = str(exc)

        atm = get_atm_vol(norm_ticker)
        atm_iv = None if atm is None else float(atm["implied_vol"])

        updated_candidates = [str(live["updated_at"])]
        if atm is not None:
            updated_candidates.append(str(atm["fetched_at"]))

        updated_dt = min(_parse_utc(ts) for ts in updated_candidates)
        updated_at = updated_dt.isoformat()

        stale = _is_stale(updated_at) or rate_stale or historical_vol is None

        return MarketResponse(
            ticker=norm_ticker,
            spot_price=float(live["spot_price"]),
            historical_vol=historical_vol,
            historical_vol_warning=historical_vol_warning,
            atm_implied_vol=atm_iv,
            risk_free_rate=risk_free_rate,
            risk_free_rate_warning=risk_free_rate_warning,
            dividend_yield=float(live["dividend_yield"]),
            updated_at=updated_at,
            stale=stale,
            data_source="database",
        )
    except Exception as exc:
        return _error(500, "Market lookup failed", str(exc))


@router.get("/option_chain/{ticker}", response_model=OptionChainResponse)
def get_option_chain(
    ticker: str,
    option_type: OptionChainType = Query(default=OptionChainType.both),
) -> OptionChainResponse | JSONResponse:
    norm_ticker = ticker.strip().upper()
    try:
        with session_scope() as session:
            stmt = select(OptionChain).where(OptionChain.ticker == norm_ticker)
            if option_type != OptionChainType.both:
                stmt = stmt.where(OptionChain.option_type == option_type.value)
            stmt = stmt.order_by(OptionChain.expiry.asc(), OptionChain.strike.asc())
            rows = session.scalars(stmt).all()

        if not rows:
            return _error(404, "Ticker not found")

        updated_at = min(str(row.fetched_at) for row in rows)
        payload_rows = [
            OptionChainRow(
                expiry=str(row.expiry),
                strike=float(row.strike),
                option_type=OptionType(str(row.option_type)),
                bid=float(row.bid),
                ask=float(row.ask),
                mid_price=float(row.mid_price),
                volume=int(row.volume),
                open_interest=int(row.open_interest),
                implied_vol=float(row.implied_vol),
                T=float(row.T),
                fetched_at=str(row.fetched_at),
            )
            for row in rows
        ]
        return OptionChainResponse(
            ticker=norm_ticker,
            option_type=option_type,
            rows=payload_rows,
            updated_at=updated_at,
            stale=_is_stale(updated_at),
            data_source="database",
        )
    except Exception as exc:
        return _error(500, "Option chain lookup failed", str(exc))
