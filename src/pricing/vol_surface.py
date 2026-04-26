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
) -> float:
    """Implied volatility via Brent's root-finding on the Black-Scholes price.

    Search bracket: [1e-6, 10.0]. Raises ValueError if Brent's method fails.
    """
    def objective(sigma: float) -> float:
        params = OptionParams(S=S, K=K, T=T, r=r, sigma=sigma, option_type=option_type)
        return _bs.price(params).price - market_price

    try:
        return brentq(objective, 1e-6, 10.0, xtol=1e-6)
    except ValueError as e:
        raise ValueError(
            f"Implied vol not found for market_price={market_price:.4f}, "
            f"S={S}, K={K}, T={T:.4f}, r={r}, type={option_type}. "
            f"Check that the price is arbitrage-free and within the bracket. ({e})"
        ) from e


def build_vol_surface(
    option_chain: pd.DataFrame,
    S: float,
    r: float,
    option_type: str = "call",
) -> pd.DataFrame:
    """Build an implied volatility surface from a yfinance-style option chain.

    Parameters
    ----------
    option_chain : DataFrame with columns:
        - 'expiry'    : expiry label (string or date)
        - 'strike'    : strike price (float)
        - 'mid_price' : (bid + ask) / 2 (float)
        - 'T'         : time to expiry in years (float)
        Rows with zero volume or zero open interest should be filtered before calling.
    S : current spot price
    r : risk-free rate (annualized decimal)
    option_type : "call" or "put"

    Returns
    -------
    DataFrame indexed by (expiry, strike) with column 'implied_vol'.
    NaN where Brent's method does not converge.
    """
    records = []
    for _, row in option_chain.iterrows():
        try:
            iv = implied_vol(row["mid_price"], S, row["strike"], row["T"], r, option_type)
        except ValueError:
            iv = np.nan
        records.append({"expiry": row["expiry"], "strike": row["strike"], "implied_vol": iv})

    df = pd.DataFrame(records).set_index(["expiry", "strike"])
    return df
