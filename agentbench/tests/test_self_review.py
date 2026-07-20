import json

import pytest

from agentbench.agent_tasks import (
    AgentBudget,
    AgentResult,
    OfflineTextEnvironment,
    VerificationResult,
    load_agent_manifest,
)
from agentbench.compare import ComparabilityError, _outcomes, check_comparable
from agentbench.import_results import artifact_to_payload, load_trials
from agentbench.self_review import (
    CORRECTION_PROMPT_MARKER,
    build_self_review_artifact,
    run_generated_offline,
    run_paired_review_trial,
    write_self_review_artifact,
)


MANIFEST_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "tasks"
    / "minibench-agent-v1-offline.json"
)
CORRECTION_BUDGET = AgentBudget(
    max_turns=1,
    wall_time_seconds=3,
    max_tokens=40,
    max_cost_usd=0.0,
)


class _PromptScriptedAgent:
    def __init__(self, first_action, correction_action):
        self.first_action = first_action
        self.correction_action = correction_action

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        action = (
            self.correction_action
            if CORRECTION_PROMPT_MARKER in prompt
            else self.first_action
        )
        target = workspace / "service.conf"
        if action == "pass":
            target.write_text("status=READY\n", encoding="utf-8")
        elif action == "fail":
            target.write_text("status=BROKEN\n", encoding="utf-8")
        elif action == "timeout":
            raise TimeoutError("scripted timeout")
        elif action == "malformed":
            return {"claimed_success": True}
        elif action == "error":
            raise RuntimeError("scripted provider failure")
        return AgentResult(
            "completed",
            claimed_success=True,
            turns=1,
            tokens_in=2,
            tokens_out=3,
            cost_usd=0.0,
        )


class _PrivateDetailEnvironment(OfflineTextEnvironment):
    def verify(self, handle):
        passed = (handle.workspace / "service.conf").read_text(
            encoding="utf-8"
        ) == "status=READY\n"
        return VerificationResult(passed, "PRIVATE_GOLD=do-not-release")


class _BudgetAwareAgent:
    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        expected_tokens = 40 if CORRECTION_PROMPT_MARKER in prompt else 100
        status = "READY" if budget.max_tokens == expected_tokens else "BROKEN"
        (workspace / "service.conf").write_text(
            f"status={status}\n", encoding="utf-8"
        )
        return AgentResult("completed", claimed_success=True, turns=1)


class _PartialUsageAgent:
    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        if CORRECTION_PROMPT_MARKER in prompt:
            (workspace / "service.conf").write_text(
                "status=READY\n", encoding="utf-8"
            )
            return AgentResult(
                "completed",
                claimed_success=True,
                turns=1,
                tokens_in=2,
                tokens_out=3,
                cost_usd=0.0,
            )
        return AgentResult("completed", claimed_success=False, turns=1)


@pytest.mark.parametrize(
    ("first", "correction", "first_passed", "final_passed", "corrected", "regressed", "unchanged"),
    [
        ("fail", "pass", False, True, True, False, False),
        ("fail", "fail", False, False, False, False, True),
        ("pass", "pass", True, True, False, False, True),
        ("pass", "fail", True, False, False, True, False),
    ],
)
def test_paired_review_records_completion_transitions(
    tmp_path,
    first,
    correction,
    first_passed,
    final_passed,
    corrected,
    regressed,
    unchanged,
):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path),
        _PromptScriptedAgent(first, correction),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )

    assert result.first_attempt.passed is first_passed
    assert result.correction is not None
    assert result.correction.passed is final_passed
    assert result.passed is final_passed
    assert result.corrected_failure is corrected
    assert result.introduced_regression is regressed
    assert result.no_change is unchanged
    assert result.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("first", "correction", "first_outcome", "correction_outcome", "final_passed"),
    [
        ("timeout", "pass", "timeout", "success", True),
        ("fail", "malformed", "verification_failed", "malformed_agent_result", False),
    ],
)
def test_timeout_and_malformed_correction_outcomes_are_explicit(
    tmp_path, first, correction, first_outcome, correction_outcome, final_passed
):
    result = run_paired_review_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        _PromptScriptedAgent(first, correction),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )

    assert result.first_attempt.outcome == first_outcome
    assert result.correction.outcome == correction_outcome
    assert result.passed is final_passed


def test_claimed_success_without_workspace_correction_does_not_pass(tmp_path):
    result = run_paired_review_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        _PromptScriptedAgent("fail", "fail"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )

    assert result.correction.agent_claimed_success is True
    assert result.correction.passed is False
    assert result.passed is False


def test_correction_receives_its_own_pinned_budget(tmp_path):
    result = run_paired_review_trial(
        load_agent_manifest(MANIFEST_PATH),
        OfflineTextEnvironment(tmp_path),
        _BudgetAwareAgent(),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )

    assert result.first_attempt.passed is True
    assert result.correction.passed is True


def test_feedback_and_artifact_never_expose_verifier_detail(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        _PrivateDetailEnvironment(tmp_path / "work"),
        _PromptScriptedAgent("fail", "fail"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    artifact = build_self_review_artifact(manifest, [result], CORRECTION_BUDGET)
    serialized = json.dumps(artifact)

    assert result.feedback.category == "verification_failed"
    assert result.feedback.message == (
        "The submitted workspace did not pass deterministic verification. "
        "Review your implementation and make one corrective attempt."
    )
    assert "PRIVATE_GOLD" not in serialized
    assert "do-not-release" not in serialized


def test_first_phase_infrastructure_failure_skips_review_and_lift(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path, fail_preparation=True),
        _PromptScriptedAgent("pass", "pass"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    summary = build_self_review_artifact(manifest, [result], CORRECTION_BUDGET)["summary"]

    assert result.first_attempt.outcome == "preparation_failed"
    assert result.first_attempt.infra_error is True
    assert result.correction is None
    assert result.pair_complete is False
    assert result.corrected_failure is False
    assert result.introduced_regression is False
    assert result.no_change is False
    assert summary["n_infra_errors"] == 1
    assert summary["n_paired_trials"] == 0
    assert summary["self_correction_lift"] is None


def test_correction_infrastructure_failure_is_phase_specific(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path),
        _PromptScriptedAgent("pass", "error"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    summary = build_self_review_artifact(
        manifest, [result], CORRECTION_BUDGET
    )["summary"]

    assert result.first_attempt.infra_error is False
    assert result.correction.outcome == "execution_failed"
    assert result.correction.infra_error is True
    assert result.pair_complete is False
    assert result.corrected_failure is False
    assert summary["n_infra_errors"] == 1
    assert summary["n_first_attempts"] == 1
    assert summary["first_pass_completion"] == 1.0
    assert summary["first_attempt_usage"] == {
        "turns_total": 1,
        "wall_time_ms_total": result.first_attempt.wall_time_ms,
        "tokens_in_total": 2,
        "tokens_out_total": 3,
        "cost_usd_total": 0.0,
    }
    assert summary["final_completion"] is None
    assert summary["self_correction_lift"] is None
    assert summary["pass_rate"] == 0.0
    assert summary["n_paired_trials"] == 0
    assert build_self_review_artifact(
        manifest, [result], CORRECTION_BUDGET
    )["provenance"]["terminal_outcome"] == "infrastructure_failed"


def test_partial_phase_usage_is_not_silently_counted_as_zero(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path),
        _PartialUsageAgent(),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    artifact = build_self_review_artifact(manifest, [result], CORRECTION_BUDGET)
    row = artifact["trials"][0]

    assert result.passed is True
    assert result.first_attempt.tokens_in is None
    assert result.correction.tokens_in == 2
    assert row["tokens_in"] is None
    assert row["tokens_out"] is None
    assert row["cost_usd"] is None
    assert artifact["summary"]["first_attempt_usage"]["tokens_in_total"] is None
    assert artifact["summary"]["first_attempt_usage"]["tokens_out_total"] is None
    assert artifact["summary"]["first_attempt_usage"]["cost_usd_total"] is None

    artifact["dry_run"] = False
    payload = artifact_to_payload(
        artifact, source="paired.json", provider="offline"
    )
    assert payload["tokens_in"] is None
    assert payload["tokens_out"] is None
    assert payload["results"][0]["tokens_in"] is None
    assert payload["results"][0]["tokens_out"] is None


def test_lift_uses_only_complete_pairs_while_first_pass_uses_all_eligible(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    correction_infra = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path / "infra"),
        _PromptScriptedAgent("pass", "error"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    corrected = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path / "complete"),
        _PromptScriptedAgent("fail", "pass"),
        correction_budget=CORRECTION_BUDGET,
        trial=2,
    )

    artifact = build_self_review_artifact(
        manifest, [correction_infra, corrected], CORRECTION_BUDGET
    )
    summary = artifact["summary"]

    assert summary["n_first_attempts"] == 2
    assert summary["first_pass_completion"] == 0.5
    assert summary["first_attempt_usage"]["turns_total"] == 2
    assert summary["n_paired_trials"] == 1
    assert summary["paired_first_pass_completion"] == 0.0
    assert summary["final_completion"] == 1.0
    assert summary["self_correction_lift"] == 1.0
    assert summary["cost_usd_total"] is None
    assert summary["cost_usd_per_task"] is None
    artifact["dry_run"] = False
    payload = artifact_to_payload(
        artifact,
        source="mixed-paired.json",
        provider="offline",
        allow_infra_errors=True,
    )
    assert payload["cost_usd_per_task"] is None


def test_artifact_has_compatible_trial_shape_and_paired_metrics(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    scripts = [
        ("fail", "pass"),
        ("fail", "fail"),
        ("pass", "pass"),
        ("pass", "fail"),
    ]
    results = [
        run_paired_review_trial(
            manifest,
            OfflineTextEnvironment(tmp_path / str(index)),
            _PromptScriptedAgent(first, correction),
            correction_budget=CORRECTION_BUDGET,
            trial=index,
        )
        for index, (first, correction) in enumerate(scripts, start=1)
    ]
    artifact = build_self_review_artifact(manifest, results, CORRECTION_BUDGET)
    summary = artifact["summary"]

    assert set(
        ("generated_at", "dry_run", "provenance", "summary", "trials")
    ) <= set(artifact)
    assert summary["evaluation_type"] == "agent_harness_self_review"
    assert summary["first_pass_completion"] == 0.5
    assert summary["final_completion"] == 0.5
    assert summary["pass_rate"] == summary["final_completion"]
    assert summary["corrected_failures"] == 1
    assert summary["introduced_regressions"] == 1
    assert summary["no_change_outcomes"] == 2
    assert summary["self_correction_lift"] == 0.0
    assert summary["n_paired_trials"] == 4
    assert summary["n_first_attempts"] == 4
    assert _outcomes(artifact) == {
        (manifest.task_id, 1): True,
        (manifest.task_id, 2): False,
        (manifest.task_id, 3): True,
        (manifest.task_id, 4): False,
    }
    assert (
        artifact["provenance"]["budgets"]["first_attempt"]["max_turns"]
        == manifest.budget.max_turns
    )
    assert (
        artifact["provenance"]["budgets"]["correction"]["max_turns"]
        == CORRECTION_BUDGET.max_turns
    )
    assert all(
        set(("task_id", "category", "trial", "passed", "outcome")) <= set(row)
        for row in artifact["trials"]
    )
    check_comparable([artifact, artifact])

    different_budget = AgentBudget(
        max_turns=2,
        wall_time_seconds=3,
        max_tokens=40,
        max_cost_usd=0.0,
    )
    incompatible = build_self_review_artifact(manifest, results, different_budget)
    with pytest.raises(ComparabilityError, match="decoding"):
        check_comparable([artifact, incompatible])


def test_self_review_artifact_round_trips_as_json(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path / "work"),
        _PromptScriptedAgent("fail", "pass"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    destination = tmp_path / "paired.json"

    artifact = write_self_review_artifact(
        destination, manifest, [result], CORRECTION_BUDGET
    )

    assert json.loads(destination.read_text(encoding="utf-8")) == artifact


def test_paired_rows_load_through_existing_result_importer(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    result = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path),
        _PromptScriptedAgent("fail", "pass"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    artifact = build_self_review_artifact(manifest, [result], CORRECTION_BUDGET)

    loaded = load_trials(artifact["trials"])

    assert len(loaded) == 1
    assert loaded[0].task_id == manifest.task_id
    assert loaded[0].passed is True
    assert loaded[0].score == 1.0
    assert loaded[0].infra_error is False
    assert loaded[0].latency_ms >= 0
    assert loaded[0].tokens_in == 4
    assert loaded[0].tokens_out == 6
    assert artifact["trials"][0]["first_attempt"]["passed"] is False
    assert artifact["trials"][0]["correction"]["passed"] is True


def test_terminal_outcome_distinguishes_scored_failure_from_infrastructure(tmp_path):
    manifest = load_agent_manifest(MANIFEST_PATH)
    scored_failure = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path / "scored"),
        _PromptScriptedAgent("fail", "fail"),
        correction_budget=CORRECTION_BUDGET,
        trial=1,
    )
    corrected = run_paired_review_trial(
        manifest,
        OfflineTextEnvironment(tmp_path / "corrected"),
        _PromptScriptedAgent("fail", "pass"),
        correction_budget=CORRECTION_BUDGET,
        trial=2,
    )

    failed_artifact = build_self_review_artifact(
        manifest, [scored_failure], CORRECTION_BUDGET
    )
    success_artifact = build_self_review_artifact(
        manifest, [corrected], CORRECTION_BUDGET
    )

    assert failed_artifact["provenance"]["terminal_outcome"] == "verification_failed"
    assert success_artifact["provenance"]["terminal_outcome"] == "success"


def test_generated_repair_self_review_smoke_uses_existing_fixture(tmp_path):
    destination = tmp_path / "generated-paired.json"

    rc = run_generated_offline(20260719, 1, destination)
    artifact = json.loads(destination.read_text(encoding="utf-8"))

    assert rc == 0
    assert artifact["summary"]["first_pass_completion"] == 0.0
    assert artifact["summary"]["final_completion"] == 1.0
    assert artifact["summary"]["corrected_failures"] == 1
    assert artifact["provenance"]["fixture_version"] == "generated-repository-repair@1"
    assert artifact["trials"][0]["first_attempt"]["outcome"] == "verification_failed"
    assert artifact["trials"][0]["correction"]["outcome"] == "success"
