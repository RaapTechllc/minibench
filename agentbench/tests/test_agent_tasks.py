import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.config import single_model_config
from agentbench.agent_tasks import (
    AgentBudget,
    AgentBudgetGuard,
    AgentResult,
    AgentTaskManifest,
    DeterministicFakeAgent,
    OfflineTextEnvironment,
    load_agent_manifest,
    main,
    run_agent_trial,
    write_agent_artifact,
    build_agent_artifact,
)
from agentbench.run import TrialResult, summarize


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "tasks" / "minibench-agent-v1-offline.json"
)


def test_manifest_loads_versioned_offline_task():
    manifest = load_agent_manifest(MANIFEST_PATH)

    assert manifest.manifest_version == "1"
    assert manifest.task_id == "mba-offline-text-repair-001"
    assert manifest.fixture.reference == "offline-text-repair@1"
    assert manifest.fixture.digest.startswith("sha256:")
    assert manifest.preparation.strategy == "offline-text-repair-v1"
    assert manifest.verification.strategy == "offline-text-repair-v1"
    assert manifest.required_capabilities == ("filesystem",)
    assert manifest.budget == AgentBudget(
        max_turns=1, wall_time_seconds=5, max_tokens=100, max_cost_usd=0.0
    )


@pytest.mark.parametrize(
    "change, message",
    [
        ({"task_id": ""}, "task_id"),
        ({"category": ""}, "category"),
        ({"public_prompt": ""}, "public_prompt"),
        ({"required_capabilities": []}, "required_capabilities"),
        ({"fixture": {"reference": "latest", "digest": "sha256:abc"}}, "reference"),
        ({"fixture": {"reference": "fixture@1", "digest": "latest"}}, "digest"),
        ({"verification": {"strategy": ""}}, "verification"),
        ({"preparation": {"strategy": ""}}, "preparation"),
        ({"budget": {"max_turns": 0, "wall_time_seconds": 5}}, "max_turns"),
        (
            {"budget": {"max_turns": 1, "wall_time_seconds": 5, "max_tokens": -1, "max_cost_usd": 0}},
            "max_tokens",
        ),
    ],
)
def test_manifest_rejects_missing_or_mutable_contract_fields(change, message):
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw.update(change)

    with pytest.raises(ValueError, match=message):
        AgentTaskManifest.from_dict(raw)


def test_offline_trial_succeeds_and_disposes_workspace(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    environment = OfflineTextEnvironment(tmp_path)

    trial = run_agent_trial(manifest, environment, DeterministicFakeAgent(), trial=1)

    assert trial.outcome == "success"
    assert trial.passed is True
    assert trial.agent_claimed_success is True
    assert trial.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_verifier_ignores_agent_success_claim_and_disposes(tmp_path):
    class ClaimOnlyAgent:
        def execute(self, prompt, workspace, budget):
            return AgentResult(termination_reason="completed", claimed_success=True)

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        ClaimOnlyAgent(),
        trial=1,
    )

    assert trial.outcome == "verification_failed"
    assert trial.passed is False
    assert trial.agent_claimed_success is True
    assert trial.workspace_disposed is True
    assert "READY" not in trial.detail
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "agent, expected_outcome",
    [
        (lambda: (_ for _ in ()).throw(TimeoutError("budget exceeded")), "timeout"),
        (lambda: {"claimed_success": True}, "malformed_agent_result"),
    ],
)
def test_terminal_agent_failures_are_explicit_and_disposed(tmp_path, agent, expected_outcome):
    class ScriptedAgent:
        def execute(self, prompt, workspace, budget):
            return agent()

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        ScriptedAgent(),
        trial=1,
    )

    assert trial.outcome == expected_outcome
    assert trial.passed is False
    assert trial.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_agent_result_over_turn_budget_is_timeout(tmp_path):
    class OverBudgetAgent:
        def execute(self, prompt, workspace, budget):
            return AgentResult(termination_reason="completed", turns=budget.max_turns + 1)

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        OverBudgetAgent(),
        trial=1,
    )

    assert trial.outcome == "timeout"
    assert trial.workspace_disposed is True


def test_harness_terminates_agent_at_wall_time_budget(tmp_path):
    class SlowAgent:
        def execute(self, prompt, workspace, budget):
            time.sleep(2)
            return AgentResult(termination_reason="completed")

    manifest = load_agent_manifest(MANIFEST_PATH)
    manifest = replace(manifest, budget=replace(manifest.budget, wall_time_seconds=1))

    started = time.monotonic()
    trial = run_agent_trial(
        manifest, OfflineTextEnvironment(tmp_path), SlowAgent(), trial=1
    )

    assert trial.outcome == "timeout"
    assert time.monotonic() - started < 1.8
    assert trial.workspace_disposed is True


def test_invalid_agent_result_is_malformed_even_if_fixture_was_repaired(tmp_path):
    class InvalidAgent:
        def execute(self, prompt, workspace, budget):
            (workspace / "service.conf").write_text("status=READY\n", encoding="utf-8")
            return AgentResult(termination_reason="", turns=-1, claimed_success=True)

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        InvalidAgent(),
        trial=1,
    )

    assert trial.outcome == "malformed_agent_result"
    assert trial.passed is False


@pytest.mark.parametrize(
    "invalid",
    [
        AgentResult(termination_reason=None),
        AgentResult(termination_reason="completed", turns="1"),
        AgentResult(termination_reason="completed", tokens_in="x"),
        AgentResult(termination_reason="completed", cost_usd="free"),
        AgentResult(termination_reason="completed", claimed_success=1),
    ],
)
def test_malformed_agent_result_types_are_classified_explicitly(tmp_path, invalid):
    class InvalidAgent:
        def execute(self, prompt, workspace, budget):
            return invalid

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        InvalidAgent(),
        trial=1,
    )

    assert trial.outcome == "malformed_agent_result"


@pytest.mark.parametrize(
    "usage",
    [
        {"turns": 2},
        {"tokens": 101},
        {"cost_usd": 0.01},
    ],
)
def test_adapter_budget_guard_rejects_usage_before_it_is_consumed(usage):
    guard = AgentBudgetGuard(load_agent_manifest(MANIFEST_PATH).budget)

    with pytest.raises(TimeoutError):
        guard.consume(**usage)

    assert guard.turns == 0
    assert guard.tokens == 0
    assert guard.cost_usd == 0.0


def test_preparation_failure_is_explicit_and_leaves_no_workspace(tmp_path):
    environment = OfflineTextEnvironment(tmp_path, fail_preparation=True)

    trial = run_agent_trial(
        load_agent_manifest(MANIFEST_PATH),
        environment,
        DeterministicFakeAgent(),
        trial=1,
    )

    assert trial.outcome == "preparation_failed"
    assert trial.passed is False
    assert trial.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_repeated_trials_start_from_identical_clean_fixture(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    environment = OfflineTextEnvironment(tmp_path)

    first = run_agent_trial(manifest, environment, DeterministicFakeAgent(), trial=1)
    second = run_agent_trial(manifest, environment, DeterministicFakeAgent(), trial=2)

    assert first.initial_state_sha256 == second.initial_state_sha256
    assert first.outcome == second.outcome == "success"
    assert list(tmp_path.iterdir()) == []


def test_offline_artifact_keeps_legacy_shape_and_agent_provenance(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    trial = run_agent_trial(
        manifest, OfflineTextEnvironment(tmp_path / "work"), DeterministicFakeAgent(), trial=1
    )
    out = tmp_path / "result.json"

    artifact = write_agent_artifact(out, manifest, [trial])
    loaded = json.loads(out.read_text(encoding="utf-8"))

    assert set(("generated_at", "dry_run", "provenance", "summary", "trials")) <= set(loaded)
    assert loaded == artifact
    assert loaded["dry_run"] is True
    assert loaded["summary"]["suite"] == "minibench-agent-v1"
    assert loaded["summary"]["pass_rate"] == 1.0
    assert loaded["summary"]["evaluation_type"] == "agent_harness"
    legacy_summary = summarize(
        single_model_config("offline/fake"),
        "legacy",
        1,
        [TrialResult("t", "test", 1, True, 1.0, 0.0, 0, 0, 0, "pass")],
    )
    assert set(legacy_summary) <= set(loaded["summary"])
    assert loaded["provenance"]["model"] == "deterministic-fake-agent"
    assert loaded["provenance"]["harness"] == "minibench-reference"
    assert loaded["provenance"]["fixture_digest"] == manifest.fixture.digest
    assert str(tmp_path) not in out.read_text(encoding="utf-8")


def test_documented_cli_runs_full_offline_lifecycle(tmp_path):
    out = tmp_path / "cli-result.json"

    rc = main([
        "--manifest", str(MANIFEST_PATH),
        "--trials", "2",
        "--out", str(out),
    ])

    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0
    assert artifact["summary"]["pass_rate"] == 1.0
    assert artifact["summary"]["pass_hat_k"] == 1.0
    assert all(trial["workspace_disposed"] for trial in artifact["trials"])


def test_infrastructure_failure_is_excluded_from_agent_statistics(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    passed = run_agent_trial(
        manifest, OfflineTextEnvironment(tmp_path), DeterministicFakeAgent(), trial=1
    )
    preparation_failure = replace(
        passed,
        trial=2,
        outcome="preparation_failed",
        passed=False,
        detail="environment preparation failed",
    )

    summary = build_agent_artifact(manifest, [passed, preparation_failure])["summary"]

    assert summary["n_trials"] == 2
    assert summary["n_infra_errors"] == 1
    assert summary["pass_rate"] == 1.0
    assert summary["pass_hat_k_effective_k"] == 1
    assert summary["pass_hat_k"] == 1.0
