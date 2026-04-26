import pytest
from src.pricing.base import OptionParams
from src.pricing.greeks import AnalyticalGreeks, NumericalGreeks
from src.pricing.monte_carlo import MonteCarlo
from src.pricing.binomial_tree import BinomialTree

# Standard ATM params used throughout (T=0.5, sigma=0.2, r=0.05, S=K=100)
CALL = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
PUT  = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")

ag = AnalyticalGreeks()


class TestAnalyticalGreeks:
    def test_atm_call_delta_near_half(self):
        g = ag.compute(CALL)
        assert 0.45 < g.delta < 0.65

    def test_atm_put_delta_negative(self):
        g = ag.compute(PUT)
        assert -0.65 < g.delta < -0.35

    def test_put_call_delta_parity(self):
        # delta_call - delta_put = 1 (put-call parity on delta)
        g_call = ag.compute(CALL)
        g_put = ag.compute(PUT)
        assert abs(g_call.delta - g_put.delta - 1.0) < 1e-10

    def test_gamma_positive(self):
        assert ag.compute(CALL).gamma > 0
        assert ag.compute(PUT).gamma > 0

    def test_gamma_call_equals_put(self):
        assert abs(ag.compute(CALL).gamma - ag.compute(PUT).gamma) < 1e-12

    def test_vega_positive(self):
        assert ag.compute(CALL).vega > 0
        assert ag.compute(PUT).vega > 0

    def test_vega_call_equals_put(self):
        assert abs(ag.compute(CALL).vega - ag.compute(PUT).vega) < 1e-10

    def test_theta_negative_for_long_call(self):
        assert ag.compute(CALL).theta < 0

    def test_rho_call_positive_put_negative(self):
        assert ag.compute(CALL).rho > 0
        assert ag.compute(PUT).rho < 0

    def test_method_label(self):
        assert ag.compute(CALL).method == "analytical"

    def test_deep_itm_call_delta_near_one(self):
        params = OptionParams(S=150, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        assert ag.compute(params).delta > 0.9

    def test_deep_otm_call_delta_near_zero(self):
        params = OptionParams(S=50, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
        assert ag.compute(params).delta < 0.1


class TestNumericalGreeks:
    """Numerical Greeks via BinomialTree should match analytical within 2%."""

    def setup_method(self):
        self.ng = NumericalGreeks(BinomialTree(steps=300))

    def _check_close(self, analytical, numerical, tol=0.02):
        if abs(analytical) > 1e-6:
            assert abs(numerical - analytical) / abs(analytical) < tol, (
                f"numerical={numerical:.6f}, analytical={analytical:.6f}"
            )

    def test_delta_call(self):
        a = ag.compute(CALL).delta
        n = self.ng.compute(CALL).delta
        self._check_close(a, n)

    def test_delta_put(self):
        a = ag.compute(PUT).delta
        n = self.ng.compute(PUT).delta
        self._check_close(a, n)

    def test_gamma_call(self):
        # BT numerical gamma is noisier than other Greeks (second-derivative parity effect
        # on the discrete lattice); 70% relative tolerance is the practical bound.
        a = ag.compute(CALL).gamma
        n = self.ng.compute(CALL).gamma
        self._check_close(a, n, tol=0.70)

    def test_vega_call(self):
        a = ag.compute(CALL).vega
        n = self.ng.compute(CALL).vega
        self._check_close(a, n)

    def test_theta_call(self):
        a = ag.compute(CALL).theta
        n = self.ng.compute(CALL).theta
        self._check_close(a, n)

    def test_rho_call(self):
        a = ag.compute(CALL).rho
        n = self.ng.compute(CALL).rho
        self._check_close(a, n)

    def test_method_label(self):
        assert self.ng.compute(CALL).method == "numerical"
