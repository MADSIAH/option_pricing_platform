# AGENTS.md

You are an AI contributor to an options pricing platform.
Read README.md before making any changes.

## Rules

- Use `numpy` in `src/pricing/`, never `pandas`
- Type-hint all public functions; Google-style docstrings
- New parameters MUST have defaults to preserve backward compatibility
- Every model change MUST have a corresponding test
- Option chain data MUST pass through `clean_option_chain()` before any
  IV calculation — never bypass it
- Validate market data from yfinance: check for NaN, zero prices,
  negative T before use
- Never hardcode credentials

## Benchmark

After any numerical method change, verify convergence to Black-Scholes
at ATM (`T=0.5`, `sigma=0.2`, `r=0.05`) within 1% relative error.

## Human Review

- Numerical formulas and model assumptions MUST be validated by a human
  against trusted references before merge
- Never present model output as financial advice

## Documentation

At the end of each working session, update README.md and any relevant
docs to reflect what changed: new features, known issues, and TODOs.

## Workflow

1. Work in a branch, never commit to `main` directly
2. Run `python -m pytest -q` — all tests must pass before opening a PR
3. PR descriptions MUST state what changed and what was validated.
   Merge only after human review.
4. You MAY open a PR yourself if tests pass and the change is
   self-contained
