"""Tests for the Heston stochastic volatility Monte Carlo pricer.

Key financial properties verified
----------------------------------
Price > 0 for both calls and puts
Put-call parity: C - P ≈ S*exp(-qT) - K*exp(-rT)
Heston → Black-Scholes when xi → 0 and v0 = theta = sigma²
Higher vol-of-vol (xi) → higher OTM option prices (volatility smile effect)
Feller condition violation issues a UserWarning (not an error)
"""

import warnings

import numpy as np
import pytest

from src.pricing.black_scholes import BlackScholes
from src.pricing.heston import HestonMC, HestonParams

# ── helpers ──────────────────────────────────────────────────────────────────
BS = BlackScholes()

# Fewer paths for test speed; properties still hold statistically.
MC = HestonMC(n_paths=30_000, n_steps=100, seed=42)

SIGMA = 0.20
BASE_CALL = HestonParams(
    S=100, K=100, T=0.5, r=0.05,
    v0=SIGMA**2, kappa=2.0, theta=SIGMA**2, xi=0.30, rho=-0.70,
    option_type="call",
)
BASE_PUT = HestonParams(
    S=100, K=100, T=0.5, r=0.05,
    v0=SIGMA**2, kappa=2.0, theta=SIGMA**2, xi=0.30, rho=-0.70,
    option_type="put",
)


def _put(**overrides):
    """Convenience: create a put with overridden fields."""
    d = dict(
        S=100, K=100, T=0.5, r=0.05,
        v0=SIGMA**2, kappa=2.0, theta=SIGMA**2, xi=0.30, rho=-0.70,
        option_type="put",
    )
    d.update(overrides)
    return HestonParams(**d)


def _call(**overrides):
    d = dict(
        S=100, K=100, T=0.5, r=0.05,
        v0=SIGMA**2, kappa=2.0, theta=SIGMA**2, xi=0.30, rho=-0.70,
        option_type="call",
    )
    d.update(overrides)
    return HestonParams(**d)


# ── HestonParams validation ──────────────────────────────────────────────────
class TestHestonParamsValidation:

    def test_invalid_option_type(self):
        with pytest.raises(ValueError, match="option_type"):
            HestonParams(S=100, K=100, T=0.5, r=0.05,
                         v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7,
                         option_type="strangle")

    def test_zero_T(self):
        with pytest.raises(ValueError):
            HestonParams(S=100, K=100, T=0, r=0.05,
                         v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7,
                         option_type="call")

    def test_negative_S(self):
        with pytest.raises(ValueError):
            HestonParams(S=-1, K=100, T=0.5, r=0.05,
                         v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7,
                         option_type="call")

    def test_rho_out_of_range(self):
        with pytest.raises(ValueError):
            HestonParams(S=100, K=100, T=0.5, r=0.05,
                         v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=1.0,
                         option_type="call")


# ── Basic sanity ─────────────────────────────────────────────────────────────
class TestHestonMC:

    def test_call_positive(self):
        assert MC.price(BASE_CALL).price > 0

    def test_put_positive(self):
        assert MC.price(BASE_PUT).price > 0

    def test_method_label(self):
        assert MC.price(BASE_CALL).method == "heston-mc"

    def test_option_type_stored_call(self):
        assert MC.price(BASE_CALL).option_type == "call"

    def test_option_type_stored_put(self):
        assert MC.price(BASE_PUT).option_type == "put"

    # ── Put-call parity ───────────────────────────────────────────────────────

    def test_put_call_parity(self):
        """C - P = S*exp(-qT) - K*exp(-rT)  (generalised with q=0)."""
        p = BASE_CALL
        call = MC.price(BASE_CALL).price
        put  = MC.price(BASE_PUT).price
        lhs = call - put
        rhs = p.S * np.exp(-p.q * p.T) - p.K * np.exp(-p.r * p.T)
        assert abs(lhs - rhs) < 0.20   # MC variance on two prices

    # ── Heston → Black-Scholes when xi → 0 ───────────────────────────────────

    def test_heston_collapses_to_bs_low_xi(self):
        """With xi → 0 and v0 = theta = sigma², Heston ≈ Black-Scholes."""
        from src.pricing.base import OptionParams
        bs_params = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=SIGMA,
                                 option_type="call")
        bs_price = BS.price(bs_params).price

        # xi very small; use more paths to reduce MC noise at low vol-of-vol
        mc_low_xi = HestonMC(n_paths=60_000, n_steps=252, seed=42)
        h_params = _call(xi=0.001, rho=0.0)
        heston_price = mc_low_xi.price(h_params).price

        assert abs(heston_price / bs_price - 1) < 0.02   # within 2%

    # ── Vol smile: higher xi → higher OTM prices ─────────────────────────────

    def test_vol_of_vol_raises_otm_put_symmetric(self):
        """Higher xi → fatter tails → higher OTM put price (rho=0 symmetric case).

        At rho=0 Heston generates a symmetric smile: both tails fatten equally.
        Deep OTM puts sit in the left tail and are therefore clearly sensitive to xi.
        Both xi values satisfy Feller: 2κθ = 0.16 > xi².
        """
        put_low  = MC.price(_put(K=80, xi=0.05, rho=0.0)).price
        put_high = MC.price(_put(K=80, xi=0.35, rho=0.0)).price
        assert put_high > put_low

    def test_higher_xi_increases_otm_put(self):
        """Higher vol-of-vol → fatter tails → more expensive OTM puts (rho=0)."""
        otm_low  = MC.price(_put(K=85, xi=0.10, rho=0.0)).price
        otm_high = MC.price(_put(K=85, xi=0.35, rho=0.0)).price
        assert otm_high > otm_low

    def test_negative_rho_cheapens_otm_call(self):
        """Negative rho (equity skew) → left tail heavier → OTM call cheaper.

        With rho=-0.70, volatility rises when the stock falls, creating a
        negative skew: right tail is lighter → OTM call price decreases.
        """
        otm_low_rho   = MC.price(_call(K=115, xi=0.30, rho=-0.70)).price
        otm_zero_rho  = MC.price(_call(K=115, xi=0.30, rho= 0.00)).price
        assert otm_low_rho < otm_zero_rho

    # ── Feller condition warning ──────────────────────────────────────────────

    def test_feller_violation_warns(self):
        """2*kappa*theta < xi² should issue a UserWarning, not raise."""
        # Choose params that clearly violate Feller: 2*0.5*0.04 = 0.04 < 1.0 = xi²
        p = _call(kappa=0.5, theta=0.04, xi=1.0)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = MC.price(p)
            assert any(issubclass(warning.category, UserWarning) for warning in w)
        assert result.price > 0   # still prices despite warning

    def test_feller_satisfied_no_warning(self):
        """When Feller holds, no UserWarning should be raised."""
        # 2*3*0.04 = 0.24 > 0.09 = 0.3² — Feller satisfied
        p = _call(kappa=3.0, theta=0.04, xi=0.3)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            MC.price(p)
            user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
            assert len(user_warnings) == 0

    # ── Monotonicity ──────────────────────────────────────────────────────────

    def test_call_increases_with_spot(self):
        p_low  = MC.price(_call(S=90)).price
        p_mid  = MC.price(_call(S=100)).price
        p_high = MC.price(_call(S=110)).price
        assert p_low < p_mid < p_high

    def test_put_decreases_with_spot(self):
        p_low  = MC.price(_put(S=90)).price
        p_mid  = MC.price(_put(S=100)).price
        p_high = MC.price(_put(S=110)).price
        assert p_low > p_mid > p_high

    def test_both_increase_with_maturity(self):
        short = MC.price(_call(T=0.25)).price
        long_ = MC.price(_call(T=1.00)).price
        assert short < long_

    # ── Dividend yield effect ─────────────────────────────────────────────────

    def test_dividend_lowers_call(self):
        """Call price should decrease when a continuous dividend yield is added."""
        no_div  = MC.price(_call(q=0.0)).price
        with_div = MC.price(_call(q=0.03)).price
        assert with_div < no_div

    def test_dividend_raises_put(self):
        """Put price should increase when a continuous dividend yield is added."""
        no_div   = MC.price(_put(q=0.0)).price
        with_div = MC.price(_put(q=0.03)).price
        assert with_div > no_div
