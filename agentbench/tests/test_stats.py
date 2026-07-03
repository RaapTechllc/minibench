from agentbench.stats import (
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
