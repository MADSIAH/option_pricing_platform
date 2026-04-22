import pytest
from src.pricing import BlackScholes, OptionParams
from src.pricing.monte_carlo import MonteCarlo

BASELINE = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
BASELINE_PUT = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")


def bs_price(params: OptionParams) -> float:
    return BlackScholes().price(params).price


def test_method_label():
    result = MonteCarlo().price(BASELINE)
    assert result.method == "monte-carlo"


def test_call_convergence_within_1pct_of_black_scholes():
    mc = MonteCarlo().price(BASELINE)
    bs = bs_price(BASELINE)
    assert abs(mc.price - bs) / bs < 0.01


def test_put_convergence_within_1pct_of_black_scholes():
    mc = MonteCarlo().price(BASELINE_PUT)
    bs = bs_price(BASELINE_PUT)
    assert abs(mc.price - bs) / bs < 0.01


def test_put_call_parity():
    # C - P = S - K*exp(-r*T)
    import numpy as np
    p = BASELINE
    call = MonteCarlo().price(p).price
    put = MonteCarlo().price(BASELINE_PUT).price
    parity = p.S - p.K * np.exp(-p.r * p.T)
    assert abs((call - put) - parity) / abs(parity) < 0.02


def test_reproducible_with_same_seed():
    r1 = MonteCarlo(seed=0).price(BASELINE).price
    r2 = MonteCarlo(seed=0).price(BASELINE).price
    assert r1 == r2


def test_different_seeds_give_different_prices():
    r1 = MonteCarlo(seed=0).price(BASELINE).price
    r2 = MonteCarlo(seed=99).price(BASELINE).price
    assert r1 != r2


def test_rejects_invalid_option_type():
    with pytest.raises(ValueError):
        OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="invalid")
