import json
from pathlib import Path

import pytest

from agentbench.import_results import (
    ImportRefused,
    artifact_to_payload,
    derive_provider,
    load_trials,
    main,
)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def _legacy_trial(**overrides):
    base = {
        "task_id": "mb-reason-01",
        "category": "reasoning",
        "trial": 1,
        "passed": True,
        "score": 1.0,
        "cost_usd": 0.0001,
        "latency_ms": 2500,
        "tokens_in": 48,
        "tokens_out": 3,
        "detail": "got 134.0, expected 134.0",
    }
    base.update(overrides)
    return base


def _legacy_artifact(**summary_overrides):
    summary = {
        "suite": "minibench-core-v1",
        "moa_config": {
            "name": "single-claude-sonnet-5",
            "self_moa": False,
            "models": ["openrouter/anthropic/claude-sonnet-5"],
        },
        "n_tasks": 20,
        "n_trials": 3,
        "pass_rate": 0.9833,
        "pass_rate_ci95": [0.9114, 0.9971],
        "pass_hat_k": 0.95,
        "cost_usd_total": 0.04048,
        "cost_usd_per_task": 0.002024,
        "latency_p50_ms": 2889.5,
        "latency_p95_ms": 3609.6,
    }
    summary.update(summary_overrides)
    return {
        "generated_at": "2026-07-08T00:00:00+00:00",
        "dry_run": False,
        "summary": summary,
        "trials": [_legacy_trial(), _legacy_trial(trial=2)],
    }


def test_legacy_artifact_maps_to_submit_payload():
    payload = artifact_to_payload(_legacy_artifact(), source="x.json")

    assert payload["benchmark_suite"] == "minibench-core-v1"
    assert payload["provider"] == "openrouter"  # derived from the model string
    assert payload["pass_rate"] == pytest.approx(98.33)  # fraction → percent
    assert payload["ci95_low"] == pytest.approx(91.14)
    assert payload["pass_hat_k"] == pytest.approx(95.0)
    assert payload["latency_p50_ms"] == 2889
    # Legacy artifacts predate these fields: defaults, never guesses.
    assert payload["grader_version"] is None
    assert payload["n_infra_errors"] == 0
    assert payload["n_canary_flags"] == 0
    assert "seed_sha256" not in payload  # no provenance block → nothing forwarded
    assert len(payload["results"]) == 2
    assert payload["results"][0]["task_id"] == "mb-reason-01"


def test_load_trials_fills_grader_v3_defaults_and_drops_unknown_keys():
    trials = load_trials([_legacy_trial(some_future_field="ignored")])
    t = trials[0]
    assert t.infra_error is False and t.canary_flag is False
    assert t.passed_format is None and t.output_snippet == ""


def test_dry_run_artifact_refused_without_override():
    art = _legacy_artifact()
    art["dry_run"] = True
    with pytest.raises(ImportRefused, match="dry_run"):
        artifact_to_payload(art, source="x.json")


def test_canary_refused_from_summary_and_from_trials():
    with pytest.raises(ImportRefused, match="canary"):
        artifact_to_payload(
            _legacy_artifact(n_canary_flags=1), source="x.json"
        )
    art = _legacy_artifact()
    art["trials"][0]["canary_flag"] = True  # current-schema per-trial flag
    with pytest.raises(ImportRefused, match="canary"):
        artifact_to_payload(art, source="x.json")


def test_lying_summary_cannot_launder_flagged_trials():
    """Summary counters saying 0 must not override per-trial flags."""
    art = _legacy_artifact(n_canary_flags=0)
    art["trials"][0]["canary_flag"] = True
    with pytest.raises(ImportRefused, match="canary"):
        artifact_to_payload(art, source="x.json")

    art = _legacy_artifact(n_infra_errors=0)
    art["trials"][0]["infra_error"] = True
    with pytest.raises(ImportRefused, match="infra-error"):
        artifact_to_payload(art, source="x.json")


def test_infra_errors_refused_unless_allowed():
    art = _legacy_artifact(n_infra_errors=2)
    with pytest.raises(ImportRefused, match="infra-error"):
        artifact_to_payload(art, source="x.json")
    payload = artifact_to_payload(art, source="x.json", allow_infra_errors=True)
    assert payload["n_infra_errors"] == 2


def test_provider_ambiguity_refused_and_override_wins():
    art = _legacy_artifact(
        moa_config={
            "name": "mixed",
            "self_moa": False,
            "models": ["openrouter/a/b", "ollama/c"],
        }
    )
    with pytest.raises(ImportRefused, match="provider"):
        artifact_to_payload(art, source="x.json")
    payload = artifact_to_payload(art, source="x.json", provider="openrouter")
    assert payload["provider"] == "openrouter"


def test_derive_provider_single_prefix():
    assert derive_provider(_legacy_artifact()["summary"]) == "openrouter"


def test_provenance_forwarded_when_present():
    art = _legacy_artifact()
    art["provenance"] = {
        "seed_sha256": "a" * 64,
        "generator_sha256": None,  # nulls are dropped, not forwarded
        "git_commit": "deadbeef",
        "is_private_split": True,
        "unrelated": "dropped",
    }
    payload = artifact_to_payload(art, source="x.json")
    assert payload["seed_sha256"] == "a" * 64
    assert payload["git_commit"] == "deadbeef"
    assert payload["is_private_split"] is True
    assert "generator_sha256" not in payload
    assert "unrelated" not in payload


def test_main_check_validates_committed_artifacts(capsys):
    """Every committed live artifact must stay importable — this is the drift guard.

    Local dry-run artifacts (run.py writes one on every --dry-run) are ignored:
    they are untracked byproducts and the importer refuses them by design.
    """
    files = [
        p
        for p in sorted(RESULTS_DIR.glob("*.json"))
        if not json.loads(p.read_text(encoding="utf-8")).get("dry_run", False)
    ]
    assert files, "no committed live artifacts found"
    rc = main([str(p) for p in files] + ["--check"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"{len(files)} validated" in out


def test_main_requires_api_or_check(tmp_path, capsys):
    art = tmp_path / "a.json"
    art.write_text(json.dumps(_legacy_artifact()), encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(art)])


def test_main_check_refuses_dry_run_file(tmp_path, capsys):
    art_data = _legacy_artifact()
    art_data["dry_run"] = True
    art = tmp_path / "dry.json"
    art.write_text(json.dumps(art_data), encoding="utf-8")
    rc = main([str(art), "--check"])
    err = capsys.readouterr().err
    assert rc == 1  # nothing imported
    assert "REFUSED" in err and "dry_run" in err
