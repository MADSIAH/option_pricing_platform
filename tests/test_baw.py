import pytest
from src.pricing.base import OptionParams
from src.pricing.baw import BaroneAdesiWhaley
from src.pricing.black_scholes import BlackScholes
from src.pricing.binomial_tree import BinomialTree

baw = BaroneAdesiWhaley()
bs = BlackScholes()
bt_american = BinomialTree(steps=500, american=True)

ATM = dict(S=100.0, K=100.0, T=0.5, r=0.05, sigma=0.2)


# --- result structure ---

def test_returns_pricing_result_call():
    params = OptionParams(**ATM, option_type="call", q=0.03)
    result = baw.price(params)
    assert result.method == "baw"
    assert result.option_type == "call"
    assert result.price > 0


def test_returns_pricing_result_put():
    params = OptionParams(**ATM, option_type="put", q=0.0)
    result = baw.price(params)
    assert result.method == "baw"
    assert result.option_type == "put"
    assert result.price > 0


# --- call with no dividends equals European call exactly ---

def test_call_no_dividend_equals_european():
    params = OptionParams(**ATM, option_type="call", q=0.0)
    assert baw.price(params).price == pytest.approx(bs.price(params).price, rel=1e-9)


# --- American >= European (early exercise premium is non-negative) ---

def test_american_call_ge_european_with_dividends():
    params = OptionParams(**ATM, option_type="call", q=0.05)
    assert baw.price(params).price >= bs.price(params).price - 1e-9


def test_american_put_ge_european():
    params = OptionParams(**ATM, option_type="put", q=0.0)
    assert baw.price(params).price >= bs.price(params).price - 1e-9


def test_american_put_ge_european_with_dividends():
    params = OptionParams(**ATM, option_type="put", q=0.03)
    assert baw.price(params).price >= bs.price(params).price - 1e-9


# --- price >= intrinsic value ---

def test_call_ge_intrinsic():
    params = OptionParams(S=110.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="call", q=0.03)
    assert baw.price(params).price >= max(110.0 - 100.0, 0.0) - 1e-9


def test_put_ge_intrinsic():
    params = OptionParams(S=90.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="put", q=0.0)
    assert baw.price(params).price >= max(100.0 - 90.0, 0.0) - 1e-9


# --- convergence vs BinomialTree (within 1% ATM) ---

def test_put_atm_within_2pct_of_binomial():
    # BAW is an approximation; documented accuracy for puts is within ~2%
    params = OptionParams(**ATM, option_type="put", q=0.0)
    baw_price = baw.price(params).price
    bt_price = bt_american.price(params).price
    assert abs(baw_price - bt_price) / bt_price < 0.02


def test_call_atm_with_dividends_within_1pct_of_binomial():
    params = OptionParams(**ATM, option_type="call", q=0.05)
    baw_price = baw.price(params).price
    bt_price = bt_american.price(params).price
    assert abs(baw_price - bt_price) / bt_price < 0.01


# --- deep ITM: price equals intrinsic ---

def test_deep_itm_put_equals_intrinsic():
    # Very deep ITM put: S well below critical price, early exercise is optimal
    params = OptionParams(S=50.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="put", q=0.0)
    assert baw.price(params).price == pytest.approx(100.0 - 50.0, rel=1e-6)


# --- monotonicity in spot ---

def test_call_monotone_increasing_in_spot():
    prices = [
        baw.price(OptionParams(S=s, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="call", q=0.03)).price
        for s in [80.0, 90.0, 100.0, 110.0, 120.0]
    ]
    assert all(prices[i] < prices[i + 1] for i in range(len(prices) - 1))


def test_put_monotone_decreasing_in_spot():
    prices = [
        baw.price(OptionParams(S=s, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="put", q=0.0)).price
        for s in [80.0, 90.0, 100.0, 110.0, 120.0]
    ]
    assert all(prices[i] > prices[i + 1] for i in range(len(prices) - 1))
