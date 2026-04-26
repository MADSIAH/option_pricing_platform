from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from .base import OptionParams, PricingModel
from .utils import d1, d2


@dataclass
class Greeks:
    delta: float   # dV/dS
    gamma: float   # d²V/dS²
    vega: float    # dV/dσ per 1% move in σ
    theta: float   # dV/dt per calendar day (usually negative)
    rho: float     # dV/dr per 1% move in r
    method: str


class AnalyticalGreeks:
    """Closed-form Black-Scholes Greeks (Lecture 9, Mancini USI)."""

    def compute(self, params: OptionParams) -> Greeks:
        p = params
        _d1 = d1(p.S, p.K, p.T, p.r, p.sigma)
        _d2 = d2(p.S, p.K, p.T, p.r, p.sigma)
        pdf_d1 = norm.pdf(_d1)
        sqrt_T = np.sqrt(p.T)
        discount = np.exp(-p.r * p.T)

        # Gamma and Vega are identical for calls and puts
        gamma = pdf_d1 / (p.S * p.sigma * sqrt_T)
        vega = p.S * pdf_d1 * sqrt_T / 100  # per 1% change in sigma

        if p.option_type == "call":
            delta = norm.cdf(_d1)
            # Theta: ∂c/∂t = -S·N'(d1)·σ/(2√T) - r·K·e^(-rT)·N(d2), per calendar day
            theta = (-(p.S * pdf_d1 * p.sigma) / (2 * sqrt_T) - p.r * p.K * discount * norm.cdf(_d2)) / 365
            rho = p.K * p.T * discount * norm.cdf(_d2) / 100
        else:
            delta = norm.cdf(_d1) - 1
            theta = (-(p.S * pdf_d1 * p.sigma) / (2 * sqrt_T) + p.r * p.K * discount * norm.cdf(-_d2)) / 365
            rho = -p.K * p.T * discount * norm.cdf(-_d2) / 100

        return Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho, method="analytical")


class NumericalGreeks:
    """Central-difference Greeks for any PricingModel (MC, Binomial Tree).

    Bump sizes follow the design spec:
      h_S     = 0.01 * S   (Delta, Gamma)
      h_sigma = 0.001      (Vega)
      h_r     = 0.001      (Rho)
      h_T     = 0.001      (Theta)
    """

    def __init__(self, model: PricingModel):
        self._model = model

    def compute(self, params: OptionParams) -> Greeks:
        p = params
        price0 = self._model.price(p).price

        # --- Delta: central difference in S ---
        h_S = 0.01 * p.S
        p_S_up = OptionParams(p.S + h_S, p.K, p.T, p.r, p.sigma, p.option_type)
        p_S_dn = OptionParams(p.S - h_S, p.K, p.T, p.r, p.sigma, p.option_type)
        delta = (self._model.price(p_S_up).price - self._model.price(p_S_dn).price) / (2 * h_S)

        # --- Gamma: second derivative in S ---
        gamma = (self._model.price(p_S_up).price - 2 * price0 + self._model.price(p_S_dn).price) / (h_S ** 2)

        # --- Vega: central difference in sigma (per 1%) ---
        h_sig = 0.001
        p_sig_up = OptionParams(p.S, p.K, p.T, p.r, p.sigma + h_sig, p.option_type)
        p_sig_dn = OptionParams(p.S, p.K, p.T, p.r, p.sigma - h_sig, p.option_type)
        vega = (self._model.price(p_sig_up).price - self._model.price(p_sig_dn).price) / (2 * h_sig) / 100

        # --- Theta: central difference in T, sign-flipped for calendar time, per day ---
        h_T = 0.001
        if p.T > h_T:
            p_T_up = OptionParams(p.S, p.K, p.T + h_T, p.r, p.sigma, p.option_type)
            p_T_dn = OptionParams(p.S, p.K, p.T - h_T, p.r, p.sigma, p.option_type)
            # dV/dt = -dV/dT; divide annual rate by 365 for per-day
            theta = (self._model.price(p_T_dn).price - self._model.price(p_T_up).price) / (2 * h_T) / 365
        else:
            theta = 0.0

        # --- Rho: central difference in r (per 1%) ---
        h_r = 0.001
        p_r_up = OptionParams(p.S, p.K, p.T, p.r + h_r, p.sigma, p.option_type)
        p_r_dn = OptionParams(p.S, p.K, p.T, p.r - h_r, p.sigma, p.option_type)
        rho = (self._model.price(p_r_up).price - self._model.price(p_r_dn).price) / (2 * h_r) / 100

        return Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho, method="numerical")
