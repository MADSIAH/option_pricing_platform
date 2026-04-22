# Option Pricing Skills — Design Spec

**Date:** 2026-04-22
**Project:** Option Pricing Platform (USI Programming in Finance II, Project 2.7)
**Scope:** Two flat Markdown skill files to guide Claude when implementing pricing models and risk analytics

---

## Context

Phase 1 is complete. `src/pricing/` implements all three pricing models (Black-Scholes, Monte Carlo, Binomial Tree) with 14 passing tests. `notebooks/pricing.ipynb` has been rewritten to use the package and demonstrates each method with plots and a final comparison. Remaining roadmap items (Greeks, volatility surface) need consistent implementation conventions enforced through Claude Code skills.

Skills purpose: **implementation guide only** — correct formulas, numerical conventions, parameter naming, library usage, and validation rules. No theory explanation layer.

---

## File Layout

```
option_pricing_platform/
├── .claude/
│   └── skills/
│       ├── option-pricing-methods.md
│       └── option-risk-analytics.md
├── notebooks/
│   └── pricing.ipynb
└── README.md
```

---

## Skill 1 — `option-pricing-methods.md`

**Trigger:** Invoked when implementing or extending any of the three pricing models.

### Sections

1. **Trigger** — when to invoke
2. **Parameter conventions**
   - Canonical names: `S` (spot), `K` (strike), `T` (time to expiry in years), `r` (risk-free rate as decimal), `sigma` (annualized volatility), `option_type` (`"call"` | `"put"`)
   - No deviation from these names across all implementations
3. **Library rules**
   - Use `numpy` for all vectorized path computations
   - Use `scipy.stats.norm` for CDF/PDF throughout — never use `math.erf` manually
4. **Black-Scholes**
   - Reference implementation lives in `src/pricing/black_scholes.py`
   - Must not be modified without updating the validation baseline
   - Serves as the benchmark for all numerical methods
5. **Monte Carlo**
   - GBM path generation under risk-neutral measure
   - Minimum 10,000 paths
   - Antithetic variates required
   - Fixed `numpy` random seed for reproducibility
   - Discount payoff by `exp(-r * T)`
6. **Binomial Tree (CRR)**
   - Up factor: `u = exp(sigma * sqrt(dt))`; down factor: `d = 1 / u`
   - Risk-neutral probability: `p = (exp(r * dt) - d) / (u - d)`
   - Backward induction for option value
   - American exercise flag: apply `max(intrinsic, continuation)` at each node when enabled
7. **Validation rule**
   - After implementing any numerical method, run a convergence check against Black-Scholes at ATM with standard params (`T=0.5`, `sigma=0.2`, `r=0.05`)
   - Assert result within 1% tolerance of the BS benchmark

---

## Skill 2 — `option-risk-analytics.md`

**Trigger:** Invoked when implementing Greeks or the volatility surface.

### Sections

1. **Trigger** — when to invoke
2. **Greeks — analytical (Black-Scholes)**
   - Delta: `norm.cdf(d1)` (call), `norm.cdf(d1) - 1` (put)
   - Gamma: `norm.pdf(d1) / (S * sigma * sqrt(T))`
   - Vega: `S * norm.pdf(d1) * sqrt(T)` (expressed per 1% move: divide by 100)
   - Theta: full BS theta formula; convention is per calendar day (divide annual by 365)
   - Rho: `K * T * exp(-r * T) * norm.cdf(d2)` (call), negated for put
   - All five Greeks must be returned together as a dict or dataclass
3. **Greeks — finite difference fallback**
   - Use central differences only (no forward/backward)
   - Bump sizes: `h = 0.01 * S` for Delta and Gamma; `h = 0.001` for Vega, Rho, Theta
   - Apply when pricing via Monte Carlo or Binomial Tree
4. **Implied volatility extraction**
   - Root-finding via `scipy.optimize.brentq`
   - Search bracket: `[1e-6, 10.0]`
   - Raise `ValueError` with descriptive message if Brent's method does not converge
   - Filter out zero-volume and zero-open-interest contracts before solving
5. **Volatility surface construction**
   - Source: `yfinance` option chain already fetched in the notebook
   - Iterate over all expiries and strikes
   - Store results as a `pandas.DataFrame` indexed by `(expiry, strike)` with column `implied_vol`
   - Surface visualization: `plotly` preferred for interactivity; `matplotlib` as fallback
   - Handle missing/NaN implied vols gracefully (drop, do not interpolate unless explicitly requested)

---

## Out of Scope

- Theory derivations, textbook references, or formula proofs
- AI explanation layer (nice-to-have from README — separate future skill)
- Data ingestion conventions (yfinance/FRED) — handled by existing notebook code
- Web frontend or API layer

---

## Decisions Log

| Decision | Choice | Reason |
|----------|--------|--------|
| Skill purpose | Implementation guide | User specified; explanation layer is a separate future concern |
| Skill count | Two | Pricing methods and risk analytics are distinct concerns |
| File format | Flat Markdown | Project is early-stage; sub-skill routing adds unnecessary overhead |
| Theory references | None | User specified implementation-only focus |
| Library for CDF | `scipy.stats.norm` | Replaces manual `math.erf`; more readable and standard |
| MC paths minimum | 10,000 | Balances accuracy and runtime for educational use |
| Validation tolerance | 1% | Tight enough to catch errors; loose enough for MC variance |
