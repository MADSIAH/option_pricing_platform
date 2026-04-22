import numpy as np
from scipy.stats import norm

from .base import OptionParams, PricingModel, PricingResult
from .utils import d1, d2


class BlackScholes(PricingModel):
    def price(self, params: OptionParams) -> PricingResult:
        p = params
        _d1 = d1(p.S, p.K, p.T, p.r, p.sigma)
        _d2 = d2(p.S, p.K, p.T, p.r, p.sigma)
        discount = np.exp(-p.r * p.T)

        if p.option_type == "call":
            value = p.S * norm.cdf(_d1) - p.K * discount * norm.cdf(_d2)
        else:
            value = p.K * discount * norm.cdf(-_d2) - p.S * norm.cdf(-_d1)

        return PricingResult(price=value, method="black-scholes", option_type=p.option_type)
