"""GBM path simulator — generates full price trajectories for exotic pricing."""

import numpy as np

from .base import OptionParams


class GBMPathSimulator:
    """Simulate N risk-neutral GBM paths with antithetic variates.

    Parameters
    ----------
    n_paths : int
        Total number of paths (must be even; half are antithetic mirrors).
    n_steps : int
        Number of time steps per path. 252 ≈ daily for a 1-year option.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    paths : np.ndarray, shape (n_paths, n_steps + 1)
        paths[:, 0] = S (spot), paths[:, -1] = S_T.
    """

    def __init__(self, n_paths: int = 50_000, n_steps: int = 252, seed: int = 42):
        self.n_paths = n_paths
        self.n_steps = n_steps
        self.seed = seed

    def simulate(self, params: OptionParams) -> np.ndarray:
        p = params
        dt = p.T / self.n_steps
        drift = (p.r - p.q - 0.5 * p.sigma ** 2) * dt
        diffusion = p.sigma * np.sqrt(dt)

        rng = np.random.default_rng(self.seed)
        half = self.n_paths // 2
        Z = rng.standard_normal((half, self.n_steps))
        Z = np.concatenate([Z, -Z], axis=0)  # antithetic variates

        # log-increments → cumulative log-price → price
        log_increments = drift + diffusion * Z          # (n_paths, n_steps)
        log_paths = np.cumsum(log_increments, axis=1)   # (n_paths, n_steps)

        # prepend log(S0) = 0 column, then exponentiate
        log_paths = np.hstack([np.zeros((self.n_paths, 1)), log_paths])
        return p.S * np.exp(log_paths)                  # (n_paths, n_steps + 1)
