---
name: option-pricing-methods
description: Use when implementing or extending any option pricing model (Black-Scholes, Monte Carlo, Binomial Tree). Enforces parameter conventions, module structure, library usage, and cross-validation rules.
type: implementation
---

# Option Pricing Methods

## When to invoke
Implementing a new pricing model, modifying an existing one, or adding pricing logic anywhere in `src/pricing/`.

## Module structure

```
src/pricing/
├── base.py          # OptionParams, PricingResult, PricingModel ABC
├── utils.py         # Shared d1/d2 calculations
├── black_scholes.py # Reference implementation — benchmark for all other methods
├── monte_carlo.py   # (next)
└── binomial_tree.py # (next)
```

Every pricing model is a class that:
- Inherits from `PricingModel`
- Accepts an `OptionParams` instance
- Returns a `PricingResult`

Do not add pricing logic outside this module.

## Parameter conventions

Always use `OptionParams` — never pass raw floats individually across model boundaries.

| Field | Type | Unit |
|-------|------|------|
| `S` | float | Spot price |
| `K` | float | Strike price |
| `T` | float | Years to expiry |
| `r` | float | Annualized risk-free rate (decimal, e.g. 0.036) |
| `sigma` | float | Annualized volatility (decimal, e.g. 0.23) |
| `option_type` | str | `"call"` or `"put"` |

`OptionParams.__post_init__` validates all fields — do not duplicate that validation in model classes.

## Library rules

- `numpy` for all vectorized computation (paths, arrays, discounting)
- `scipy.stats.norm` for CDF and PDF — never use `math.erf` manually
- `scipy.optimize.brentq` for implied volatility (see `option-risk-analytics` skill)

## Black-Scholes (reference implementation)

`BlackScholes` in `src/pricing/black_scholes.py` is the closed-form benchmark.

- Uses shared `d1`/`d2` from `utils.py` — do not recompute inline
- Must not be modified without re-running the validation baseline
- All other models must produce results consistent with BS where a closed form exists

## Adding a new pricing model

1. Create `src/pricing/<method>.py`
2. Define a class inheriting `PricingModel`
3. Implement `price(self, params: OptionParams) -> PricingResult`
4. Set `PricingResult.method` to a unique lowercase string (e.g. `"monte-carlo"`)
5. Export from `src/pricing/__init__.py`
6. Run validation (see below)

## Monte Carlo conventions (when implementing)

- GBM under risk-neutral measure: `S * exp((r - 0.5*sigma²)*T + sigma*sqrt(T)*Z)`
- Minimum 10,000 paths
- Antithetic variates required: generate N/2 standard normals, use both `Z` and `-Z`
- Fix seed: `np.random.default_rng(seed=42)` — pass seed as constructor arg with default 42
- Discount: `exp(-r * T) * mean(payoffs)`

## Binomial Tree conventions (when implementing)

- CRR parameterisation: `u = exp(sigma * sqrt(dt))`, `d = 1 / u`
- Risk-neutral probability: `p = (exp(r * dt) - d) / (u - d)`
- Backward induction from terminal payoffs
- American exercise: accept `american: bool = False` in constructor; apply `max(intrinsic, continuation)` at each node when `True`

## Validation rule

After implementing any numerical method, assert convergence against Black-Scholes:

```python
from src.pricing import BlackScholes, OptionParams

BASELINE = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
bs_price = BlackScholes().price(BASELINE).price

new_price = YourModel().price(BASELINE).price
assert abs(new_price - bs_price) / bs_price < 0.01, (
    f"{new_price:.4f} deviates from BS benchmark {bs_price:.4f} by more than 1%"
)
```

Run this check before committing any new pricing model.
