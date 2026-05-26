"""Pricing endpoint for Spec C API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.schemas import (
    GreekValues,
    OptionStyle,
    PriceModelOutput,
    PriceRequest,
    PriceResponse,
    PricingMethod,
    SigmaType,
)
from src.data.fetcher import (
    InsufficientDataError,
    calculate_historical_vol,
    get_atm_vol,
    get_latest_live_price,
    get_latest_risk_free_rate,
)
from src.pricing.base import OptionParams, PricingModel
from src.pricing.baw import BaroneAdesiWhaley
from src.pricing.binomial_tree import BinomialTree
from src.pricing.black_scholes import BlackScholes
from src.pricing.greeks import AnalyticalGreeks, NumericalGreeks
from src.pricing.longstaff_schwartz import LongstaffSchwartz
from src.pricing.monte_carlo import MonteCarlo

STALE_AFTER = timedelta(minutes=90)
STALE_RATE_AFTER = timedelta(days=7)

router = APIRouter(tags=["pricing"])


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
    *,
    ticker: str | None,
    sigma: float | None,
    sigma_type: SigmaType,
) -> tuple[float, str, bool, str | None]:
    """Return (sigma, source, fallback, fetched_at)."""
    if sigma is not None:
        return float(sigma), "user_provided", False, None

    if ticker is None:
        raise ValueError("Custom stock requires S, r, q, sigma")

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


def _validate_style_method(style: OptionStyle, method: PricingMethod) -> None:
    if style == OptionStyle.european:
        valid = {
            PricingMethod.black_scholes,
            PricingMethod.monte_carlo,
            PricingMethod.binomial_tree,
            PricingMethod.all,
        }
    else:
        valid = {
            PricingMethod.baw,
            PricingMethod.binomial_tree,
            PricingMethod.longstaff_schwartz,
            PricingMethod.all,
        }
    if method not in valid:
        raise ValueError(f"Method '{method.value}' is not valid for style '{style.value}'")


def _build_models(style: OptionStyle, method: PricingMethod, mc_paths: int) -> list[tuple[str, PricingModel]]:
    if style == OptionStyle.european:
        models: list[tuple[str, PricingModel]] = [
            ("black_scholes", BlackScholes()),
            ("monte_carlo", MonteCarlo(n_paths=mc_paths)),
            ("binomial_tree", BinomialTree(steps=200, american=False)),
        ]
    else:
        models = [
            ("baw", BaroneAdesiWhaley()),
            ("binomial_tree", BinomialTree(steps=200, american=True)),
            ("longstaff_schwartz", LongstaffSchwartz(n_paths=mc_paths)),
        ]

    if method == PricingMethod.all:
        return models
    wanted = method.value
    return [item for item in models if item[0] == wanted]


@router.post("/price", response_model=PriceResponse)
def price_option(payload: PriceRequest) -> PriceResponse | JSONResponse:
    try:
        _validate_style_method(payload.style, payload.method)

        ticker: str | None = None
        data_source = "user_provided"
        updated_at: str | None = None
        stale = False

        if payload.ticker is not None:
            ticker = payload.ticker.strip().upper()
            live = get_latest_live_price(ticker)
            if live is not None:
                data_source = "database"
                S = float(payload.S) if payload.S is not None else float(live["spot_price"])
                q = float(payload.q) if payload.q is not None else float(live["dividend_yield"])

                rate_stale = False
                if payload.r is None:
                    rate = get_latest_risk_free_rate()
                    if rate is None:
                        return _error(422, "Risk-free rate not in DB; please provide r manually")
                    r = float(rate["rate"])
                    rate_stale = _rate_is_stale(rate)
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
            else:
                missing = [
                    name
                    for name, value in (
                        ("S", payload.S),
                        ("r", payload.r),
                        ("q", payload.q),
                        ("sigma", payload.sigma),
                    )
                    if value is None
                ]
                if missing:
                    return _error(422, "Custom stock requires S, r, q, sigma")
                S = float(payload.S)
                r = float(payload.r)
                q = float(payload.q)
                sigma = float(payload.sigma)
                sigma_source = "user_provided"
                sigma_fallback = False
                ticker = payload.ticker.strip().upper()
        else:
            S = float(payload.S)
            r = float(payload.r)
            q = float(payload.q)
            sigma = float(payload.sigma)
            sigma_source = "user_provided"
            sigma_fallback = False

        params = OptionParams(
            S=S,
            K=float(payload.K),
            T=float(payload.T),
            r=r,
            sigma=sigma,
            option_type=payload.option_type.value,
            q=q,
        )

        model_outputs: dict[str, PriceModelOutput] = {}
        for key, model in _build_models(payload.style, payload.method, payload.mc_paths):
            price = float(model.price(params).price)
            if key == "black_scholes":
                g = AnalyticalGreeks().compute(params)
            else:
                g = NumericalGreeks(model).compute(params)
            model_outputs[key] = PriceModelOutput(
                price=price,
                greeks=GreekValues(
                    delta=float(g.delta),
                    gamma=float(g.gamma),
                    vega=float(g.vega),
                    theta=float(g.theta),
                    rho=float(g.rho),
                ),
            )

        return PriceResponse(
            ticker=ticker,
            option_type=payload.option_type,
            style=payload.style,
            method=payload.method,
            S=S,
            K=float(payload.K),
            T=float(payload.T),
            r=r,
            q=q,
            sigma=sigma,
            sigma_source=sigma_source,
            sigma_fallback=sigma_fallback,
            prices=model_outputs,
            data_source=data_source,
            updated_at=updated_at,
            stale=stale,
        )
    except InsufficientDataError as exc:
        return _error(422, f"{exc} Please provide sigma manually.")
    except ValueError as exc:
        return _error(422, str(exc))
    except Exception as exc:
        return _error(500, "Pricing failed", str(exc))
