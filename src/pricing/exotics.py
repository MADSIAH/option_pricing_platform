"""Exotic option pricers — all use full GBM path simulation.

Supported types
---------------
AsianOption     arithmetic-average strike payoff (call or put)
BarrierOption   knock-out / knock-in, up / down (call or put)
LookbackOption  fixed-strike lookback (call on max, put on min)
DigitalOption   cash-or-nothing: pays $1 if in-the-money at expiry
"""

import numpy as np

from .base import OptionParams, PricingModel, PricingResult
from .path_simulator import GBMPathSimulator


# ---------------------------------------------------------------------------
# Asian option  (arithmetic average)
# ---------------------------------------------------------------------------

class AsianOption(PricingModel):
    """Arithmetic-average Asian option priced via Monte Carlo.

    The payoff uses the average of *all monitored prices* (excluding S_0):
        call: max(avg(S) - K, 0)
        put:  max(K - avg(S), 0)

    Asian options are always cheaper than vanilla options with the same
    parameters because averaging reduces effective volatility.
    """

    def __init__(self, n_paths: int = 50_000, n_steps: int = 252, seed: int = 42):
        self._sim = GBMPathSimulator(n_paths=n_paths, n_steps=n_steps, seed=seed)

    def price(self, params: OptionParams) -> PricingResult:
        paths = self._sim.simulate(params)          # (n_paths, n_steps+1)
        avg = paths[:, 1:].mean(axis=1)             # arithmetic mean, exclude S0

        if params.option_type == "call":
            payoffs = np.maximum(avg - params.K, 0.0)
        else:
            payoffs = np.maximum(params.K - avg, 0.0)

        value = float(np.exp(-params.r * params.T) * payoffs.mean())
        return PricingResult(price=value, method="asian-mc", option_type=params.option_type)


# ---------------------------------------------------------------------------
# Barrier option
# ---------------------------------------------------------------------------

class BarrierOption(PricingModel):
    """Barrier option priced via Monte Carlo with discrete path monitoring.

    Parameters
    ----------
    barrier : float
        Barrier level H.
    barrier_type : str
        One of: "up-and-out", "up-and-in", "down-and-out", "down-and-in".
    rebate : float
        Cash paid immediately when a knock-out barrier is hit (default 0).

    Parity
    ------
    knock-out + knock-in = vanilla European (same strike, same expiry).
    """

    VALID_TYPES = {"up-and-out", "up-and-in", "down-and-out", "down-and-in"}

    def __init__(
        self,
        barrier: float,
        barrier_type: str = "up-and-out",
        rebate: float = 0.0,
        n_paths: int = 50_000,
        n_steps: int = 252,
        seed: int = 42,
    ):
        if barrier_type not in self.VALID_TYPES:
            raise ValueError(f"barrier_type must be one of {self.VALID_TYPES}")
        if barrier <= 0:
            raise ValueError("barrier must be positive")
        self.barrier = barrier
        self.barrier_type = barrier_type
        self.rebate = rebate
        self._sim = GBMPathSimulator(n_paths=n_paths, n_steps=n_steps, seed=seed)

    def price(self, params: OptionParams) -> PricingResult:
        paths = self._sim.simulate(params)          # (n_paths, n_steps+1)
        monitoring = paths[:, 1:]                   # exclude S0 from barrier check

        # --- barrier crossing ---
        if self.barrier_type.startswith("up"):
            crossed = monitoring.max(axis=1) >= self.barrier
        else:
            crossed = monitoring.min(axis=1) <= self.barrier

        # --- vanilla payoff on terminal price ---
        terminal = paths[:, -1]
        if params.option_type == "call":
            vanilla_payoff = np.maximum(terminal - params.K, 0.0)
        else:
            vanilla_payoff = np.maximum(params.K - terminal, 0.0)

        # --- apply barrier condition ---
        if self.barrier_type.endswith("out"):
            payoffs = np.where(crossed, self.rebate, vanilla_payoff)
        else:  # knock-in: only alive if barrier was hit
            payoffs = np.where(crossed, vanilla_payoff, self.rebate)

        value = float(np.exp(-params.r * params.T) * payoffs.mean())
        return PricingResult(price=value, method=f"barrier-{self.barrier_type}-mc", option_type=params.option_type)


# ---------------------------------------------------------------------------
# Lookback option  (fixed strike)
# ---------------------------------------------------------------------------

class LookbackOption(PricingModel):
    """Fixed-strike lookback option priced via Monte Carlo.

    Payoff
    ------
    call: max(max(S_t) - K, 0)   — right to buy at the historical low
    put:  max(K - min(S_t), 0)   — right to sell at the historical high

    Lookbacks are always worth at least as much as the corresponding vanilla
    because the holder effectively exercises at the best price over the period.
    """

    def __init__(self, n_paths: int = 50_000, n_steps: int = 252, seed: int = 42):
        self._sim = GBMPathSimulator(n_paths=n_paths, n_steps=n_steps, seed=seed)

    def price(self, params: OptionParams) -> PricingResult:
        paths = self._sim.simulate(params)
        monitoring = paths[:, 1:]                   # exclude S0

        if params.option_type == "call":
            extreme = monitoring.max(axis=1)
            payoffs = np.maximum(extreme - params.K, 0.0)
        else:
            extreme = monitoring.min(axis=1)
            payoffs = np.maximum(params.K - extreme, 0.0)

        value = float(np.exp(-params.r * params.T) * payoffs.mean())
        return PricingResult(price=value, method="lookback-mc", option_type=params.option_type)


# ---------------------------------------------------------------------------
# Digital option  (cash-or-nothing)
# ---------------------------------------------------------------------------

class DigitalOption(PricingModel):
    """Cash-or-nothing digital option priced via Monte Carlo.

    Pays $1 at expiry if in-the-money, $0 otherwise.
        call: pays 1 if S_T > K
        put:  pays 1 if S_T < K

    The analytical Black-Scholes price is exp(-rT) * N(±d2), which can be
    used to validate the MC result.
    """

    def __init__(self, n_paths: int = 50_000, seed: int = 42):
        # Digital only needs terminal price — use 1 step for efficiency
        self._sim = GBMPathSimulator(n_paths=n_paths, n_steps=1, seed=seed)

    def price(self, params: OptionParams) -> PricingResult:
        paths = self._sim.simulate(params)
        terminal = paths[:, -1]

        if params.option_type == "call":
            payoffs = (terminal > params.K).astype(float)
        else:
            payoffs = (terminal < params.K).astype(float)

        value = float(np.exp(-params.r * params.T) * payoffs.mean())
        return PricingResult(price=value, method="digital-mc", option_type=params.option_type)
