from agentbench.stats import (
    bootstrap_ci_by_task,
    consistency,
    mcnemar_exact,
    mean_brier,
    pass_rate,
    pass_hat_k,
    wilson_ci,
    percentile,
    indistinguishable,
)


def test_pass_rate():
    assert pass_rate(3, 4) == 0.75
    assert pass_rate(0, 0) == 0.0


def test_pass_hat_k_rewards_consistency():
    # Task A: 5/5 pass -> pass^3 = 1. Task B: 2/5 pass -> C(2,3)=0.
    val = pass_hat_k([5, 2], [5, 5], k=3)
    assert abs(val - 0.5) < 1e-9  # (1.0 + 0.0) / 2


def test_pass_hat_k_partial():
    # 4/5 passed, k=2: C(4,2)/C(5,2) = 6/10 = 0.6
    assert abs(pass_hat_k([4], [5], k=2) - 0.6) < 1e-9


def test_pass_hat_k_skips_tasks_with_too_few_trials():
    assert pass_hat_k([1], [1], k=3) == 0.0  # n<k -> no estimate -> empty -> 0


def test_wilson_ci_bounds_and_ordering():
    lo, hi = wilson_ci(8, 10)
    assert 0.0 <= lo < 0.8 < hi <= 1.0


def test_wilson_ci_zero_trials():
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_percentile_p50_p95():
    xs = [10, 20, 30, 40, 50]
    assert percentile(xs, 50) == 30
    assert percentile(xs, 0) == 10
    assert percentile(xs, 100) == 50
    assert abs(percentile(xs, 95) - 48) < 1e-9


def test_indistinguishable_overlap():
    assert indistinguishable((0.4, 0.7), (0.6, 0.9))
    assert not indistinguishable((0.1, 0.3), (0.6, 0.9))


def test_mcnemar_exact_known_values():
    assert mcnemar_exact(0, 0) == 1.0
    # b=5, c=0: two-sided exact binomial -> 2 * (1/2)^5 = 0.0625
    assert abs(mcnemar_exact(5, 0) - 0.0625) < 1e-9
    # Symmetric discordance is maximally insignificant.
    assert mcnemar_exact(3, 3) == 1.0
    # Big asymmetry is significant.
    assert mcnemar_exact(15, 1) < 0.001
    # Symmetric in its arguments.
    assert mcnemar_exact(2, 9) == mcnemar_exact(9, 2)


def test_bootstrap_ci_by_task():
    assert bootstrap_ci_by_task([]) == (0.0, 0.0)
    # Degenerate: identical fractions -> zero-width interval at that value.
    lo, hi = bootstrap_ci_by_task([1.0, 1.0, 1.0])
    assert lo == hi == 1.0
    # Mixed fractions -> interval containing the mean, wider than a point.
    lo, hi = bootstrap_ci_by_task([1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0])
    assert lo < 0.5 < hi
    # Deterministic for the same seed.
    assert bootstrap_ci_by_task([0.2, 0.8, 0.5]) == bootstrap_ci_by_task([0.2, 0.8, 0.5])


def test_bootstrap_ci_wider_than_pooled_wilson_when_tasks_cluster():
    # 10 tasks, 5 trials each, all-or-nothing per task (max clustering):
    # pooled Wilson sees 25/50 independent trials; the task bootstrap must not
    # pretend those 50 are independent.
    fracs = [1.0] * 5 + [0.0] * 5
    b_lo, b_hi = bootstrap_ci_by_task(fracs)
    w_lo, w_hi = wilson_ci(25, 50)
    assert (b_hi - b_lo) > (w_hi - w_lo)


# ── pro axes: calibration (Brier) + robustness (consistency) ──────────────────


def test_mean_brier():
    # score = 1 - brier; perfect (score 1.0) → brier 0, worst (score 0.0) → 1.
    assert mean_brier([1.0, 1.0]) == 0.0
    assert mean_brier([0.0, 0.0]) == 1.0
    assert abs(mean_brier([0.75, 0.75]) - 0.25) < 1e-9  # always-0.5 baseline
    assert mean_brier([]) == 1.0  # empty is maximally miscalibrated, not perfect


def test_consistency():
    # Agreement fraction (1 - flip rate).
    assert consistency([(True, True), (False, False)]) == 1.0   # never flips
    assert consistency([(True, False), (False, True)]) == 0.0   # always flips
    assert consistency([(True, True), (True, False)]) == 0.5
    assert consistency([]) == 1.0
