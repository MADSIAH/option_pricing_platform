"""Heston stochastic volatility model — Monte Carlo pricer.

Model dynamics (risk-neutral measure)
--------------------------------------
dS_t = (r - q) S_t dt + sqrt(v_t) S_t dW_S
dv_t = kappa (theta - v_t) dt + xi sqrt(v_t) dW_v
d<W_S, W_v> = rho dt

Parameters
----------
v0    : initial variance  (sigma_0 = sqrt(v0))
kappa : mean-reversion speed of variance
theta : long-run (steady-state) variance
xi    : volatility of variance ("vol of vol")
rho   : instantaneous correlation between S and v shocks

Key property
------------
When xi → 0 and v_0 = theta = sigma^2, Heston collapses to Black-Scholes.
Non-zero xi generates a volatility smile / skew absent in Black-Scholes.

Feller condition
----------------
2 * kappa * theta >= xi^2  ensures variance stays strictly positive a.s.
A warning is issued when the condition is violated; pricing still proceeds
using full truncation (max(v, 0)).

Discretisation
--------------
Euler-Maruyama with full truncation:
    v_{t+dt} = max(v_t, 0) + kappa*(theta - max(v_t,0))*dt + xi*sqrt(max(v_t,0))*dW_v
    log S_{t+dt} = log S_t + (r - q - 0.5*max(v_t,0))*dt + sqrt(max(v_t,0))*dW_S
Antithetic variates: second half of paths uses (-Z_S, -Z_v).
"""

import warnings
from dataclasses import dataclass, field

import numpy as np

from .base import PricingResult


@dataclass
class HestonParams:
    """Parameters for the Heston stochastic volatility model."""

    S: float          # spot price
    K: float          # strike price
    T: float          # time to expiry in years
    r: float          # risk-free rate (annualised decimal)
    v0: float         # initial variance  (not volatility — use sigma²)
    kappa: float      # mean-reversion speed
    theta: float      # long-run variance
    xi: float         # vol of vol
    rho: float        # correlation W_S ↔ W_v  ∈ (-1, 1)
    option_type: str  # "call" or "put"
    q: float = 0.0    # continuous dividend yield

    def __post_init__(self):
        if self.option_type not in ("call", "put"):
            raise ValueError('option_type must be "call" or "put".')
        if self.T <= 0:
            raise ValueError("T must be positive.")
        if self.S <= 0 or self.K <= 0:
            raise ValueError("S and K must be positive.")
        if self.v0 <= 0 or self.theta <= 0:
            raise ValueError("v0 and theta must be positive.")
        if self.kappa <= 0 or self.xi <= 0:
            raise ValueError("kappa and xi must be positive.")
        if not -1.0 < self.rho < 1.0:
            raise ValueError("rho must be strictly in (-1, 1).")


class HestonMC:
    """Monte Carlo pricer for the Heston stochastic volatility model.

    Parameters
    ----------
    n_paths : int
        Total number of paths (must be even; antithetic variates used).
    n_steps : int
        Number of time steps for discretisation (252 ≈ daily for T=1y).
    seed : int
        RNG seed for reproducibility.
    """

    def __init__(self, n_paths: int = 50_000, n_steps: int = 252, seed: int = 42):
        self.n_paths = n_paths
        self.n_steps = n_steps
        self.seed = seed

    def price(self, params: HestonParams) -> PricingResult:
        p = params

        # Feller condition check
        if 2 * p.kappa * p.theta < p.xi ** 2:
            warnings.warn(
                f"Feller condition violated (2κθ={2*p.kappa*p.theta:.4f} < ξ²={p.xi**2:.4f}). "
                "Variance may hit zero; full truncation applied.",
                UserWarning,
                stacklevel=2,
            )

        dt = p.T / self.n_steps
        sqrt_dt = np.sqrt(dt)
        half = self.n_paths // 2

        rng = np.random.default_rng(self.seed)
        Z1_half = rng.standard_normal((half, self.n_steps))   # drives S
        Z2_half = rng.standard_normal((half, self.n_steps))   # independent

        # antithetic: negate both to preserve correlation structure
        Z1 = np.concatenate([Z1_half, -Z1_half], axis=0)
        Z2 = np.concatenate([Z2_half, -Z2_half], axis=0)

        # correlated increments: dW_v = rho*dW_S + sqrt(1-rho²)*dW_perp
        dW_S = Z1 * sqrt_dt
        dW_v = (p.rho * Z1 + np.sqrt(1 - p.rho ** 2) * Z2) * sqrt_dt

        # initialise
        log_S = np.full(self.n_paths, np.log(p.S))
        v = np.full(self.n_paths, p.v0)

        # Euler-Maruyama with full truncation
        for i in range(self.n_steps):
            v_pos = np.maximum(v, 0.0)
            log_S += (p.r - p.q - 0.5 * v_pos) * dt + np.sqrt(v_pos) * dW_S[:, i]
            v = v_pos + p.kappa * (p.theta - v_pos) * dt + p.xi * np.sqrt(v_pos) * dW_v[:, i]

        S_T = np.exp(log_S)

        if p.option_type == "call":
            payoffs = np.maximum(S_T - p.K, 0.0)
        else:
            payoffs = np.maximum(p.K - S_T, 0.0)

        value = float(np.exp(-p.r * p.T) * payoffs.mean())
        return PricingResult(price=value, method="heston-mc", option_type=p.option_type)
