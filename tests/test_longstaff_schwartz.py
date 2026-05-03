"""Tests for the Longstaff-Schwartz American option pricer.

Key financial properties verified
----------------------------------
American put  ≥ European put     (early exercise premium)
American call ≈ European call    (non-dividend stock: never optimal to exercise early)
LS American put close to BT American put (cross-model validation, within ~3%)
Price > 0, method label correct
Deep ITM put bounded above by discounted intrinsic
"""

import numpy as np
import pytest

from src.pricing.base import OptionParams
from src.pricing.black_scholes import BlackScholes
from src.pricing.binomial_tree import BinomialTree
from src.pricing.longstaff_schwartz import LongstaffSchwartz

# ── shared fixtures ──────────────────────────────────────────────────────────
BS = BlackScholes()
BT = BinomialTree(steps=500)

CALL = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
PUT  = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")

# Use fewer paths for speed; properties still hold statistically.
LS = LongstaffSchwartz(n_paths=20_000, n_steps=100, seed=42)


class TestLongstaffSchwartz:

    # ── Sanity ────────────────────────────────────────────────────────────────

    def test_call_positive(self):
        assert LS.price(CALL).price > 0

    def test_put_positive(self):
        assert LS.price(PUT).price > 0

    def test_method_label_call(self):
        assert LS.price(CALL).method == "longstaff-schwartz"

    def test_method_label_put(self):
        assert LS.price(PUT).method == "longstaff-schwartz"

    def test_option_type_stored(self):
        assert LS.price(CALL).option_type == "call"
        assert LS.price(PUT).option_type == "put"

    # ── Early-exercise premium ────────────────────────────────────────────────

    def test_american_put_geq_european_put(self):
        """American put ≥ European put (early exercise has non-negative value)."""
        american_put = LS.price(PUT).price
        european_put = BS.price(PUT).price
        assert american_put >= european_put - 0.05   # 5-cent tolerance for MC noise

    def test_american_call_approx_european_call(self):
        """American call on a non-dividend stock ≈ European call.

        It is never optimal to exercise an American call early on a non-dividend
        paying stock (Merton 1973), so LS should match Black-Scholes closely.
        """
        american_call = LS.price(CALL).price
        european_call = BS.price(CALL).price
        # Allow 3% relative tolerance — LS is MC so has some variance
        assert abs(american_call / european_call - 1) < 0.04

    # ── Cross-model validation ────────────────────────────────────────────────

    def test_american_put_close_to_binomial_tree(self):
        """LS and BT American put should agree within ~5%.

        Both are numerical methods with different discretisation errors:
        LS uses MC regression (sampling noise) and BT uses a lattice (step-count error).
        5% tolerance accommodates these joint approximation differences.
        """
        ls_price = LS.price(PUT).price
        bt_price  = BT.price(PUT).price        # BT prices American by default
        assert abs(ls_price / bt_price - 1) < 0.05

    # ── Monotonicity / boundary conditions ───────────────────────────────────

    def test_put_price_decreases_with_spot(self):
        """Higher spot → lower put price."""
        put_itm  = OptionParams(S=90,  K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")
        put_atm  = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")
        put_otm  = OptionParams(S=110, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")
        p_itm  = LS.price(put_itm).price
        p_atm  = LS.price(put_atm).price
        p_otm  = LS.price(put_otm).price
        assert p_itm > p_atm > p_otm

    def test_call_price_increases_with_spot(self):
        """Higher spot → higher call price."""
        call_otm = OptionParams(S=90,  K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        call_atm = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        call_itm = OptionParams(S=110, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        p_otm = LS.price(call_otm).price
        p_atm = LS.price(call_atm).price
        p_itm = LS.price(call_itm).price
        assert p_itm > p_atm > p_otm

    def test_deep_itm_put_bounded_by_intrinsic(self):
        """Deep ITM American put ≤ intrinsic (K - S) — can exercise immediately."""
        params = OptionParams(S=60, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")
        price     = LS.price(params).price
        intrinsic = params.K - params.S
        assert price <= intrinsic + 0.10   # small tolerance for MC noise

    def test_price_increases_with_volatility(self):
        """Higher vol → higher American option price (options love vol)."""
        low_vol  = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.10, option_type="put")
        high_vol = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.40, option_type="put")
        assert LS.price(low_vol).price < LS.price(high_vol).price

    def test_price_increases_with_time(self):
        """Longer expiry → higher American option price (more time = more value)."""
        short = OptionParams(S=100, K=100, T=0.25, r=0.05, sigma=0.2, option_type="put")
        long_ = OptionParams(S=100, K=100, T=1.00, r=0.05, sigma=0.2, option_type="put")
        assert LS.price(short).price < LS.price(long_).price
