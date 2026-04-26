import pytest
from src.pricing import BlackScholes, OptionParams
from src.pricing.binomial_tree import BinomialTree

BASELINE = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call")
BASELINE_PUT = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="put")


def bs_price(params: OptionParams) -> float:
    return BlackScholes().price(params).price


def test_method_label():
    result = BinomialTree().price(BASELINE)
    assert result.method == "binomial-tree"


def test_european_call_convergence_within_1pct_of_black_scholes():
    bt = BinomialTree(steps=500).price(BASELINE)
    bs = bs_price(BASELINE)
    assert abs(bt.price - bs) / bs < 0.01


def test_european_put_convergence_within_1pct_of_black_scholes():
    bt = BinomialTree(steps=500).price(BASELINE_PUT)
    bs = bs_price(BASELINE_PUT)
    assert abs(bt.price - bs) / bs < 0.01


def test_more_steps_converges_closer_to_black_scholes():
    bs = bs_price(BASELINE)
    error_100 = abs(BinomialTree(steps=100).price(BASELINE).price - bs)
    error_500 = abs(BinomialTree(steps=500).price(BASELINE).price - bs)
    assert error_500 < error_100


def test_american_put_worth_at_least_european_put():
    european = BinomialTree(steps=200, american=False).price(BASELINE_PUT).price
    american = BinomialTree(steps=200, american=True).price(BASELINE_PUT).price
    assert american >= european


def test_american_call_equals_european_call_on_non_dividend_stock():
    # For non-dividend paying stocks, American call == European call
    european = BinomialTree(steps=200, american=False).price(BASELINE).price
    american = BinomialTree(steps=200, american=True).price(BASELINE).price
    assert abs(american - european) / european < 0.001


def test_rejects_invalid_option_type():
    with pytest.raises(ValueError):
        OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="invalid")


def test_call_price_lower_with_dividend():
    no_div = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call", q=0.0)
    with_div = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=0.2, option_type="call", q=0.03)
    assert BinomialTree().price(with_div).price < BinomialTree().price(no_div).price
