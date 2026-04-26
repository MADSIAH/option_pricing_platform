import numpy as np


def d1(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    return d1(S, K, T, r, sigma, q) - sigma * np.sqrt(T)
