"""Rigor stats: pass rate, pass^k consistency, Wilson CI, percentiles.

Agent runs are non-deterministic, so a single pass number hides variance. The
brief mandates multiple trials + confidence intervals and reporting pass^k
(consistency across trials) beside pass rate. These are pure functions so they
carry unit tests and match the numbers the leaderboard shows.
"""
from __future__ import annotations

import math
import random
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


def bootstrap_ci_by_task(
    per_task_fracs: list[float],
    *,
    n_boot: int = 10_000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """CI for the mean pass rate that respects TASK clustering.

    Trials of the same task are correlated (same instance), so pooling all
    trials into one binomial (Wilson) understates uncertainty. Resampling
    TASKS with replacement is the honest interval for "how would the score
    move on a different draw of tasks?" — the question a ranking claim asks.
    Deterministic for a given ``seed`` so results are reproducible.
    """
    if not per_task_fracs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(per_task_fracs)
    means = sorted(
        sum(rng.choice(per_task_fracs) for _ in range(n)) / n for _ in range(n_boot)
    )
    alpha = (1 - confidence) / 2
    lo = means[max(0, math.floor(alpha * n_boot))]
    hi = means[min(n_boot - 1, math.ceil((1 - alpha) * n_boot) - 1)]
    return (lo, hi)


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar test p-value (two-sided) on discordant pair counts.

    ``b`` = pairs where A passed and B failed; ``c`` = the reverse. Under H0
    (equal ability) each discordant pair is a fair coin, so the p-value is the
    exact binomial tail. Valid for paired benchmark runs — same tasks, same
    seed, same trial count. Small discordant counts (the norm at minibench
    scale) make the chi-square approximation unusable; the exact test is not.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def indistinguishable(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Two configs are 'indistinguishable' if their CIs overlap — not a winner."""
    lo_a, hi_a = a
    lo_b, hi_b = b
    return lo_a <= hi_b and lo_b <= hi_a


# Kept for callers that want a normal-approx z for a custom confidence level.
def z_for(confidence: float = 0.95) -> float:
    return NormalDist().inv_cdf(1 - (1 - confidence) / 2)
