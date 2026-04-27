import numpy as np
import pandas as pd
import pytest

from src.pricing.base import OptionParams
from src.pricing.black_scholes import BlackScholes
from src.pricing.vol_surface import implied_vol, build_vol_surface, clean_option_chain

bs = BlackScholes()


def bs_price(S, K, T, r, sigma, option_type):
    p = OptionParams(S=S, K=K, T=T, r=r, sigma=sigma, option_type=option_type)
    return bs.price(p).price


class TestImpliedVol:
    def test_roundtrip_call(self):
        """Implied vol should recover the input sigma when BS price is used."""
        sigma_input = 0.25
        price = bs_price(100, 100, 0.5, 0.05, sigma_input, "call")
        iv = implied_vol(price, S=100, K=100, T=0.5, r=0.05, option_type="call")
        assert abs(iv - sigma_input) < 1e-5

    def test_roundtrip_put(self):
        sigma_input = 0.30
        price = bs_price(100, 110, 1.0, 0.03, sigma_input, "put")
        iv = implied_vol(price, S=100, K=110, T=1.0, r=0.03, option_type="put")
        assert abs(iv - sigma_input) < 1e-5

    def test_roundtrip_otm_call(self):
        sigma_input = 0.20
        price = bs_price(100, 120, 0.5, 0.05, sigma_input, "call")
        iv = implied_vol(price, S=100, K=120, T=0.5, r=0.05, option_type="call")
        assert abs(iv - sigma_input) < 1e-5

    def test_raises_on_impossible_price(self):
        """A call priced above its intrinsic value + BS max is impossible."""
        with pytest.raises(ValueError):
            implied_vol(9999.0, S=100, K=100, T=0.5, r=0.05, option_type="call")

    def test_raises_on_zero_price_for_itm_call(self):
        """Zero price for deep ITM call has no implied vol solution."""
        with pytest.raises(ValueError):
            implied_vol(0.0, S=150, K=100, T=0.5, r=0.05, option_type="call")

    def test_different_vol_levels(self):
        """Higher sigma → higher price → higher implied vol."""
        price_lo = bs_price(100, 100, 1.0, 0.05, 0.10, "call")
        price_hi = bs_price(100, 100, 1.0, 0.05, 0.40, "call")
        iv_lo = implied_vol(price_lo, 100, 100, 1.0, 0.05, "call")
        iv_hi = implied_vol(price_hi, 100, 100, 1.0, 0.05, "call")
        assert iv_hi > iv_lo


class TestBuildVolSurface:
    def _make_chain(self):
        """Synthetic option chain built from known BS prices."""
        rows = []
        for expiry, T in [("2026-07", 0.25), ("2026-10", 0.5), ("2027-01", 0.75)]:
            for K in [90.0, 100.0, 110.0]:
                sigma = 0.20 + 0.02 * abs(K - 100) / 100  # slight skew
                price = bs_price(100, K, T, 0.05, sigma, "call")
                rows.append({"expiry": expiry, "strike": K, "mid_price": price, "T": T})
        return pd.DataFrame(rows)

    def test_surface_shape(self):
        chain = self._make_chain()
        surface = build_vol_surface(chain, S=100, r=0.05, option_type="call")
        assert isinstance(surface, pd.DataFrame)
        assert len(surface) == 9  # 3 expiries × 3 strikes

    def test_surface_index(self):
        chain = self._make_chain()
        surface = build_vol_surface(chain, S=100, r=0.05)
        assert surface.index.names == ["expiry", "strike"]

    def test_surface_values_close_to_input_sigma(self):
        chain = self._make_chain()
        surface = build_vol_surface(chain, S=100, r=0.05)
        # ATM options should recover ~0.20
        atm_ivs = surface.loc[(slice(None), 100.0), "implied_vol"]
        for iv in atm_ivs:
            assert abs(iv - 0.20) < 1e-4

    def test_surface_no_nan_for_valid_chain(self):
        chain = self._make_chain()
        surface = build_vol_surface(chain, S=100, r=0.05)
        assert surface["implied_vol"].isna().sum() == 0

    def test_cleaning_flag_filters_bad_rows(self):
        rows = [
            {
                "expiry": "2026-10",
                "strike": 100.0,
                "bid": 6.8,
                "ask": 7.2,
                "volume": 100,
                "openInterest": 200,
                "T": 0.5,
            },
            {
                "expiry": "2026-10",
                "strike": 170.0,
                "bid": 0.05,
                "ask": 0.70,  # very wide spread + far OTM
                "volume": 100,
                "openInterest": 200,
                "T": 0.5,
            },
        ]
        chain = pd.DataFrame(rows)
        chain["mid_price"] = (chain["bid"] + chain["ask"]) / 2.0

        surface_unclean = build_vol_surface(chain, S=100, r=0.05, clean=False)
        surface_clean = build_vol_surface(chain, S=100, r=0.05, clean=True)

        assert len(surface_unclean) == 2
        assert len(surface_clean) == 1


class TestChainCleaning:
    def _base_chain(self):
        return pd.DataFrame(
            [
                {
                    "expiry": "2026-07",
                    "strike": 100.0,
                    "bid": 5.8,
                    "ask": 6.2,
                    "volume": 10,
                    "openInterest": 10,
                    "T": 0.4,
                },
                {
                    "expiry": "2026-07",
                    "strike": 100.0,
                    "bid": 5.8,
                    "ask": 6.2,
                    "volume": 10,
                    "openInterest": 10,
                    "T": 3.0 / 365.0,  # too close to expiry
                },
                {
                    "expiry": "2026-07",
                    "strike": 100.0,
                    "bid": 2.0,
                    "ask": 5.0,  # too wide spread
                    "volume": 10,
                    "openInterest": 10,
                    "T": 0.4,
                },
                {
                    "expiry": "2026-07",
                    "strike": 170.0,  # moneyness > 1.3 for S=100
                    "bid": 0.3,
                    "ask": 0.4,
                    "volume": 10,
                    "openInterest": 10,
                    "T": 0.4,
                },
            ]
        )

    def test_filters_min_days_to_expiry(self):
        chain = self._base_chain()
        cleaned = clean_option_chain(chain, S=100)
        assert (cleaned["T"] >= 7.0 / 365.0).all()

    def test_filters_relative_spread(self):
        chain = self._base_chain()
        cleaned = clean_option_chain(chain, S=100)
        spreads = (cleaned["ask"] - cleaned["bid"]) / cleaned["mid_price"]
        assert (spreads <= 0.35).all()

    def test_filters_moneyness_range(self):
        chain = self._base_chain()
        cleaned = clean_option_chain(chain, S=100)
        m = cleaned["strike"] / 100.0
        assert (m >= 0.7).all()
        assert (m <= 1.3).all()

    def test_returns_expected_number_of_rows(self):
        chain = self._base_chain()
        cleaned = clean_option_chain(chain, S=100)
        assert len(cleaned) == 1


class TestDividend:
    def test_roundtrip_with_dividend(self):
        sigma_input = 0.25
        p = OptionParams(S=100, K=100, T=0.5, r=0.05, sigma=sigma_input, option_type="call", q=0.02)
        from src.pricing.black_scholes import BlackScholes
        price = BlackScholes().price(p).price
        iv = implied_vol(price, S=100, K=100, T=0.5, r=0.05, option_type="call", q=0.02)
        assert abs(iv - sigma_input) < 1e-5
