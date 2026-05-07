# Dividend Yield Modeling — Design Spec

**Date:** 2026-04-26
**Project:** Option Pricing Platform (USI Programming in Finance II, Project 2.7)
**Scope:** Add continuous dividend yield `q` across all pricing models, Greeks, and implied vol

---

## Approach

Continuous dividend yield (Merton 1973). Add `q: float = 0.0` to `OptionParams`. Default zero means all 43 existing tests pass unchanged. Discrete dividends and the escrowed model were considered and rejected as over-engineered for an educational platform.

---

## Section 1: Data Layer

### `src/pricing/base.py`

Add to `OptionParams`:
```python
q: float = 0.0   # continuous dividend yield (annualized decimal, e.g. 0.02)
```
Validation in `__post_init__`: `if self.q < 0: raise ValueError("q must be non-negative.")`

### `src/pricing/utils.py`

Update `d1` and `d2` signatures to accept `q: float = 0.0`:
```
d1 = (log(S/K) + (r - q + 0.5·σ²)·T) / (σ·√T)
d2 = d1 − σ·√T
```
All callers pass `q` explicitly.

---

## Section 2: Pricing Models

### `src/pricing/black_scholes.py`

Pass `p.q` to `d1`/`d2`. Replace bare `p.S` with `p.S * exp(-p.q * p.T)`:
```
call = S·e^(-qT)·N(d1) − K·e^(-rT)·N(d2)
put  = K·e^(-rT)·N(−d2) − S·e^(-qT)·N(−d1)
```

### `src/pricing/monte_carlo.py`

Update GBM drift:
```python
terminal = S * exp((r - q - 0.5·σ²)·T + σ·√T · z)
```

### `src/pricing/binomial_tree.py`

Update risk-neutral probability (rename local `q` → `q_prob` to avoid shadowing `params.q`):
```python
q_prob = (exp((r - q) * dt) - d) / (u - d)
```

---

## Section 3: Greeks

### `src/pricing/greeks.py` — `AnalyticalGreeks`

Full Merton extension. Pass `p.q` to `d1`/`d2`. Updated formulas:

```
delta_call = exp(-qT) · N(d1)
delta_put  = exp(-qT) · (N(d1) − 1)

gamma      = exp(-qT) · N'(d1) / (S·σ·√T)

vega       = S · exp(-qT) · N'(d1) · √T / 100

theta_call = (−S·σ·exp(-qT)·N'(d1)/(2√T) − r·K·exp(-rT)·N(d2)  + q·S·exp(-qT)·N(d1))  / 365
theta_put  = (−S·σ·exp(-qT)·N'(d1)/(2√T) + r·K·exp(-rT)·N(−d2) − q·S·exp(-qT)·N(−d1)) / 365

rho_call   = K·T·exp(-rT)·N(d2)  / 100
rho_put    = −K·T·exp(-rT)·N(−d2) / 100
```

### `src/pricing/greeks.py` — `NumericalGreeks`

No changes. Inherits dividend support automatically via `OptionParams.q`.

---

## Section 4: Volatility Surface

### `src/pricing/vol_surface.py`

`implied_vol`: add `q: float = 0.0`, pass to `OptionParams` inside the objective.

`build_vol_surface`: add `q: float = 0.0`, forward to `implied_vol`.

DataFrame contract and return type unchanged.

---

## Section 5: Tests

No existing tests change. New tests added to existing test files:

| File | Test | Assertion |
|------|------|-----------|
| `test_monte_carlo.py` | `test_call_price_lower_with_dividend` | `price(q=0.03) < price(q=0)` for call |
| `test_binomial_tree.py` | `test_call_price_lower_with_dividend` | `price(q=0.03) < price(q=0)` for call |
| `test_greeks.py` | `test_delta_call_reduced_by_dividend` | `delta(q=0.03) < delta(q=0)` |
| `test_vol_surface.py` | `test_roundtrip_with_dividend` | implied vol roundtrip with `q=0.02`, tolerance `1e-5` |

---

## Decisions Log

| Decision | Choice | Reason |
|----------|--------|--------|
| Dividend model | Continuous yield `q` | Standard Merton extension; taught in finance courses; clean across all three models |
| Discrete dividends | Rejected | Requires dividend schedule, non-analytic in BS, messy in BT |
| Escrowed model | Rejected | Adds complexity without pedagogical benefit |
| Default value | `q = 0.0` | Full backward compatibility; all 43 existing tests pass unchanged |
| Local variable rename | `q_prob` in BT | Avoids shadowing `params.q` |
| Rho with dividends | Unchanged formula | Rho measures sensitivity to `r`, not `q`; formula is correct as-is |
| NumericalGreeks | No changes | Inherits `q` through `OptionParams` automatically |
