import json

import pytest

from agentbench.client import InfraError
from agentbench.config import load_moa_config, single_model_config
from agentbench.run import (
    StubModel,
    TrialResult,
    build_provenance,
    gold_self_check,
    run_suite,
    summarize,
    load_tasks,
    main,
    to_agent_run_submit,
)
from agentbench.resources import MOA_V1, CODING_V1


def test_dry_run_end_to_end_passes_seed_tasks():
    config = load_moa_config(MOA_V1)
    suite, tasks = load_tasks(CODING_V1)
    results = run_suite(config, tasks, trials=3, model=None, stub=StubModel())

    # 4 tasks x 3 trials.
    assert len(results) == 12
    # The stub answers satisfy every seed oracle, so all trials pass.
    assert all(r.passed for r in results)

    summary = summarize(config, suite, 3, results)
    assert summary["n_tasks"] == 4
    assert summary["n_trials"] == 3
    assert summary["pass_rate"] == 1.0
    assert summary["pass_hat_k"] == 1.0
    assert summary["latency_p95_ms"] == 0.0  # stub is instantaneous


def test_cli_dry_run_writes_artifact(tmp_path):
    out = tmp_path / "result.json"
    rc = main([
        "--config", MOA_V1,
        "--tasks", CODING_V1,
        "--trials", "2",
        "--dry-run",
        "--out", str(out),
    ])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["dry_run"] is True
    assert payload["summary"]["pass_rate"] == 1.0
    assert len(payload["trials"]) == 8  # 4 tasks x 2 trials


def test_to_agent_run_submit_scales_percentages():
    config = load_moa_config(MOA_V1)
    suite, tasks = load_tasks(CODING_V1)
    results = run_suite(config, tasks, trials=2, model=None, stub=StubModel())
    summary = summarize(config, suite, 2, results)
    payload = to_agent_run_submit(summary, results, provider="openrouter")

    assert payload["benchmark_suite"] == suite
    assert payload["pass_rate"] == 100.0
    assert payload["pass_hat_k"] == 100.0
    assert payload["ci95_low"] is not None
    assert len(payload["results"]) == len(results)


def test_live_run_without_key_errors_cleanly(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    rc = main([
        "--config", MOA_V1,
        "--tasks", CODING_V1,
        "--provider", "openrouter",
    ])
    assert rc == 2  # refuses to pretend; tells the user to use --dry-run


# ── infra-error accounting ────────────────────────────────────────────────────


class _FlakyModel:
    """Raises InfraError on the first call, then answers correctly."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        from agentbench.moa import MoAResult

        self.calls += 1
        if self.calls == 1:
            raise InfraError("rate limited", status=429, attempts=5)
        return MoAResult(text="42", cost_usd=0.0, prompt_tokens=1,
                         completion_tokens=1, latency_ms=1, n_calls=1)


def _numeric_task(expected=42):
    return {"id": "t1", "category": "reasoning", "prompt": "6*7?",
            "verification": {"type": "numeric_match", "expected": expected}}


def test_infra_errors_recorded_and_excluded_from_denominators():
    config = single_model_config("openrouter/x/y")
    results = run_suite(config, [_numeric_task()], trials=3, model=_FlakyModel())
    assert len(results) == 3
    assert results[0].infra_error and not results[0].passed
    summary = summarize(config, "s", 3, results)
    assert summary["n_infra_errors"] == 1
    # 2 scored trials, both passed — the infra trial must not dilute the rate.
    assert summary["pass_rate"] == 1.0
    assert summary["pass_hat_k"] == 1.0


def test_canary_echo_flagged():
    class _Contaminated:
        def generate(self, prompt):
            from agentbench.moa import MoAResult

            return MoAResult(text="AGENTBENCH-CANARY-4d9e7b1a-DO-NOT-TRAIN 42",
                             cost_usd=0.0, prompt_tokens=1, completion_tokens=1,
                             latency_ms=1, n_calls=1)

    config = single_model_config("openrouter/x/y")
    results = run_suite(config, [_numeric_task()], trials=1, model=_Contaminated())
    assert results[0].canary_flag
    assert summarize(config, "s", 1, results)["n_canary_flags"] == 1


def test_publish_refused_on_infra_errors(monkeypatch, tmp_path):
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.setattr("agentbench.run.run_suite", lambda *a, **k: [
        TrialResult("t1", "reasoning", 1, False, 0.0, None, 0, 0, 0,
                    "infra: 429", infra_error=True),
    ])
    published = []
    monkeypatch.setattr("agentbench.run.publish_run", lambda url, p: published.append(p) or {})
    rc = main(["--model", "openrouter/x/y", "--tasks", CODING_V1, "--dry-run",
               "--out", str(tmp_path / "r.json"), "--publish", "http://api"])
    assert rc == 3
    assert not published


def test_publish_refused_on_canary_flags(monkeypatch, tmp_path):
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.setattr("agentbench.run.run_suite", lambda *a, **k: [
        TrialResult("t1", "reasoning", 1, True, 1.0, None, 0, 0, 0,
                    "match", canary_flag=True),
    ])
    published = []
    monkeypatch.setattr("agentbench.run.publish_run", lambda url, p: published.append(p) or {})
    rc = main(["--model", "openrouter/x/y", "--tasks", CODING_V1, "--dry-run",
               "--out", str(tmp_path / "r.json"), "--publish", "http://api"])
    assert rc == 3
    assert not published


# ── private-seed --generate protocol ──────────────────────────────────────────


def test_generate_requires_env_seed(monkeypatch, tmp_path):
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.delenv("MINIBENCH_SEED", raising=False)
    rc = main(["--model", "openrouter/x/y", "--generate", "core", "--dry-run",
               "--out", str(tmp_path / "r.json")])
    assert rc == 2


def test_generate_runs_gold_self_check_and_records_provenance(monkeypatch, tmp_path):
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.setenv("MINIBENCH_SEED", "987654321")
    out = tmp_path / "r.json"
    rc = main(["--model", "openrouter/x/y", "--generate", "core", "--trials", "1",
               "--dry-run", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    prov = payload["provenance"]
    import hashlib

    assert prov["seed_sha256"] == hashlib.sha256(b"987654321").hexdigest()
    assert prov["is_private_split"] is True
    assert prov["generator_sha256"]
    assert payload["summary"]["grader_version"] == "2"
    assert payload["summary"]["decoding"]["temperature"] == 0.0
    assert payload["summary"]["decoding"]["top_p"] == 1.0
    # The raw seed must never appear anywhere in the artifact.
    assert "987654321" not in out.read_text()


def test_gold_self_check_catches_poisoned_spec():
    poisoned = [{"id": "bad", "category": "reasoning", "prompt": "?",
                 "verification": {"type": "numeric_match", "expected": 1},
                 "_gold": "2"}]
    assert gold_self_check(poisoned) == ["bad"]


def test_minibench_suite_rejects_moa_configs(monkeypatch, tmp_path):
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.setenv("MINIBENCH_SEED", "11")
    rc = main(["--config", MOA_V1, "--generate", "core", "--dry-run",
               "--out", str(tmp_path / "r.json")])
    assert rc == 2  # MoA/system-prompt configs are not comparable on minibench


def test_provenance_seed_hash_none_without_seed():
    prov = build_provenance(seed=None, is_private_split=False)
    assert prov["seed_sha256"] is None
    assert prov["is_private_split"] is False


def test_private_split_redacts_gold_from_trial_detail(monkeypatch, tmp_path):
    # Grader detail embeds the gold ("got X, expected Y") even on passing
    # numeric trials; a committed private-split artifact must not leak it.
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    monkeypatch.setenv("MINIBENCH_SEED", "112233445566")
    out = tmp_path / "r.json"
    rc = main(["--model", "openrouter/x/y", "--generate", "core", "--trials", "1",
               "--dry-run", "--out", str(out)])
    assert rc == 0
    text = out.read_text()
    assert "expected" not in text  # no "got N, expected M" leak
    for t in json.loads(text)["trials"]:
        assert t["detail"] in {"pass", "fail", "infra"}


# ── pro axes surfacing (calibration + robustness) ─────────────────────────────


def _pro_trial(task_id, category, trial, passed, score=None):
    return TrialResult(task_id, category, trial, passed,
                       score if score is not None else (1.0 if passed else 0.0),
                       0.0, 1, 1, 1, "d")


def test_summary_calibration_and_robustness_axes():
    config = single_model_config("openrouter/x/y")
    results = [
        # two binary reasoning trials
        _pro_trial("mbp-count-01", "counting", 1, True),
        _pro_trial("mbp-count-01", "counting", 2, True),
        # calibration: score = 1 - brier (0.75 → brier 0.25)
        _pro_trial("mbp-calib-01", "calibration", 1, False, score=0.75),
        _pro_trial("mbp-calib-01", "calibration", 2, False, score=0.75),
        # robustness pair: base right, pert wrong on trial 1 → a flip
        _pro_trial("mbp-robust-01-base", "robustness", 1, True),
        _pro_trial("mbp-robust-01-pert", "robustness", 1, False),
    ]
    s = summarize(config, "minibench-pro-v1", 2, results)
    # Calibration AND robustness are excluded from the binary pool: pass_rate is
    # over the counting items only (2/2 pass = 1.0).
    assert s["pass_rate"] == 1.0
    assert s["calibration_brier"] == 0.25
    assert s["n_calibration_trials"] == 2
    # Robustness axis: the single pair-trial flipped (base pass, pert fail).
    assert s["robustness_correct"] == 0.0        # not both-correct → primary axis 0
    assert s["robustness_consistency"] == 0.0    # flipped → diagnostic 0
    assert s["n_robust_pairs"] == 1


def test_robustness_correct_not_gamed_by_uniform_wrongness():
    # A model that answers every robustness prompt with the same WRONG value gets
    # perfect bare consistency (both-wrong agrees) but robustness_correct 0 — the
    # published headline must expose it, not reward it.
    config = single_model_config("openrouter/x/y")
    results = [
        _pro_trial("mbp-robust-01-base", "robustness", 1, False),
        _pro_trial("mbp-robust-01-pert", "robustness", 1, False),
        _pro_trial("mbp-robust-02-base", "robustness", 1, False),
        _pro_trial("mbp-robust-02-pert", "robustness", 1, False),
    ]
    s = summarize(config, "minibench-pro-v1", 1, results)
    assert s["robustness_consistency"] == 1.0  # both-wrong "agrees" (diagnostic)
    assert s["robustness_correct"] == 0.0      # but nothing is correct (headline)


def test_core_summary_has_no_pro_axes():
    config = single_model_config("openrouter/x/y")
    results = [_pro_trial("mb-reason-01", "reasoning", 1, True)]
    s = summarize(config, "minibench-core-v1", 1, results)
    assert "calibration_brier" not in s
    assert "robustness_consistency" not in s
    assert "robustness_correct" not in s
