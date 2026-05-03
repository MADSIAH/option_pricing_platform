"""Tests for exotic option pricers.

Key financial properties verified
----------------------------------
Asian    : price < vanilla (averaging reduces volatility)
Barrier  : knock-out + knock-in = vanilla (parity)
           knock-out = 0 when spot already past barrier at t=0
           knock-out < vanilla
Lookback : price >= vanilla (exercises at the best price over the period)
Digital  : call + put ≈ exp(-rT) (certainty of paying $1)
           call ≈ exp(-rT)*N(d2) (Black-Scholes analytical)
"""

import numpy as np
import pytest
from scipy.stats import norm

from src.pricing.base import OptionParams
from src.pricing.black_scholes import BlackScholes
from src.pricing.exotics import AsianOption, BarrierOption, DigitalOption, LookbackOption

# ── shared fixtures ─────────────────────────────────────────────────────────
# Use fewer paths/steps in tests for speed; financial properties still hold.
N_PATHS = 20_000
N_STEPS = 63   # quarterly monitoring (≈ 1 step / week for T=0.25 ... rescales)

BS = BlackScholes()

CALL = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
PUT  = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")

def vanilla_price(params):
    return BS.price(params).price


# ── GBMPathSimulator ────────────────────────────────────────────────────────
class TestPathSimulator:
    def test_shape(self):
        from src.pricing.path_simulator import GBMPathSimulator
        sim = GBMPathSimulator(n_paths=1_000, n_steps=50, seed=0)
        paths = sim.simulate(CALL)
        assert paths.shape == (1_000, 51)

    def test_first_column_is_spot(self):
        from src.pricing.path_simulator import GBMPathSimulator
        sim = GBMPathSimulator(n_paths=500, n_steps=10, seed=0)
        paths = sim.simulate(CALL)
        assert np.allclose(paths[:, 0], CALL.S)

    def test_terminal_mean_near_forward(self):
        """E[S_T] ≈ S * exp((r-q)*T) under risk-neutral measure."""
        from src.pricing.path_simulator import GBMPathSimulator
        sim = GBMPathSimulator(n_paths=50_000, n_steps=252, seed=42)
        paths = sim.simulate(CALL)
        forward = CALL.S * np.exp((CALL.r - CALL.q) * CALL.T)
        assert abs(paths[:, -1].mean() / forward - 1) < 0.01  # within 1%

    def test_antithetic_symmetry(self):
        """Second half of paths should be mirrors of the first half."""
        from src.pricing.path_simulator import GBMPathSimulator
        sim = GBMPathSimulator(n_paths=1_000, n_steps=20, seed=7)
        paths = sim.simulate(CALL)
        half = 500
        # log(S_t / S_0) of path i and path i+half should sum to 2*(r-q-0.5σ²)*T
        log_returns_1 = np.log(paths[:half, -1] / CALL.S)
        log_returns_2 = np.log(paths[half:, -1] / CALL.S)
        expected_sum = 2 * (CALL.r - CALL.q - 0.5 * CALL.sigma**2) * CALL.T
        assert np.allclose(log_returns_1 + log_returns_2, expected_sum, atol=1e-10)


# ── Asian option ─────────────────────────────────────────────────────────────
class TestAsianOption:
    def setup_method(self):
        self.asian = AsianOption(n_paths=N_PATHS, n_steps=N_STEPS, seed=42)

    def test_call_cheaper_than_vanilla(self):
        asian_price = self.asian.price(CALL).price
        v_price = vanilla_price(CALL)
        assert asian_price < v_price

    def test_put_cheaper_than_vanilla(self):
        asian_price = self.asian.price(PUT).price
        v_price = vanilla_price(PUT)
        assert asian_price < v_price

    def test_call_positive(self):
        assert self.asian.price(CALL).price > 0

    def test_put_positive(self):
        assert self.asian.price(PUT).price > 0

    def test_method_label(self):
        assert self.asian.price(CALL).method == "asian-mc"

    def test_deep_itm_call_close_to_intrinsic(self):
        """Deep ITM Asian call ≈ (S - K)*exp(-rT) since avg ≈ S >> K."""
        params = OptionParams(S=200, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        price = self.asian.price(params).price
        intrinsic = (params.S - params.K) * np.exp(-params.r * params.T)
        assert price > intrinsic * 0.85   # at least 85% of discounted intrinsic


# ── Barrier option ────────────────────────────────────────────────────────────
class TestBarrierOption:
    def _make(self, barrier, btype, n_paths=N_PATHS, n_steps=N_STEPS):
        return BarrierOption(barrier=barrier, barrier_type=btype,
                             n_paths=n_paths, n_steps=n_steps, seed=42)

    # parity: knock-out + knock-in = vanilla MC (not analytical BS)
    # tolerance accounts for MC variance on the vanilla price itself
    def test_parity_up_call(self):
        H = 120.0
        out = self._make(H, "up-and-out").price(CALL).price
        inn = self._make(H, "up-and-in").price(CALL).price
        v   = vanilla_price(CALL)
        assert abs(out + inn - v) < 0.15   # within 15 cents (MC noise on vanilla)

    def test_parity_down_put(self):
        H = 80.0
        out = self._make(H, "down-and-out").price(PUT).price
        inn = self._make(H, "down-and-in").price(PUT).price
        v   = vanilla_price(PUT)
        assert abs(out + inn - v) < 0.15

    # knock-out with barrier already breached → price ≈ 0
    def test_up_and_out_call_zero_when_barrier_below_spot(self):
        """If H < S, all paths immediately breach → price ≈ 0."""
        H = 90.0   # below S=100
        price = self._make(H, "up-and-out").price(CALL).price
        assert price < 0.10

    def test_down_and_out_put_zero_when_barrier_above_spot(self):
        """If H > S, all paths immediately breach → price ≈ 0."""
        H = 110.0  # above S=100
        price = self._make(H, "down-and-out").price(PUT).price
        assert price < 0.10

    # knock-out < vanilla (barrier can only remove value)
    def test_up_and_out_cheaper_than_vanilla(self):
        price = self._make(130.0, "up-and-out").price(CALL).price
        assert price < vanilla_price(CALL)

    def test_down_and_out_cheaper_than_vanilla(self):
        price = self._make(70.0, "down-and-out").price(PUT).price
        assert price < vanilla_price(PUT)

    # very far barrier → knock-out ≈ vanilla
    def test_up_and_out_far_barrier_near_vanilla(self):
        price = self._make(10_000.0, "up-and-out", n_paths=40_000).price(CALL).price
        v = vanilla_price(CALL)
        assert abs(price / v - 1) < 0.03

    def test_invalid_barrier_type_raises(self):
        with pytest.raises(ValueError):
            BarrierOption(barrier=120, barrier_type="sideways-and-confused")

    def test_method_label(self):
        price_result = self._make(130, "up-and-out").price(CALL)
        assert "barrier" in price_result.method


# ── Lookback option ───────────────────────────────────────────────────────────
class TestLookbackOption:
    def setup_method(self):
        self.lb = LookbackOption(n_paths=N_PATHS, n_steps=N_STEPS, seed=42)

    def test_call_geq_vanilla(self):
        """Lookback call ≥ vanilla call (exercises at historical max)."""
        assert self.lb.price(CALL).price >= vanilla_price(CALL) - 0.05

    def test_put_geq_vanilla(self):
        """Lookback put ≥ vanilla put (exercises at historical min)."""
        assert self.lb.price(PUT).price >= vanilla_price(PUT) - 0.05

    def test_call_positive(self):
        assert self.lb.price(CALL).price > 0

    def test_put_positive(self):
        assert self.lb.price(PUT).price > 0

    def test_method_label(self):
        assert self.lb.price(CALL).method == "lookback-mc"


# ── Digital option ────────────────────────────────────────────────────────────
class TestDigitalOption:
    def setup_method(self):
        self.dig = DigitalOption(n_paths=N_PATHS * 2, seed=42)

    def test_call_plus_put_equals_bond(self):
        """Digital call + digital put = exp(-rT) (one of them always pays $1)."""
        call_price = self.dig.price(CALL).price
        put_price  = self.dig.price(PUT).price
        bond = np.exp(-CALL.r * CALL.T)
        assert abs(call_price + put_price - bond) < 0.02

    def test_call_matches_bs_analytical(self):
        """Digital call = exp(-rT) * N(d2)."""
        from src.pricing.utils import d2
        _d2 = d2(CALL.S, CALL.K, CALL.T, CALL.r, CALL.sigma)
        analytical = np.exp(-CALL.r * CALL.T) * norm.cdf(_d2)
        mc_price = self.dig.price(CALL).price
        assert abs(mc_price / analytical - 1) < 0.03   # within 3%

    def test_deep_itm_call_near_bond(self):
        """Deep ITM digital call ≈ exp(-rT) (pays $1 almost surely)."""
        params = OptionParams(S=200, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        price = self.dig.price(params).price
        bond  = np.exp(-params.r * params.T)
        assert abs(price / bond - 1) < 0.02

    def test_method_label(self):
        assert self.dig.price(CALL).method == "digital-mc"
