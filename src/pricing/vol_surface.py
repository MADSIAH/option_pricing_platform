import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .base import OptionParams
from .black_scholes import BlackScholes

_bs = BlackScholes()


def implied_vol(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
    q: float = 0.0,
) -> float:
    """Implied volatility via Brent's root-finding on the Black-Scholes price.

    Search bracket: [1e-6, 10.0]. Raises ValueError if Brent's method fails.
    """
    def objective(sigma: float) -> float:
        params = OptionParams(S=S, K=K, T=T, r=r, sigma=sigma, option_type=option_type, q=q)
        return _bs.price(params).price - market_price

    try:
        return brentq(objective, 1e-6, 10.0, xtol=1e-6)
    except ValueError as e:
        raise ValueError(
            f"Implied vol not found for market_price={market_price:.4f}, "
            f"S={S}, K={K}, T={T:.4f}, r={r}, type={option_type}. "
            f"Check that the price is arbitrage-free and within the bracket. ({e})"
        ) from e


def clean_option_chain(
    option_chain: pd.DataFrame,
    S: float,
    min_days_to_expiry: float = 7.0,
    max_relative_spread: float = 0.35,
    moneyness_min: float = 0.7,
    moneyness_max: float = 1.3,
    min_volume: int = 1,
    min_open_interest: int = 1,
) -> pd.DataFrame:
    """
    Clean a yfinance-style option chain before implied-vol extraction.

    The function applies conservative market-quality filters to reduce
    volatility-surface spikes caused by illiquid contracts.
    """
    if S <= 0:
        raise ValueError("S must be positive.")
    if min_days_to_expiry < 0:
        raise ValueError("min_days_to_expiry must be non-negative.")
    if max_relative_spread <= 0:
        raise ValueError("max_relative_spread must be positive.")
    if moneyness_min <= 0 or moneyness_max <= 0 or moneyness_min >= moneyness_max:
        raise ValueError("moneyness range must satisfy 0 < moneyness_min < moneyness_max.")
    if min_volume < 0 or min_open_interest < 0:
        raise ValueError("min_volume and min_open_interest must be non-negative.")

    if "strike" not in option_chain.columns:
        raise ValueError("option_chain must include 'strike'.")
    if "T" not in option_chain.columns:
        raise ValueError("option_chain must include 'T' (time to expiry in years).")

    df = option_chain.copy()

    bid_col = "bid" if "bid" in df.columns else None
    ask_col = "ask" if "ask" in df.columns else None
    oi_col = "open_interest" if "open_interest" in df.columns else ("openInterest" if "openInterest" in df.columns else None)

    if "mid_price" not in df.columns:
        if bid_col is not None and ask_col is not None:
            df["mid_price"] = (df[bid_col] + df[ask_col]) / 2.0
        else:
            raise ValueError("option_chain must include 'mid_price' or both 'bid' and 'ask'.")

    df = df.dropna(subset=["strike", "T", "mid_price"])
    df = df[(df["strike"] > 0) & (df["T"] > 0) & (df["mid_price"] > 0)]

    min_T = min_days_to_expiry / 365.0
    df = df[df["T"] >= min_T]

    moneyness = df["strike"] / S
    df = df[(moneyness >= moneyness_min) & (moneyness <= moneyness_max)]

    if "volume" in df.columns:
        df = df[df["volume"].fillna(0) >= min_volume]
    if oi_col is not None:
        df = df[df[oi_col].fillna(0) >= min_open_interest]

    if bid_col is not None and ask_col is not None:
        df = df[df[bid_col].notna() & df[ask_col].notna()]
        df = df[(df[bid_col] > 0) & (df[ask_col] > 0) & (df[ask_col] >= df[bid_col])]
        rel_spread = (df[ask_col] - df[bid_col]) / df["mid_price"]
        df = df[rel_spread <= max_relative_spread]

    return df


def build_vol_surface(
    option_chain: pd.DataFrame,
    S: float,
    r: float,
    option_type: str = "call",
    q: float = 0.0,
    clean: bool = True,
    min_days_to_expiry: float = 7.0,
    max_relative_spread: float = 0.35,
    moneyness_min: float = 0.7,
    moneyness_max: float = 1.3,
    min_volume: int = 1,
    min_open_interest: int = 1,
) -> pd.DataFrame:
    """Build an implied volatility surface from a yfinance-style option chain.

    Parameters
    ----------
    option_chain : DataFrame with columns:
        - 'expiry'    : expiry label (string or date)
        - 'strike'    : strike price (float)
        - 'mid_price' : (bid + ask) / 2 (float)
        - 'T'         : time to expiry in years (float)
        If clean=True (default), filtering is handled internally.
    S : current spot price
    r : risk-free rate (annualized decimal)
    option_type : "call" or "put"

    clean : bool
        If True, apply chain-quality filters before implied-vol extraction.

    Returns
    -------
    DataFrame indexed by (expiry, strike) with column 'implied_vol'.
    NaN where Brent's method does not converge.
    """
    if "expiry" not in option_chain.columns:
        raise ValueError("option_chain must include 'expiry'.")

    chain = option_chain
    if clean:
        chain = clean_option_chain(
            option_chain=option_chain,
            S=S,
            min_days_to_expiry=min_days_to_expiry,
            max_relative_spread=max_relative_spread,
            moneyness_min=moneyness_min,
            moneyness_max=moneyness_max,
            min_volume=min_volume,
            min_open_interest=min_open_interest,
        )

    records = []
    for _, row in chain.iterrows():
        try:
            iv = implied_vol(row["mid_price"], S, row["strike"], row["T"], r, option_type, q)
        except ValueError:
            iv = np.nan
        records.append({"expiry": row["expiry"], "strike": row["strike"], "implied_vol": iv})

    df = pd.DataFrame(records).set_index(["expiry", "strike"])
    return df
