"""Pydantic schemas for Spec C API endpoints."""

from __future__ import annotations

from enum import Enum

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class OptionType(str, Enum):
    call = "call"
    put = "put"


class OptionStyle(str, Enum):
    european = "european"
    american = "american"


class PricingMethod(str, Enum):
    black_scholes = "black_scholes"
    monte_carlo = "monte_carlo"
    binomial_tree = "binomial_tree"
    baw = "baw"
    longstaff_schwartz = "longstaff_schwartz"
    all = "all"


class SigmaType(str, Enum):
    historical = "historical"
    implied = "implied"


class VaryBy(str, Enum):
    S = "S"
    T = "T"


class OptionChainType(str, Enum):
    call = "call"
    put = "put"
    both = "both"


class HealthResponse(BaseModel):
    status: str
    db_reachable: bool


class MarketResponse(BaseModel):
    ticker: str
    spot_price: float
    historical_vol: float | None
    historical_vol_warning: str | None = None
    atm_implied_vol: float | None
    risk_free_rate: float | None
    risk_free_rate_warning: str | None = None
    dividend_yield: float
    updated_at: str
    stale: bool
    data_source: str = "database"


class VolSurfacePoint(BaseModel):
    expiry: str
    T: float
    strike: float
    implied_vol: float


class VolSurfaceGrid(BaseModel):
    T_values: list[float]
    K_values: list[float]
    z: list[list[float | None]]  # z[K_idx][T_idx] — IV in %


class VolSurfaceResponse(BaseModel):
    ticker: str
    points: list[VolSurfacePoint]
    grid: VolSurfaceGrid | None = None
    updated_at: str
    stale: bool
    data_source: str = "database"


class OptionChainRow(BaseModel):
    expiry: str
    strike: float
    option_type: OptionType
    bid: float
    ask: float
    mid_price: float
    volume: int
    open_interest: int
    implied_vol: float
    T: float
    fetched_at: str


class OptionChainResponse(BaseModel):
    ticker: str
    option_type: OptionChainType
    rows: list[OptionChainRow]
    updated_at: str
    stale: bool
    data_source: str = "database"


class PriceRequest(BaseModel):
    ticker: str | None = None
    S: float | None = None
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float | None = None
    q: float | None = None
    sigma: float | None = Field(default=None, gt=0)
    sigma_type: SigmaType = SigmaType.historical
    option_type: OptionType
    style: OptionStyle
    method: PricingMethod = PricingMethod.all
    mc_paths: int = Field(default=50_000, gt=0, le=100_000)

    @model_validator(mode="after")
    def validate_custom_stock_requirements(self) -> "PriceRequest":
        if self.ticker is None:
            missing = [
                name
                for name, value in (
                    ("S", self.S),
                    ("r", self.r),
                    ("q", self.q),
                    ("sigma", self.sigma),
                )
                if value is None
            ]
            if missing:
                raise ValueError("Custom stock requires S, r, q, sigma")
        return self


class PriceSurfaceRequest(BaseModel):
    ticker: str
    option_type: OptionType
    style: OptionStyle
    sigma: float | None = Field(default=None, gt=0)
    sigma_type: SigmaType = SigmaType.historical
    S: float | None = Field(default=None, gt=0)
    r: float | None = None
    q: float | None = Field(default=None, ge=0)
    K_min_frac: float = Field(default=0.75, gt=0, le=1.0)
    K_max_frac: float = Field(default=1.25, ge=1.0, le=2.0)
    n_K: int = Field(default=60, ge=10, le=100)
    n_T: int = Field(default=45, ge=10, le=80)


class GreeksProfileRequest(BaseModel):
    ticker: str | None = None
    S: float | None = Field(default=None, gt=0)
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float | None = None
    q: float | None = Field(default=None, ge=0)
    sigma: float | None = Field(default=None, gt=0)
    sigma_type: SigmaType = SigmaType.historical
    option_type: OptionType
    vary_by: VaryBy
    range_min: float
    range_max: float
    steps: int = Field(default=50, ge=2, le=500)

    @model_validator(mode="after")
    def validate_ranges_and_custom_stock(self) -> "GreeksProfileRequest":
        if self.range_max <= self.range_min:
            raise ValueError("range_max must be greater than range_min")

        if self.vary_by == VaryBy.S and self.range_min <= 0:
            raise ValueError("S range_min must be positive")
        if self.vary_by == VaryBy.T and self.range_min <= 0:
            raise ValueError("T range_min must be positive")

        if self.ticker is None:
            missing = [
                name
                for name, value in (
                    ("S", self.S),
                    ("r", self.r),
                    ("q", self.q),
                    ("sigma", self.sigma),
                )
                if value is None
            ]
            if missing:
                raise ValueError("Custom stock requires S, r, q, sigma")
        return self


class GreekValues(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class PriceModelOutput(BaseModel):
    price: float
    greeks: GreekValues


class PriceResponse(BaseModel):
    ticker: str | None = None
    option_type: OptionType
    style: OptionStyle
    method: PricingMethod
    S: float
    K: float
    T: float
    r: float
    q: float
    sigma: float
    sigma_source: str
    sigma_fallback: bool = False
    prices: dict[str, PriceModelOutput]
    data_source: str
    updated_at: str | None = None
    stale: bool = False


class MarketPricePoint(BaseModel):
    K: float
    T: float
    mid_price: float
    volume: int = 0
    open_interest: int = 0


class PriceSurfaceResponse(BaseModel):
    ticker: str
    option_type: OptionType
    style: OptionStyle
    S_ref: float
    sigma: float
    sigma_source: str
    sigma_fallback: bool = False
    K_values: list[float]
    T_values: list[float]
    z: list[list[float]]  # z[T_idx][K_idx]
    market_points: list[MarketPricePoint]
    data_source: str
    updated_at: str
    stale: bool


class BucketMetrics(BaseModel):
    t_label: str
    m_label: str
    spike_count: int
    mean_signed_div: float | None
    mean_abs_div: float | None
    pct_large_div: float | None
    count_large_div: int
    volume: int
    open_interest: int


class SurfaceExplainRequest(BaseModel):
    user_level: UserLevel
    ticker: str
    option_type: OptionType
    smile_intensity: float
    put_skew: float
    deep_itm_bias: float | None
    divergence_threshold: float
    buckets: list[BucketMetrics]


class SurfaceExplainResponse(BaseModel):
    explanation: str


class GreeksProfilePoint(BaseModel):
    x: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class GreeksProfileResponse(BaseModel):
    ticker: str | None = None
    option_type: OptionType
    vary_by: VaryBy
    K: float
    S: float
    T: float
    r: float
    q: float
    sigma: float
    sigma_source: str
    sigma_fallback: bool = False
    points: list[GreeksProfilePoint]
    data_source: str
    updated_at: str | None = None
    stale: bool = False


# ── AI feature schemas ─────────────────────────────────────────────────────


class UserLevel(str, Enum):
    beginner = "beginner"
    finance_student = "finance_student"
    professional = "professional"


class ExplainRequest(BaseModel):
    user_level: UserLevel
    option_type: OptionType
    style: OptionStyle
    method: PricingMethod
    S: float = Field(..., gt=0)
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float
    sigma: float = Field(..., gt=0)
    q: float = Field(..., ge=0)
    prices: dict[str, PriceModelOutput]


class ExplainResponse(BaseModel):
    explanation: str


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    user_level: UserLevel
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
