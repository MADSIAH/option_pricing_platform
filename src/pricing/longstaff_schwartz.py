"""Longstaff-Schwartz LSM algorithm for American option pricing.

Algorithm (Longstaff & Schwartz, 2001)
---------------------------------------
1. Simulate N GBM paths with M time steps.
2. At maturity, set cash_flows = intrinsic payoff.
3. Backward from t = M-1 to t = 1:
   a. Discount cash_flows one step.
   b. Identify in-the-money (ITM) paths at time t.
   c. Regress discounted cash_flows on a polynomial basis of S_t
      to estimate the continuation value.
   d. Where immediate exercise > estimated continuation: exercise now
      (replace cash_flows with intrinsic at t).
4. Discount once more to t = 0 and average.

The regression identifies *when* to exercise optimally on each path.
Early exercise is possible at every monitoring date (daily by default).
"""

import numpy as np

from .base import OptionParams, PricingModel, PricingResult
from .path_simulator import GBMPathSimulator


class LongstaffSchwartz(PricingModel):
    """American option pricing via the Longstaff-Schwartz LSM algorithm.

    Parameters
    ----------
    n_paths : int
        Number of simulated paths (must be even; half are antithetic mirrors).
    n_steps : int
        Number of exercise opportunities (time steps). 252 ≈ daily monitoring.
    seed : int
        RNG seed for reproducibility.
    degree : int
        Degree of the polynomial regression basis (default 2: 1, S, S²).
        Higher degrees capture more curvature but risk over-fitting.
    """

    def __init__(
        self,
        n_paths: int = 50_000,
        n_steps: int = 252,
        seed: int = 42,
        degree: int = 2,
    ):
        self._sim = GBMPathSimulator(n_paths=n_paths, n_steps=n_steps, seed=seed)
        self._degree = degree

    def price(self, params: OptionParams) -> PricingResult:
        p = params
        paths = self._sim.simulate(p)               # (n_paths, n_steps+1)
        n_paths, n_cols = paths.shape
        n_steps = n_cols - 1
        dt = p.T / n_steps
        discount = np.exp(-p.r * dt)

        # intrinsic payoff at every node
        if p.option_type == "call":
            intrinsic = np.maximum(paths - p.K, 0.0)
        else:
            intrinsic = np.maximum(p.K - paths, 0.0)

        # cash_flows[i] = best discounted future payoff for path i
        cash_flows = intrinsic[:, -1].copy()

        # backward induction: t = n_steps-1 down to t = 1
        for t in range(n_steps - 1, 0, -1):
            cash_flows *= discount                  # discount one step backward

            itm = intrinsic[:, t] > 0
            n_itm = itm.sum()
            if n_itm < self._degree + 2:            # too few ITM paths to regress
                continue

            # normalised basis to improve conditioning: x = S_t / K
            x = paths[itm, t] / p.K
            X = np.column_stack([x ** k for k in range(self._degree + 1)])
            Y = cash_flows[itm]

            coeffs, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
            continuation = X @ coeffs

            # exercise now where immediate value beats expected continuation
            exercise = intrinsic[itm, t] > continuation
            idx = np.where(itm)[0][exercise]
            cash_flows[idx] = intrinsic[idx, t]

        # final discount from t=1 to t=0
        value = float(cash_flows.mean() * discount)
        return PricingResult(
            price=value, method="longstaff-schwartz", option_type=p.option_type
        )
