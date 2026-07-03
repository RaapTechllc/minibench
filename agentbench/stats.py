"""Rigor stats: pass rate, pass^k consistency, Wilson CI, percentiles.

Agent runs are non-deterministic, so a single pass number hides variance. The
brief mandates multiple trials + confidence intervals and reporting pass^k
(consistency across trials) beside pass rate. These are pure functions so they
carry unit tests and match the numbers the leaderboard shows.
"""
from __future__ import annotations

import math
from statistics import NormalDist


def pass_rate(passes: int, trials: int) -> float:
    """Fraction of trials that passed."""
    if trials <= 0:
        return 0.0
    return passes / trials


def pass_hat_k(per_task_passes: list[int], per_task_trials: list[int], k: int) -> float:
    """Unbiased pass^k: expected fraction of tasks solved on ALL of k sampled trials.

    Uses the combinatorial estimator (same family as HumanEval's pass@k): for a
    task with ``n`` trials of which ``c`` passed, the probability that a random
    size-k subset is all-passing is C(c,k)/C(n,k). Averaged over tasks. This
    rewards consistency, not a single lucky trial.
    """
    if not per_task_passes or k < 1:
        return 0.0
    vals = []
    for c, n in zip(per_task_passes, per_task_trials):
        if n < k:
            continue  # not enough trials to estimate pass^k for this task
        if c < k:
            vals.append(0.0)
        else:
            vals.append(math.comb(c, k) / math.comb(n, k))
    return sum(vals) / len(vals) if vals else 0.0


def wilson_ci(passes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (better than normal at extremes)."""
    if trials <= 0:
        return (0.0, 0.0)
    p = passes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile (q in [0,100]). Used for latency p50/p95."""
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    rank = (q / 100) * (len(xs) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (rank - lo)


def indistinguishable(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Two configs are 'indistinguishable' if their CIs overlap — not a winner."""
    lo_a, hi_a = a
    lo_b, hi_b = b
    return lo_a <= hi_b and lo_b <= hi_a


# Kept for callers that want a normal-approx z for a custom confidence level.
def z_for(confidence: float = 0.95) -> float:
    return NormalDist().inv_cdf(1 - (1 - confidence) / 2)
