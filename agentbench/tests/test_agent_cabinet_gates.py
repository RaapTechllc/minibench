"""Offline unit tests for Agent Cabinet provenance, reliability, and gates.

No Docker, no live keys, no scrape. Publication tests use in-memory
``dry_run is False`` copies; the writer still emits ``dry_run: true``.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.agent_cabinet import (
    AGENT_CABINET_POLICY,
    COMPARABILITY_FIELDS,
    PUBLICATION_REFUSE_REASONS,
    PUBLISH_REFUSE_CANARY_FLAGS,
    PUBLISH_REFUSE_DRY_RUN,
    PUBLISH_REFUSE_INCOMPLETE_DISPOSAL,
    PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS,
    PUBLISH_REFUSE_INVALID_SELF_CHECK,
    PUBLISH_REFUSE_MISSING_PROVENANCE,
    PUBLISH_REFUSE_MUTABLE_FIXTURE,
    PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH,
    RELIABILITY_SUMMARY_FIELDS,
    REQUIRED_PROVENANCE_KEYS,
    comparability_receipt,
    is_agent_cabinet_artifact,
    publication_receipt,
    reliability_summary_fields,
    sanitize_agent_provenance,
)
from agentbench.agent_tasks import (
    DeterministicFakeAgent,
    OfflineTextEnvironment,
    build_agent_artifact,
    load_agent_manifest,
    run_agent_trial,
)
from agentbench.compare import ComparabilityError, check_comparable
from agentbench.import_results import ImportRefused, artifact_to_payload
from agentbench.tests.test_compare import _run


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "tasks" / "minibench-agent-v1-offline.json"
)


def _offline_artifact(tmp_path: Path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    trial = run_agent_trial(
        manifest,
        OfflineTextEnvironment(tmp_path),
        DeterministicFakeAgent(),
        trial=1,
    )
    return manifest, trial, build_agent_artifact(manifest, [trial])


def _publishable(artifact: dict) -> dict:
    copy = deepcopy(artifact)
    copy["dry_run"] = False
    if not copy["provenance"].get("git_commit"):
        copy["provenance"]["git_commit"] = "a" * 40
    return copy


def _importable(artifact: dict) -> dict:
    copy = _publishable(artifact)
    for trial in copy["trials"]:
        trial.setdefault("score", 1.0 if trial.get("passed") else 0.0)
        trial.setdefault("latency_ms", trial.get("wall_time_ms") or 0)
        trial.setdefault("detail", "pass" if trial.get("passed") else "fail")
    return copy


def test_policy_constant_and_required_key_set():
    assert AGENT_CABINET_POLICY == "agent-cabinet-gates-v1"
    assert REQUIRED_PROVENANCE_KEYS == (
        "model",
        "provider",
        "model_route",
        "harness",
        "harness_version",
        "tool_contract",
        "tool_contract_sha256",
        "prompt_config_sha256",
        "fixture_reference",
        "fixture_digest",
        "generator_sha256",
        "suite",
        "task_set_sha256",
        "budgets",
        "git_commit",
        "grader_version",
        "private_split",
        "private_split_id",
        "policy_version",
    )
    assert set(PUBLICATION_REFUSE_REASONS) == {
        PUBLISH_REFUSE_DRY_RUN,
        PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS,
        PUBLISH_REFUSE_CANARY_FLAGS,
        PUBLISH_REFUSE_MUTABLE_FIXTURE,
        PUBLISH_REFUSE_MISSING_PROVENANCE,
        PUBLISH_REFUSE_INCOMPLETE_DISPOSAL,
        PUBLISH_REFUSE_INVALID_SELF_CHECK,
        PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH,
    }


def test_build_agent_artifact_emits_required_provenance_and_reliability(tmp_path):
    manifest, _trial, artifact = _offline_artifact(tmp_path / "work")

    assert artifact["dry_run"] is True
    assert artifact["provenance"]["policy_version"] == AGENT_CABINET_POLICY
    assert set(REQUIRED_PROVENANCE_KEYS) <= set(artifact["provenance"])
    assert set(RELIABILITY_SUMMARY_FIELDS) <= set(artifact["summary"])
    assert artifact["provenance"]["model"] == "deterministic-fake-agent"
    assert artifact["provenance"]["provider"] == "offline"
    assert artifact["provenance"]["model_route"] == "offline/deterministic-fake-agent"
    assert artifact["provenance"]["suite"] == manifest.suite
    assert artifact["provenance"]["fixture_reference"] == manifest.fixture.reference
    assert artifact["provenance"]["fixture_digest"] == manifest.fixture.digest
    assert artifact["provenance"]["generator_sha256"]
    assert artifact["provenance"]["private_split"] is False
    assert artifact["summary"]["pass_rate"] == 1.0
    assert artifact["summary"]["pass_hat_k"] == 1.0
    assert artifact["summary"]["pass_rate_ci95"]
    assert artifact["summary"]["regression_rate"] is None
    assert artifact["summary"]["false_verification_rate"] == 0.0
    assert artifact["summary"]["termination_reasons"]["completed"] == 1
    encoded = str(tmp_path)
    assert encoded not in str(artifact)


def test_sanitize_drops_gold_hidden_tests_seed_and_workspace_paths():
    cleaned = sanitize_agent_provenance(
        {
            "model": "keep",
            "gold": "SECRET_PATCH",
            "hidden_tests": ["assert False"],
            "private_rows": [{"id": 1}],
            "seed": 987654321,
            "MINIBENCH_SEED": "123",
            "workspace": "/tmp/agent-workspace",
            "nested": {"probe": "do-not-leak", "harness": "ok"},
        }
    )
    assert cleaned == {"model": "keep", "nested": {"harness": "ok"}}


@pytest.mark.parametrize(
    "outcome, claimed, expected",
    [
        ("verification_failed", True, 1.0),
        ("verification_failed", False, 0.0),
        ("timeout", True, 0.0),
        ("success", True, 0.0),
    ],
)
def test_false_verification_is_claim_and_oracle_fail_only(outcome, claimed, expected):
    fields = reliability_summary_fields(
        [
            {
                "outcome": outcome,
                "passed": outcome == "success",
                "agent_claimed_success": claimed,
                "termination_reason": "completed",
            }
        ]
    )
    assert fields["false_verification_rate"] == expected


def test_regression_rate_is_null_unless_structured():
    unstructured = reliability_summary_fields(
        [{"outcome": "verification_failed", "passed": False, "termination_reason": "completed"}]
    )
    structured = reliability_summary_fields(
        [
            {
                "outcome": "verification_failed",
                "passed": False,
                "termination_reason": "completed",
                "introduced_regression": True,
            },
            {
                "outcome": "success",
                "passed": True,
                "termination_reason": "completed",
                "introduced_regression": False,
            },
        ]
    )
    assert unstructured["regression_rate"] is None
    assert structured["regression_rate"] == 0.5


def test_infra_trials_excluded_from_false_verification_rate(tmp_path):
    manifest, passed, _artifact = _offline_artifact(tmp_path / "work")
    infra = replace(
        passed,
        trial=2,
        outcome="preparation_failed",
        passed=False,
        agent_claimed_success=True,
        detail="environment preparation failed",
    )
    claimed_fail = replace(
        passed,
        trial=3,
        outcome="verification_failed",
        passed=False,
        agent_claimed_success=True,
        detail="fail",
    )
    summary = build_agent_artifact(manifest, [passed, infra, claimed_fail])["summary"]
    assert summary["n_infra_errors"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["false_verification_rate"] == 0.5
    assert summary["regression_rate"] is None


def test_comparability_accepts_matching_agent_runs(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    receipt = comparability_receipt(left, right)
    assert receipt["policy_version"] == AGENT_CABINET_POLICY
    assert receipt["comparable"] is True
    assert receipt["failing_fields"] == []
    assert receipt["reasons"] == []
    check_comparable([left, right])


def test_comparability_rejects_generator_or_oracle_source_change(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    right["provenance"]["generator_sha256"] = "0" * 64

    receipt = comparability_receipt(left, right)

    assert receipt["comparable"] is False
    assert "generator_sha256" in receipt["failing_fields"]
    assert "generator_mismatch" in receipt["reasons"]


def test_comparability_rejects_suite_change_even_with_forged_task_set_hash(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    right["provenance"]["suite"] = "different-suite"

    receipt = comparability_receipt(left, right)

    assert receipt["comparable"] is False
    assert "suite" in receipt["failing_fields"]
    assert "suite_mismatch" in receipt["reasons"]


@pytest.mark.parametrize("field", COMPARABILITY_FIELDS)
def test_comparability_rejects_each_incompatibility(tmp_path, field):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    if field == "budgets":
        right["provenance"]["budgets"] = {**right["provenance"]["budgets"], "max_turns": 99}
    elif field == "fixture_reference":
        right["provenance"]["fixture_reference"] = "offline-text-repair@9"
    elif field == "fixture_digest":
        right["provenance"]["fixture_digest"] = "sha256:" + "ab" * 32
    elif isinstance(right["provenance"].get(field), bool):
        right["provenance"][field] = not right["provenance"][field]
    else:
        right["provenance"][field] = f"mutated-{field}"

    receipt = comparability_receipt(left, right)
    assert receipt["comparable"] is False
    assert field in receipt["failing_fields"]
    assert receipt["reasons"]
    # Pairing mismatch must not publish-refuse either run.
    assert publication_receipt(left)["publishable"] is True
    assert publication_receipt(right)["publishable"] is True


def test_publication_refuses_dry_run_and_accepts_in_memory_copy(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    dry = publication_receipt(artifact)
    live = publication_receipt(_publishable(artifact))
    assert dry["publishable"] is False
    assert PUBLISH_REFUSE_DRY_RUN in dry["reasons"]
    assert live["publishable"] is True
    assert live["reasons"] == []


@pytest.mark.parametrize(
    "mutate, reason",
    [
        (
            lambda art: art["summary"].__setitem__("n_infra_errors", 1)
            or art["trials"][0].__setitem__("outcome", "preparation_failed"),
            PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS,
        ),
        (
            lambda art: art["summary"].__setitem__("n_canary_flags", 1)
            or art["trials"][0].__setitem__("canary_flag", True),
            PUBLISH_REFUSE_CANARY_FLAGS,
        ),
        (
            lambda art: art["provenance"].__setitem__("fixture_reference", "offline-text-repair@latest"),
            PUBLISH_REFUSE_MUTABLE_FIXTURE,
        ),
        (
            lambda art: art["provenance"].pop("generator_sha256"),
            PUBLISH_REFUSE_MISSING_PROVENANCE,
        ),
        (
            lambda art: art["trials"][0].__setitem__("workspace_disposed", False),
            PUBLISH_REFUSE_INCOMPLETE_DISPOSAL,
        ),
        (
            lambda art: art["provenance"].__setitem__("self_check", "failed"),
            PUBLISH_REFUSE_INVALID_SELF_CHECK,
        ),
        (
            # Claimed pass_rate stays 1.0 while the only trial actually failed.
            lambda art: art["trials"][0].__setitem__("passed", False),
            PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH,
        ),
        (
            # A summary with no trials behind it cannot support any score.
            lambda art: art.__setitem__("trials", []),
            PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH,
        ),
        (
            # n_trials must match the recorded trial count.
            lambda art: art["summary"].__setitem__("n_trials", 5),
            PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH,
        ),
    ],
)
def test_publication_refuses_each_named_reason(tmp_path, mutate, reason):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    copy = _publishable(artifact)
    mutate(copy)
    receipt = publication_receipt(copy)
    assert receipt["publishable"] is False
    assert reason in receipt["reasons"]
    assert receipt["policy_version"] == AGENT_CABINET_POLICY


@pytest.mark.parametrize("bad_key", [(None, 1), ("task", None)])
def test_duplicate_or_null_trial_keys_fail_publication_and_comparison(tmp_path, bad_key):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    valid = _publishable(artifact)
    invalid = deepcopy(valid)
    invalid["trials"][0]["task_id"], invalid["trials"][0]["trial"] = bad_key

    publication = publication_receipt(invalid)
    comparison = comparability_receipt(invalid, deepcopy(invalid))

    assert publication["publishable"] is False
    assert PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH in publication["reasons"]
    assert comparison["comparable"] is False
    assert "invalid_trial_keys" in comparison["reasons"]


def test_duplicate_trial_keys_fail_publication_and_comparison(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    valid = _publishable(artifact)
    invalid = deepcopy(valid)
    invalid["trials"].append(deepcopy(invalid["trials"][0]))
    invalid["summary"]["n_trials"] = 2

    publication = publication_receipt(invalid)
    comparison = comparability_receipt(invalid, deepcopy(invalid))

    assert publication["publishable"] is False
    assert PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH in publication["reasons"]
    assert comparison["comparable"] is False
    assert "invalid_trial_keys" in comparison["reasons"]


def test_valid_unique_trial_keys_remain_publishable_and_comparable(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    valid = _publishable(artifact)

    assert publication_receipt(valid)["publishable"] is True
    assert comparability_receipt(valid, deepcopy(valid))["comparable"] is True


def test_multi_task_artifact_uses_trials_per_task_and_remains_publishable(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    valid = _publishable(artifact)
    second = deepcopy(valid["trials"][0])
    second["task_id"] = "second-task"
    valid["trials"].append(second)
    valid["summary"].update(
        {
            "n_tasks": 2,
            "n_trials": 1,
            "pass_hat_k_effective_k": 1,
            "pass_rate_ci95": [0.3424, 1.0],
            "termination_reasons": {"completed": 2},
        }
    )

    assert publication_receipt(valid)["publishable"] is True


def test_publication_refuses_missing_n_trials(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    invalid = _publishable(artifact)
    invalid["summary"].pop("n_trials")

    receipt = publication_receipt(invalid)

    assert receipt["publishable"] is False
    assert PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH in receipt["reasons"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("n_tasks", 2),
        ("n_tasks", True),
        ("pass_rate", 0.0),
        ("pass_hat_k_effective_k", 2),
        ("pass_hat_k_effective_k", True),
        ("pass_hat_k", 0.0),
        ("pass_rate_ci95", [0.0, 0.0]),
        ("pass_rate_ci95_boot", [0.0, 0.0]),
        ("false_verification_rate", 1.0),
        ("regression_rate", 1.0),
        ("termination_reasons", {"fabricated": 1}),
        ("cost_usd_total", 999.0),
        ("cost_usd_per_task", 999.0),
        ("latency_p50_ms", 999.0),
        ("latency_p95_ms", 999.0),
    ],
)
def test_publication_refuses_each_inconsistent_trial_derived_summary(
    tmp_path, field, replacement
):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    invalid = _publishable(artifact)
    invalid["summary"][field] = replacement

    receipt = publication_receipt(invalid)

    assert receipt["publishable"] is False
    assert PUBLISH_REFUSE_SUMMARY_TRIALS_MISMATCH in receipt["reasons"]


def test_comparability_rejects_mismatched_trial_sets(tmp_path):
    """Different --trials values must refuse at the receipt, not silently
    intersect inside compare_pair (McNemar assumes matched samples)."""
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    extra = deepcopy(right["trials"][0])
    extra["trial"] = 2
    right["trials"].append(extra)
    receipt = comparability_receipt(left, right)
    assert receipt["comparable"] is False
    assert "trials" in receipt["failing_fields"]
    assert "trial_set_mismatch" in receipt["reasons"]


def test_comparability_rejects_mismatched_mcnemar_eligible_trial_sets(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    right["trials"][0]["category"] = "calibration"

    assert publication_receipt(left)["publishable"] is True
    assert publication_receipt(right)["publishable"] is True
    receipt = comparability_receipt(left, right)

    assert receipt["comparable"] is False
    assert "trials" in receipt["failing_fields"]
    assert "trial_set_mismatch" in receipt["reasons"]


def test_comparability_rejects_vacuous_axis_only_pair(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    left["trials"][0]["category"] = "robustness"
    right = deepcopy(left)

    assert publication_receipt(left)["publishable"] is True
    receipt = comparability_receipt(left, right)

    assert receipt["comparable"] is False
    assert "trials" in receipt["failing_fields"]
    assert "no_matched_trials" in receipt["reasons"]


def test_publication_does_not_refuse_for_comparability_mismatch_alone(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    left = _publishable(artifact)
    right = deepcopy(left)
    right["provenance"]["task_set_sha256"] = "0" * 64
    assert comparability_receipt(left, right)["comparable"] is False
    assert publication_receipt(left)["publishable"] is True
    assert publication_receipt(right)["publishable"] is True


def test_solo_and_moa_remain_comparable_under_existing_rules():
    a = _run("a", {"t1": [True, True]})
    b = _run("b", {"t1": [True, False]})
    check_comparable([a, b])
    assert is_agent_cabinet_artifact(a) is False


def test_mixed_agent_and_solo_are_not_comparable(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    agent = _publishable(artifact)
    solo = _run("solo", {agent["trials"][0]["task_id"]: [True]})
    solo["summary"]["suite"] = agent["summary"]["suite"]
    solo["summary"]["grader_version"] = agent["summary"]["grader_version"]
    solo["summary"]["decoding"] = agent["summary"]["decoding"]
    solo["provenance"]["seed_sha256"] = (agent.get("provenance") or {}).get("seed_sha256")
    with pytest.raises(ComparabilityError, match="evaluation_type"):
        check_comparable([solo, agent])


def test_import_results_forwards_new_provenance_keys_when_present():
    from agentbench.tests.test_import_results import _legacy_artifact

    art = _legacy_artifact()
    art["provenance"] = {
        "seed_sha256": "a" * 64,
        "tool_contract_sha256": "b" * 64,
        "private_split_id": "c" * 64,
        "model_route": "offline/fake",
        "unrelated": "dropped",
    }
    payload = artifact_to_payload(art, source="x.json")
    assert payload["seed_sha256"] == "a" * 64
    assert payload["tool_contract_sha256"] == "b" * 64
    assert payload["private_split_id"] == "c" * 64
    assert payload["model_route"] == "offline/fake"
    assert "unrelated" not in payload
    assert "pass_rate" in payload


def test_import_results_refuses_agent_infra_without_allow_infra_override(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    art = _importable(artifact)
    art["summary"]["n_infra_errors"] = 1
    art["trials"][0]["outcome"] = "preparation_failed"
    art["trials"][0]["infra_error"] = True
    with pytest.raises(ImportRefused, match="infrastructure_errors"):
        artifact_to_payload(art, source="agent.json", provider="offline")
    with pytest.raises(ImportRefused, match="infrastructure_errors"):
        artifact_to_payload(
            art, source="agent.json", provider="offline", allow_infra_errors=True
        )


def test_import_results_check_prints_cabinet_destination(tmp_path, capsys):
    from agentbench.import_results import CABINET_DESTINATION, import_destination, main

    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    art = _importable(artifact)
    path = tmp_path / "cabinet.json"
    path.write_text(json.dumps(art), encoding="utf-8")
    assert import_destination(art) == CABINET_DESTINATION
    rc = main([str(path), "--check"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"destination={CABINET_DESTINATION}" in out


def test_import_results_allow_infra_still_ignored_on_cabinet_prepare(tmp_path):
    from agentbench.import_results import prepare_cabinet_artifact

    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    art = _importable(artifact)
    art["summary"]["n_infra_errors"] = 1
    art["trials"][0]["outcome"] = "preparation_failed"
    art["trials"][0]["infra_error"] = True
    with pytest.raises(ImportRefused, match="infrastructure_errors"):
        prepare_cabinet_artifact(art, source="agent.json")


def test_import_results_accepts_publishable_in_memory_agent_copy(tmp_path):
    _manifest, _trial, artifact = _offline_artifact(tmp_path)
    payload = artifact_to_payload(
        _importable(artifact), source="agent.json", provider="offline"
    )
    assert payload["benchmark_suite"] == "minibench-agent-v1"
    assert payload["policy_version"] == AGENT_CABINET_POLICY
    assert payload["generator_sha256"]
    assert payload["pass_rate"] == pytest.approx(100.0)
