"""Surface and profile endpoints for Spec C API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from scipy.interpolate import griddata
from sqlalchemy import select

from src.api.schemas import (
    GreeksProfilePoint,
    GreeksProfileRequest,
    GreeksProfileResponse,
    MarketPricePoint,
    PriceSurfaceRequest,
    PriceSurfaceResponse,
    SigmaType,
    VolSurfaceGrid,
    VolSurfaceResponse,
)
from src.data.database import OptionChain, VolSurface, session_scope
from src.data.fetcher import (
    InsufficientDataError,
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
STALE_RATE_AFTER = timedelta(days=7)
T_MIN = 0.05
T_MAX = 1.5

router = APIRouter(tags=["surface"])


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


def _resolve_sigma(
    ticker: str,
    sigma: float | None,
    sigma_type: SigmaType,
) -> tuple[float, str, bool, str | None]:
    """Return (sigma, source, fallback, fetched_at). No cross-type fallbacks."""
    if sigma is not None:
        return float(sigma), "user_provided", False, None

    if sigma_type == SigmaType.implied:
        atm = get_atm_vol(ticker)
        if atm is not None:
            return float(atm["implied_vol"]), "implied", False, str(atm["fetched_at"])
        raise InsufficientDataError(
            f"ATM implied vol unavailable for {ticker}: vol surface has not been computed yet"
        )

    # sigma_type == SigmaType.historical
    try:
        hist = calculate_historical_vol(ticker)
        return float(hist), "historical", False, None
    except InsufficientDataError as exc:
        raise InsufficientDataError(
            f"Historical vol unavailable for {ticker}: {exc}"
        ) from exc


def _build_vol_surface_grid(rows: list, n_grid: int = 60) -> VolSurfaceGrid | None:
    """Interpolate scattered (T, strike) → IV points onto a regular grid."""
    if len(rows) < 4:
        return None
    try:
        strikes = np.array([float(r.strike) for r in rows])
        ts = np.array([float(r.T) for r in rows])
        ivs = np.array([float(r.implied_vol) * 100.0 for r in rows])

        t_lin = np.linspace(ts.min(), ts.max(), n_grid)
        k_lin = np.linspace(strikes.min(), strikes.max(), n_grid)
        # TT[i,j] = t_lin[j], KK[i,j] = k_lin[i] → z shape (n_K, n_T)
        TT, KK = np.meshgrid(t_lin, k_lin)

        pts = np.column_stack([ts, strikes])
        z_cubic = griddata(pts, ivs, (TT, KK), method="cubic", rescale=True)
        z_linear = griddata(pts, ivs, (TT, KK), method="linear", rescale=True)
        z = np.where(np.isnan(z_cubic), z_linear, z_cubic)
        z = np.clip(z, 1.0, 150.0)

        return VolSurfaceGrid(
            T_values=t_lin.tolist(),
            K_values=k_lin.tolist(),
            z=[[None if np.isnan(v) else float(v) for v in row] for row in z.tolist()],
        )
    except Exception:
        return None


@router.get("/vol_surface/{ticker}", response_model=VolSurfaceResponse)
def get_vol_surface(
    ticker: str,
    option_type: str = Query(default="call"),
) -> VolSurfaceResponse | JSONResponse:
    norm_ticker = ticker.strip().upper()
    opt = option_type.lower().strip()
    try:
        with session_scope() as session:
            if opt == "put":
                rows = session.scalars(
                    select(OptionChain).where(
                        OptionChain.ticker == norm_ticker,
                        OptionChain.option_type == "put",
                        OptionChain.T > (30 / 365),
                        OptionChain.implied_vol > 0.01,
                        OptionChain.implied_vol <= 2.0,
                        OptionChain.bid > 0,
                    ).order_by(OptionChain.expiry.asc(), OptionChain.strike.asc())
                ).all()
            else:
                rows = session.scalars(
                    select(VolSurface)
                    .where(VolSurface.ticker == norm_ticker)
                    .order_by(VolSurface.expiry.asc(), VolSurface.strike.asc())
                ).all()
                if not rows:
                    rows = session.scalars(
                        select(OptionChain).where(
                            OptionChain.ticker == norm_ticker,
                            OptionChain.option_type == "call",
                            OptionChain.T > (30 / 365),
                            OptionChain.implied_vol > 0.01,
                            OptionChain.implied_vol <= 2.0,
                            OptionChain.bid > 0,
                        ).order_by(OptionChain.expiry.asc(), OptionChain.strike.asc())
                    ).all()

        if not rows:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "reason": "Vol surface not yet computed"},
            )

        updated_at = min(str(row.fetched_at) for row in rows)
        points = [
            {"expiry": str(r.expiry), "T": float(r.T), "strike": float(r.strike), "implied_vol": float(r.implied_vol)}
            for r in rows
        ]
        grid = _build_vol_surface_grid(rows)

        return VolSurfaceResponse(
            ticker=norm_ticker,
            points=points,
            grid=grid,
            updated_at=updated_at,
            stale=_is_stale(updated_at),
            data_source="database",
        )
    except Exception as exc:
        return _error(500, "Vol surface lookup failed", str(exc))


@router.post("/price_surface", response_model=PriceSurfaceResponse)
def price_surface(payload: PriceSurfaceRequest) -> PriceSurfaceResponse | JSONResponse:
    """
    Compute option price surface over a K × T grid (varying strike, fixed spot).
    Mirrors the notebook: x=K, y=T, z=price, with real market mid-prices overlaid.
    """
    ticker = payload.ticker.strip().upper()
    try:
        live = get_latest_live_price(ticker)
        if live is None:
            return _error(404, "Ticker not found")

        S_ref = float(payload.S) if payload.S is not None else float(live["spot_price"])
        q = float(payload.q) if payload.q is not None else float(live["dividend_yield"])

        rate_stale = False
        if payload.r is None:
            rate_row = get_latest_risk_free_rate()
            if rate_row is None:
                return _error(503, "Risk-free rate not available; you can provide r in the request body")
            r = float(rate_row["rate"])
            rate_stale = _rate_is_stale(rate_row)
        else:
            r = float(payload.r)

        sigma, sigma_source, sigma_fallback, sigma_ts = _resolve_sigma(
            ticker=ticker,
            sigma=payload.sigma,
            sigma_type=payload.sigma_type,
        )

        model = BlackScholes() if payload.style.value == "european" else BaroneAdesiWhaley()

        K_min = S_ref * payload.K_min_frac
        K_max = S_ref * payload.K_max_frac
        K_range = np.linspace(K_min, K_max, payload.n_K)
        T_range = np.linspace(T_MIN, T_MAX, payload.n_T)

        # z[T_idx][K_idx] = price — matches Plotly surface(x=K, y=T, z=z)
        z: list[list[float]] = []
        for T_val in T_range:
            row = []
            for K_val in K_range:
                try:
                    params = OptionParams(
                        S=S_ref,
                        K=float(K_val),
                        T=float(T_val),
                        r=r,
                        sigma=sigma,
                        option_type=payload.option_type.value,
                        q=q,
                    )
                    row.append(float(model.price(params).price))
                except Exception:
                    row.append(float("nan"))
            z.append(row)

        # Market mid-prices overlay from option_chain table
        market_points: list[MarketPricePoint] = []
        try:
            with session_scope() as session:
                chain_rows = session.scalars(
                    select(OptionChain).where(
                        OptionChain.ticker == ticker,
                        OptionChain.option_type == payload.option_type.value,
                        OptionChain.T >= T_MIN,
                        OptionChain.T <= T_MAX,
                        OptionChain.strike >= K_min,
                        OptionChain.strike <= K_max,
                    )
                ).all()
            market_points = [
                MarketPricePoint(K=float(cr.strike), T=float(cr.T), mid_price=float(cr.mid_price))
                for cr in chain_rows
                if float(cr.mid_price) > 0
            ]
        except Exception:
            pass

        timestamps = [str(live["updated_at"])]
        if sigma_ts is not None:
            timestamps.append(sigma_ts)
        updated_at = min(timestamps, key=_parse_utc)

        return PriceSurfaceResponse(
            ticker=ticker,
            option_type=payload.option_type,
            style=payload.style,
            S_ref=S_ref,
            sigma=sigma,
            sigma_source=sigma_source,
            sigma_fallback=sigma_fallback,
            K_values=K_range.tolist(),
            T_values=T_range.tolist(),
            z=z,
            market_points=market_points,
            data_source="database",
            updated_at=updated_at,
            stale=_is_stale(updated_at) or rate_stale,
        )
    except InsufficientDataError as exc:
        return _error(503, f"Volatility data not available: {exc} You can provide sigma in the request body.")
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

            rate_stale = False
            if payload.r is None:
                rate_row = get_latest_risk_free_rate()
                if rate_row is None:
                    return _error(503, "Risk-free rate not available; you can provide r in the request body")
                r = float(rate_row["rate"])
                rate_stale = _rate_is_stale(rate_row)
            else:
                r = float(payload.r)

            sigma, sigma_source, sigma_fallback, sigma_ts = _resolve_sigma(
                ticker=ticker,
                sigma=payload.sigma,
                sigma_type=payload.sigma_type,
            )

            ts_candidates = [str(live["updated_at"])]
            if sigma_ts is not None:
                ts_candidates.append(sigma_ts)
            updated_at = min(ts_candidates, key=_parse_utc)
            stale = _is_stale(updated_at) or rate_stale
            data_source = "database"
        else:
            ticker = None
            S = float(payload.S)
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
    except InsufficientDataError as exc:
        return _error(503, f"Volatility data not available: {exc} You can provide sigma in the request body.")
    except ValueError as exc:
        return _error(422, str(exc))
    except Exception as exc:
        return _error(500, "Greeks profile failed", str(exc))
