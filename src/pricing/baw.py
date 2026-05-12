import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from .base import OptionParams, PricingModel, PricingResult
from .black_scholes import BlackScholes
from .utils import d1


def _baw_params(r: float, sigma: float, T: float, q: float) -> tuple[float, float]:
    """Quadratic approximation coefficients q1 (put) and q2 (call)."""
    M = 2.0 * r / sigma**2
    N = 2.0 * (r - q) / sigma**2
    k = 1.0 - np.exp(-r * T)
    disc = np.sqrt((N - 1.0)**2 + 4.0 * M / k)
    return ((N - 1.0) - disc) / 2.0, ((N - 1.0) + disc) / 2.0  # q1, q2


def _critical_call(K: float, T: float, r: float, sigma: float, q: float, q2: float) -> float:
    """Critical stock price S* above which immediate exercise dominates for a call."""
    bs = BlackScholes()
    eq = np.exp(-q * T)

    def f(S: float) -> float:
        c = bs.price(OptionParams(S=S, K=K, T=T, r=r, sigma=sigma, option_type="call", q=q)).price
        return S - K - c - (S / q2) * (1.0 - eq * norm.cdf(d1(S, K, T, r, sigma, q)))

    upper = 2.0 * K
    while f(upper) < 0.0:
        upper *= 2.0
    return brentq(f, K + 1e-8, upper, xtol=1e-8, rtol=1e-8)


def _critical_put(K: float, T: float, r: float, sigma: float, q: float, q1: float) -> float:
    """Critical stock price S** below which immediate exercise dominates for a put."""
    bs = BlackScholes()
    eq = np.exp(-q * T)

    def f(S: float) -> float:
        p = bs.price(OptionParams(S=S, K=K, T=T, r=r, sigma=sigma, option_type="put", q=q)).price
        return K - S - p + (S / q1) * (1.0 - eq * norm.cdf(-d1(S, K, T, r, sigma, q)))

    return brentq(f, 1e-8, K - 1e-8, xtol=1e-8, rtol=1e-8)


class BaroneAdesiWhaley(PricingModel):
    """
    Barone-Adesi and Whaley (1987) quadratic approximation for American options.

    For calls with q=0 early exercise is never optimal; returns the European price exactly.
    """

    def price(self, params: OptionParams) -> PricingResult:
        p = params
        bs = BlackScholes()
        european = bs.price(p).price
        q1, q2 = _baw_params(p.r, p.sigma, p.T, p.q)
        eq = np.exp(-p.q * p.T)

        if p.option_type == "call":
            if p.q == 0.0:
                value = european
            else:
                S_star = _critical_call(p.K, p.T, p.r, p.sigma, p.q, q2)
                if p.S >= S_star:
                    value = p.S - p.K
                else:
                    A2 = (S_star / q2) * (1.0 - eq * norm.cdf(d1(S_star, p.K, p.T, p.r, p.sigma, p.q)))
                    value = european + A2 * (p.S / S_star) ** q2
        else:
            S_dstar = _critical_put(p.K, p.T, p.r, p.sigma, p.q, q1)
            if p.S <= S_dstar:
                value = p.K - p.S
            else:
                A1 = -(S_dstar / q1) * (1.0 - eq * norm.cdf(-d1(S_dstar, p.K, p.T, p.r, p.sigma, p.q)))
                value = european + A1 * (p.S / S_dstar) ** q1

        return PricingResult(price=float(value), method="baw", option_type=p.option_type)
