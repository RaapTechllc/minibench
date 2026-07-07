import pytest

from agentbench.compare import ComparabilityError, check_comparable, compare_pair
from agentbench.item_stats import audit, point_biserial


def _run(model: str, outcomes: dict[str, list[bool]], *, seed_hash: str = "abc",
         suite: str = "minibench-core-v1") -> dict:
    trials = [
        {"task_id": task, "trial": i + 1, "passed": p, "infra_error": False}
        for task, results in outcomes.items()
        for i, p in enumerate(results)
    ]
    n = len(trials)
    passes = sum(1 for t in trials if t["passed"])
    return {
        "dry_run": False,
        "provenance": {"seed_sha256": seed_hash},
        "summary": {
            "suite": suite,
            "grader_version": "2",
            "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
            "moa_config": {"name": f"single-{model}", "models": [model]},
            "pass_rate": round(passes / n, 4) if n else 0.0,
        },
        "trials": trials,
    }


def test_check_comparable_rejects_different_seeds():
    a = _run("a", {"t1": [True]}, seed_hash="abc")
    b = _run("b", {"t1": [True]}, seed_hash="zzz")
    with pytest.raises(ComparabilityError, match="seed"):
        check_comparable([a, b])


def test_check_comparable_rejects_different_grader_versions():
    a = _run("a", {"t1": [True]})
    b = _run("b", {"t1": [True]})
    b["summary"]["grader_version"] = "1"
    with pytest.raises(ComparabilityError, match="grader_version"):
        check_comparable([a, b])


def test_check_comparable_rejects_different_task_sets():
    a = _run("a", {"t1": [True]})
    b = _run("b", {"t2": [True]})
    with pytest.raises(ComparabilityError, match="task/trial"):
        check_comparable([a, b])


def test_compare_pair_indistinguishable_on_small_discordance():
    a = _run("a", {f"t{i}": [True] for i in range(10)})
    b = _run("b", {f"t{i}": [i != 0] for i in range(10)})  # b fails one task
    report = compare_pair(a, b)
    assert report["verdict"] == "indistinguishable"
    assert report["mcnemar_p"] > 0.05


def test_compare_pair_significant_on_large_discordance():
    # a passes everything; b fails 8 of 20 tasks -> b=8 discordant, c=0.
    a = _run("a", {f"t{i}": [True] for i in range(20)})
    b = _run("b", {f"t{i}": [i >= 8] for i in range(20)})
    report = compare_pair(a, b)
    assert report["verdict"] == "a > b"
    assert report["mcnemar_p"] < 0.05


def test_infra_trials_excluded_from_pairing():
    a = _run("a", {"t1": [True], "t2": [True]})
    b = _run("b", {"t1": [True], "t2": [False]})
    b["trials"][1]["infra_error"] = True  # t2 was infra for b, not a real fail
    report = compare_pair(a, b)
    assert report["discordant_a_wins"] == 0
    assert report["discordant_b_wins"] == 0


# ── item_stats ────────────────────────────────────────────────────────────────


def test_point_biserial_direction():
    # Item passed only by the stronger models -> positive correlation.
    assert point_biserial([1.0, 1.0, 0.0], [0.9, 0.8, 0.2]) > 0.5
    # Constant item -> zero.
    assert point_biserial([1.0, 1.0, 1.0], [0.9, 0.8, 0.2]) == 0.0


def test_audit_flags_ceiling_floor_and_low_discrimination():
    runs = [
        _run("strong", {"easy": [True], "hard": [True], "broken": [False]}),
        _run("mid", {"easy": [True], "hard": [False], "broken": [False]}),
        _run("weak", {"easy": [True], "hard": [False], "broken": [False]}),
    ]
    report = audit(runs)
    flags = {i["task_id"]: i["flags"] for i in report["items"]}
    assert flags["easy"] == ["ceiling"]
    assert flags["broken"] == ["floor"]
    assert flags["hard"] == []  # separates strong from the rest: keep
    assert set(report["prune_candidates"]) == {"easy", "broken"}


def test_audit_does_not_fabricate_zero_for_infra_excluded_task():
    # A model whose only trial on "hard" was infra-excluded is ABSENT for that
    # task, not a 0.0 — otherwise a provider rate-limit reads as a capability
    # floor and corrupts the item's discrimination stats.
    strong = _run("strong", {"easy": [True], "hard": [True]})
    mid = _run("mid", {"easy": [True], "hard": [True]})
    weak = _run("weak", {"easy": [True], "hard": [False]})
    # weak's "hard" trial was infra, not a real fail:
    weak["trials"][1]["infra_error"] = True
    report = audit(runs=[strong, mid, weak])
    hard = next(i for i in report["items"] if i["task_id"] == "hard")
    assert hard["n_models_scored"] == 2  # weak excluded, not counted as 0
    assert hard["mean_pass"] == 1.0      # would be 0.667 if fabricated to 0
    assert any(f.startswith("missing-") for f in hard["flags"])
