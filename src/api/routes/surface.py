"""Surface and profile endpoints for Spec C API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.api.schemas import (
    GreeksProfilePoint,
    GreeksProfileRequest,
    GreeksProfileResponse,
    PriceSurfacePoint,
    PriceSurfaceRequest,
    PriceSurfaceResponse,
    SigmaType,
    VolSurfacePoint,
    VolSurfaceResponse,
)
from src.data.database import VolSurface, session_scope
from src.data.fetcher import (
    calculate_historical_vol,
    get_atm_vol,
    get_latest_live_price,
    get_latest_risk_free_rate,
)
from src.pricing.base import OptionParams
from src.pricing.baw import BaroneAdesiWhaley
from src.pricing.black_scholes import BlackScholes
from src.pricing.greeks import AnalyticalGreeks

STALE_AFTER = timedelta(minutes=90)
S_MIN_MULT = 0.7
S_MAX_MULT = 1.3
S_STEPS = 25
T_MIN = 0.05
T_MAX = 1.5
T_STEPS = 25

router = APIRouter(tags=["surface"])


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _is_stale(updated_at: str) -> bool:
    return datetime.now(timezone.utc) - _parse_utc(updated_at) > STALE_AFTER


def _error(status_code: int, message: str, detail: str | None = None) -> JSONResponse:
    payload: dict[str, str] = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


def _resolve_sigma(
    ticker: str,
    sigma: float | None,
    sigma_type: SigmaType,
) -> tuple[float, str, bool, str | None]:
    if sigma is not None:
        return float(sigma), "user_provided", False, None

    if sigma_type == SigmaType.implied:
        atm = get_atm_vol(ticker)
        if atm is not None:
            return float(atm["implied_vol"]), "implied", False, str(atm["fetched_at"])
        try:
            hist = calculate_historical_vol(ticker)
            return float(hist), "historical", True, None
        except ValueError as exc:
            raise ValueError("Implied vol unavailable and no fallback sigma provided") from exc

    try:
        hist = calculate_historical_vol(ticker)
    except ValueError as exc:
        raise ValueError("No valid historical sigma available") from exc
    return float(hist), "historical", False, None


@router.get("/vol_surface/{ticker}", response_model=VolSurfaceResponse)
def get_vol_surface(ticker: str) -> VolSurfaceResponse | JSONResponse:
    norm_ticker = ticker.strip().upper()
    try:
        with session_scope() as session:
            rows = session.scalars(
                select(VolSurface)
                .where(VolSurface.ticker == norm_ticker)
                .order_by(VolSurface.expiry.asc(), VolSurface.strike.asc())
            ).all()

        if not rows:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "reason": "Vol surface not yet computed"},
            )

        updated_at = min(str(row.fetched_at) for row in rows)
        points = [
            VolSurfacePoint(
                expiry=str(row.expiry),
                T=float(row.T),
                strike=float(row.strike),
                implied_vol=float(row.implied_vol),
            )
            for row in rows
        ]
        return VolSurfaceResponse(
            ticker=norm_ticker,
            points=points,
            updated_at=updated_at,
            stale=_is_stale(updated_at),
            data_source="database",
        )
    except Exception as exc:
        return _error(500, "Vol surface lookup failed", str(exc))


@router.post("/price_surface", response_model=PriceSurfaceResponse)
def price_surface(payload: PriceSurfaceRequest) -> PriceSurfaceResponse | JSONResponse:
    ticker = payload.ticker.strip().upper()
    try:
        live = get_latest_live_price(ticker)
        if live is None:
            return _error(404, "Ticker not found")

        S_ref = float(payload.S) if payload.S is not None else float(live["spot_price"])
        q = float(payload.q) if payload.q is not None else float(live["dividend_yield"])

        rate_updated_at: str | None = None
        if payload.r is None:
            rate_row = get_latest_risk_free_rate()
            if rate_row is None:
                return _error(503, "Market data unavailable", "Risk-free rate not available")
            r = float(rate_row["rate"])
            rate_updated_at = str(rate_row["updated_at"])
        else:
            r = float(payload.r)

        sigma, sigma_source, sigma_fallback, sigma_ts = _resolve_sigma(
            ticker=ticker,
            sigma=payload.sigma,
            sigma_type=payload.sigma_type,
        )

        model = BlackScholes() if payload.style.value == "european" else BaroneAdesiWhaley()

        s_values = np.linspace(S_MIN_MULT * S_ref, S_MAX_MULT * S_ref, S_STEPS)
        t_values = np.linspace(T_MIN, T_MAX, T_STEPS)
        points: list[PriceSurfacePoint] = []
        for T in t_values:
            for S in s_values:
                params = OptionParams(
                    S=float(S),
                    K=float(payload.K),
                    T=float(T),
                    r=r,
                    sigma=sigma,
                    option_type=payload.option_type.value,
                    q=q,
                )
                price = float(model.price(params).price)
                points.append(PriceSurfacePoint(S=float(S), T=float(T), price=price))

        timestamps = [str(live["updated_at"])]
        if rate_updated_at is not None:
            timestamps.append(rate_updated_at)
        if sigma_ts is not None:
            timestamps.append(sigma_ts)
        updated_at = min(timestamps, key=_parse_utc)

        return PriceSurfaceResponse(
            ticker=ticker,
            option_type=payload.option_type,
            style=payload.style,
            K=float(payload.K),
            S_ref=S_ref,
            sigma=sigma,
            sigma_source=sigma_source,
            sigma_fallback=sigma_fallback,
            points=points,
            data_source="database",
            updated_at=updated_at,
            stale=_is_stale(updated_at),
        )
    except ValueError as exc:
        return _error(422, str(exc))
    except Exception as exc:
        return _error(500, "Pricing failed", str(exc))


@router.post("/greeks_profile", response_model=GreeksProfileResponse)
def greeks_profile(payload: GreeksProfileRequest) -> GreeksProfileResponse | JSONResponse:
    try:
        if payload.ticker is not None:
            ticker = payload.ticker.strip().upper()
            live = get_latest_live_price(ticker)
            if live is None:
                return _error(404, "Ticker not found")

            S = float(payload.S) if payload.S is not None else float(live["spot_price"])
            q = float(payload.q) if payload.q is not None else float(live["dividend_yield"])

            rate_updated_at: str | None = None
            if payload.r is None:
                rate_row = get_latest_risk_free_rate()
                if rate_row is None:
                    return _error(503, "Market data unavailable", "Risk-free rate not available")
                r = float(rate_row["rate"])
                rate_updated_at = str(rate_row["updated_at"])
            else:
                r = float(payload.r)

            sigma, sigma_source, sigma_fallback, sigma_ts = _resolve_sigma(
                ticker=ticker,
                sigma=payload.sigma,
                sigma_type=payload.sigma_type,
            )

            ts_candidates = [str(live["updated_at"])]
            if rate_updated_at is not None:
                ts_candidates.append(rate_updated_at)
            if sigma_ts is not None:
                ts_candidates.append(sigma_ts)
            updated_at = min(ts_candidates, key=_parse_utc)
            stale = _is_stale(updated_at)
            data_source = "database"
        else:
            ticker = None
            S = float(payload.S)  # validated at schema level
            r = float(payload.r)
            q = float(payload.q)
            sigma = float(payload.sigma)
            sigma_source = "user_provided"
            sigma_fallback = False
            updated_at = None
            stale = False
            data_source = "user_provided"

        greeks_engine = AnalyticalGreeks()
        x_values = np.linspace(payload.range_min, payload.range_max, payload.steps)
        points: list[GreeksProfilePoint] = []
        for x in x_values:
            cur_S = float(x) if payload.vary_by.value == "S" else float(S)
            cur_T = float(x) if payload.vary_by.value == "T" else float(payload.T)
            params = OptionParams(
                S=cur_S,
                K=float(payload.K),
                T=cur_T,
                r=r,
                sigma=sigma,
                option_type=payload.option_type.value,
                q=q,
            )
            g = greeks_engine.compute(params)
            points.append(
                GreeksProfilePoint(
                    x=float(x),
                    delta=float(g.delta),
                    gamma=float(g.gamma),
                    vega=float(g.vega),
                    theta=float(g.theta),
                    rho=float(g.rho),
                )
            )

        return GreeksProfileResponse(
            ticker=ticker,
            option_type=payload.option_type,
            vary_by=payload.vary_by,
            K=float(payload.K),
            S=float(S),
            T=float(payload.T),
            r=r,
            q=q,
            sigma=sigma,
            sigma_source=sigma_source,
            sigma_fallback=sigma_fallback,
            points=points,
            data_source=data_source,
            updated_at=updated_at,
            stale=stale,
        )
    except ValueError as exc:
        return _error(422, str(exc))
    except Exception as exc:
        return _error(500, "Greeks profile failed", str(exc))
