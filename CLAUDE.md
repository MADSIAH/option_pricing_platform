# Claude Code — Project Context

## What this project is

Educational option pricing platform for USI "Programming in Finance II" (Project 2.7).
Prices European options via Black-Scholes, Monte Carlo, and Binomial Tree; computes Greeks; constructs the implied volatility surface.

## Current state (as of 2026-04-22)

**Phase 1 complete.** The pricing engine is fully implemented and tested.

### Pricing engine (`src/pricing/`)

| File | Class | Status |
|------|-------|--------|
| `base.py` | `OptionParams`, `PricingResult`, `PricingModel` | Done |
| `utils.py` | `d1`, `d2` | Done |
| `black_scholes.py` | `BlackScholes` | Done — reference benchmark |
| `monte_carlo.py` | `MonteCarlo` | Done — TBD: dividend yields |
| `binomial_tree.py` | `BinomialTree` | Done — TBD: dividend yields |

All models implement `PricingModel` and accept `OptionParams`, returning `PricingResult`.

### Tests (`tests/`)

- `test_monte_carlo.py` — 7 tests, all passing
- `test_binomial_tree.py` — 7 tests, all passing

Run with: `python -m pytest tests/ -v`

### Skills (`.claude/skills/`)

- `option-pricing-methods.md` — invoke when implementing or extending any pricing model

### Notebook (`notebooks/pricing.ipynb`)

Fully rewritten — uses `src/pricing` throughout. Sections:

1. **Fetch Real Data** — live AAPL price, annualized volatility, risk-free rate (FRED TB3MS), option chain via yfinance
2. **Set Parameters** — S₀, K (2% OTM), T=0.5y, σ
3. **Pricing Engine Setup** — imports from `src/pricing`, creates `call_params` and `put_params`
4. **Black-Scholes** — prices call and put; plots price vs spot over ±30% range
5. **Monte Carlo** — prices call and put (50k paths); plots 40 simulated GBM paths; plots convergence vs path count
6. **Binomial Tree** — prices European call/put and American put (500 steps); plots CRR lattice (7 steps, illustrative); plots convergence vs step count; shows early exercise premium
7. **Method Comparison** — side-by-side table and grouped bar chart (call + put, all three methods)

### Design spec

`docs/superpowers/specs/2026-04-22-option-pricing-skills-design.md` — full design decisions and conventions.

## What's next

1.**Pricing** — add dividend yield modeling
2. **Greeks** — `src/pricing/greeks.py`: analytical BS Greeks (Delta, Gamma, Vega, Theta, Rho) + finite-difference fallback for MC/BT. Return all five as a dict.
3. **Volatility surface** — `src/pricing/vol_surface.py`: implied vol via `scipy.optimize.brentq` on the yfinance option chain; surface as a `pandas.DataFrame` indexed by `(expiry, strike)`.
4. **Skill file** — `.claude/skills/option-risk-analytics.md`: second skill from the design spec.
5. **Web frontend + API** — later phases, tech stack TBD.

## Conventions

- Parameter names: `S`, `K`, `T`, `r`, `sigma`, `option_type` — always use `OptionParams`, never raw floats across boundaries
- Libraries: `numpy` for vectorised computation, `scipy.stats.norm` for CDF/PDF, `scipy.optimize.brentq` for implied vol
- Validation: after any new pricing model, assert within 1% of Black-Scholes ATM (see skill file for exact check)
- Black-Scholes is the benchmark — do not modify it without re-running the validation baseline
