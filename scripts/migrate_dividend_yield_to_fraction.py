"""One-shot migration: convert live_price.dividend_yield from percent to fraction.

Historically the fetcher stored yfinance's `dividendYield` verbatim, which is in
percent units (e.g. 1.03 for 1.03%). The pricing API consumed that value directly
as the option dividend yield `q`, producing absurd yields (1.03 -> 103%) and badly
wrong prices for dividend-paying tickers such as SPY.

The fetcher now stores the value as a decimal fraction (divides by 100). This script
back-fills existing rows the same way.

IMPORTANT: This is NOT idempotent (it always divides by 100). Run it exactly ONCE,
*after* deploying the fetcher fix. Dry-run by default; pass --apply to write.

    python scripts/migrate_dividend_yield_to_fraction.py            # preview
    python scripts/migrate_dividend_yield_to_fraction.py --apply    # commit

Respects the DB_PATH environment variable, like the rest of the data layer.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from src.data.database import LivePrice, session_scope


def main(apply: bool) -> None:
    with session_scope() as session:
        rows = session.execute(select(LivePrice)).scalars().all()
        if not rows:
            print("live_price is empty — nothing to migrate.")
            return

        print(f"{'ticker':<8} {'old (percent)':>14} {'new (fraction)':>16}")
        print("-" * 40)
        for row in rows:
            old = float(row.dividend_yield)
            new = old / 100.0
            print(f"{row.ticker:<8} {old:>14.4f} {new:>16.6f}")
            if apply:
                row.dividend_yield = new

        if apply:
            print("\nApplied. dividend_yield is now stored as a decimal fraction.")
        else:
            print("\nDry run — no changes written. Re-run with --apply to commit.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv[1:])
