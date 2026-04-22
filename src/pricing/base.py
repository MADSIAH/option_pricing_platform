from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OptionParams:
    S: float       # spot price
    K: float       # strike price
    T: float       # time to expiry in years
    r: float       # risk-free rate (annualized decimal)
    sigma: float   # volatility (annualized decimal)
    option_type: str  # "call" or "put"

    def __post_init__(self):
        if self.option_type not in ("call", "put"):
            raise ValueError('option_type must be "call" or "put".')
        if self.T <= 0:
            raise ValueError("T must be positive.")
        if self.sigma <= 0:
            raise ValueError("sigma must be positive.")
        if self.S <= 0 or self.K <= 0:
            raise ValueError("S and K must be positive.")


@dataclass
class PricingResult:
    price: float
    method: str
    option_type: str


class PricingModel(ABC):
    @abstractmethod
    def price(self, params: OptionParams) -> PricingResult:
        ...
