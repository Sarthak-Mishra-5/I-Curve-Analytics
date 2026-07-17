"""Numba-accelerated rolling stats. Pure-numpy fallbacks if numba unavailable."""
from __future__ import annotations

import numpy as np

try:
    from numba import njit
    _NUMBA = True
except Exception:  # noqa: BLE001
    _NUMBA = False

    def njit(*a, **kw):  # type: ignore
        def deco(f):
            return f
        return deco if (a and callable(a[0])) is False else a[0]


@njit(cache=True, fastmath=True)
def rolling_mean_std(x: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    n = x.shape[0]
    mean = np.empty(n, dtype=np.float64)
    std = np.empty(n, dtype=np.float64)
    for i in range(n):
        a = max(0, i - window + 1)
        s = 0.0
        c = 0
        for j in range(a, i + 1):
            s += x[j]
            c += 1
        m = s / c if c > 0 else 0.0
        mean[i] = m
        v = 0.0
        for j in range(a, i + 1):
            d = x[j] - m
            v += d * d
        std[i] = (v / c) ** 0.5 if c > 0 else 0.0
    return mean, std


@njit(cache=True, fastmath=True)
def ewma(x: np.ndarray, alpha: float) -> np.ndarray:
    n = x.shape[0]
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    out[0] = x[0]
    for i in range(1, n):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


@njit(cache=True, fastmath=True)
def realized_vol(x: np.ndarray, window: int) -> float:
    n = x.shape[0]
    if n < 2:
        return 0.0
    a = max(0, n - window)
    m = 0.0
    c = 0
    for i in range(a + 1, n):
        r = x[i] - x[i - 1]
        m += r
        c += 1
    if c == 0:
        return 0.0
    m /= c
    v = 0.0
    for i in range(a + 1, n):
        r = x[i] - x[i - 1]
        d = r - m
        v += d * d
    return (v / c) ** 0.5


def zscore(x: np.ndarray, window: int) -> float:
    if x.size == 0:
        return 0.0
    w = x[-window:] if x.size > window else x
    if w.size < 2:
        return 0.0
    mu = float(np.mean(w))
    sd = float(np.std(w))
    if sd <= 1e-12:
        return 0.0
    return (float(x[-1]) - mu) / sd


def percentile_of_last(x: np.ndarray, window: int) -> float:
    if x.size == 0:
        return 50.0
    w = x[-window:] if x.size > window else x
    last = float(w[-1])
    return float(100.0 * (np.sum(w <= last) - 1) / max(1, w.size - 1))
