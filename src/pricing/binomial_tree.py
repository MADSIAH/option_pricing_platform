import numpy as np

from .base import OptionParams, PricingModel, PricingResult


class BinomialTree(PricingModel):
    def __init__(self, steps: int = 200, american: bool = False):
        self._steps = steps
        self._american = american

    def price(self, params: OptionParams) -> PricingResult:
        p = params
        n = self._steps
        dt = p.T / n

        u = np.exp(p.sigma * np.sqrt(dt))
        d = 1.0 / u
        q_prob = (np.exp((p.r - p.q) * dt) - d) / (u - d)  # risk-neutral probability
        discount = np.exp(-p.r * dt)

        # terminal stock prices
        j = np.arange(n + 1)
        terminal = p.S * (u ** (n - j)) * (d ** j)

        if p.option_type == "call":
            values = np.maximum(terminal - p.K, 0.0)
        else:
            values = np.maximum(p.K - terminal, 0.0)

        # backward induction
        for i in range(n - 1, -1, -1):
            values = discount * (q_prob * values[:-1] + (1 - q_prob) * values[1:])
            if self._american:
                stock = p.S * (u ** (i - np.arange(i + 1))) * (d ** np.arange(i + 1))
                if p.option_type == "call":
                    intrinsic = np.maximum(stock - p.K, 0.0)
                else:
                    intrinsic = np.maximum(p.K - stock, 0.0)
                values = np.maximum(values, intrinsic)

        return PricingResult(price=float(values[0]), method="binomial-tree", option_type=p.option_type)
