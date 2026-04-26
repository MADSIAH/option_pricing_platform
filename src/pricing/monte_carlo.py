import numpy as np

from .base import OptionParams, PricingModel, PricingResult


class MonteCarlo(PricingModel):
    def __init__(self, n_paths: int = 10_000, seed: int = 42):
        self._n_paths = n_paths
        self._seed = seed

    def price(self, params: OptionParams) -> PricingResult:
        p = params
        rng = np.random.default_rng(self._seed)

        half = self._n_paths // 2
        z = rng.standard_normal(half)
        z = np.concatenate([z, -z])  # antithetic variates

        terminal = p.S * np.exp((p.r - p.q - 0.5 * p.sigma**2) * p.T + p.sigma * np.sqrt(p.T) * z)

        if p.option_type == "call":
            payoffs = np.maximum(terminal - p.K, 0)
        else:
            payoffs = np.maximum(p.K - terminal, 0)

        value = np.exp(-p.r * p.T) * payoffs.mean()
        return PricingResult(price=float(value), method="monte-carlo", option_type=p.option_type)
