"""Paired first-attempt and bounded self-review evaluation for Agent Cabinet tasks.

The runner deliberately exposes only classified, developer-visible feedback.
Verifier details and fixture-private state never cross into the correction prompt
or result artifact. Completion is measured only by running the same deterministic
workspace verifier after each agent invocation.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentbench.agent_tasks import (
    AgentAdapter,
    AgentBudget,
    AgentResult,
    AgentTaskManifest,
    AgentTrialResult,
    EnvironmentHandle,
    TaskEnvironment,
    VerificationResult,
    _over_budget,
    _valid_agent_result,
    build_agent_artifact,
)


CORRECTION_PROMPT_MARKER = "[MINIBENCH_SELF_REVIEW_CORRECTION_V1]"

_FEEDBACK_MESSAGES = {
    "verification_passed": (
        "The submitted workspace passed deterministic verification. Review it "
        "for regressions and make one corrective attempt only if needed."
    ),
    "verification_failed": (
        "The submitted workspace did not pass deterministic verification. "
        "Review your implementation and make one corrective attempt."
    ),
    "timeout": (
        "The first attempt exceeded its fixed resource budget. Review the "
        "implementation and make one bounded corrective attempt."
    ),
    "malformed_agent_result": (
        "The first attempt did not return a valid terminal result. Inspect the "
        "workspace and make one bounded corrective attempt."
    ),
}


@dataclass(frozen=True)
class ReviewFeedback:
    category: str
    message: str


@dataclass(frozen=True)
class ReviewPhaseResult:
    phase: str
    outcome: str
    passed: bool
    infra_error: bool
    agent_claimed_success: bool
    termination_reason: str
    turns: int
    wall_time_ms: int
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None


@dataclass(frozen=True)
class PairedReviewTrialResult:
    task_id: str
    category: str
    trial: int
    outcome: str
    passed: bool
    infra_error: bool
    pair_complete: bool
    first_attempt: ReviewPhaseResult
    correction: ReviewPhaseResult | None
    feedback: ReviewFeedback | None
    corrected_failure: bool
    introduced_regression: bool
    no_change: bool
    initial_state_sha256: str | None
    workspace_disposed: bool


def _phase_result(
    phase: str,
    environment: TaskEnvironment,
    agent: AgentAdapter,
    handle: EnvironmentHandle,
    prompt: str,
    budget: AgentBudget,
) -> ReviewPhaseResult:
    started = time.monotonic()
    agent_result: AgentResult | None = None
    outcome = "execution_failed"
    infra_error = True
    try:
        candidate = environment.execute(agent, handle, prompt, budget)
        if not _valid_agent_result(candidate):
            outcome = "malformed_agent_result"
            infra_error = False
        elif _over_budget(candidate, budget):
            agent_result = candidate
            outcome = "timeout"
            infra_error = False
        else:
            agent_result = candidate
            try:
                verification = environment.verify(handle)
            except Exception:
                outcome = "verification_infra_failed"
            else:
                if not isinstance(verification, VerificationResult) or not isinstance(
                    verification.passed, bool
                ):
                    outcome = "verification_infra_failed"
                else:
                    outcome = "success" if verification.passed else "verification_failed"
                    infra_error = False
    except TimeoutError:
        outcome = "timeout"
        infra_error = False
    except Exception:
        pass

    return ReviewPhaseResult(
        phase=phase,
        outcome=outcome,
        passed=outcome == "success",
        infra_error=infra_error,
        agent_claimed_success=agent_result.claimed_success if agent_result else False,
        termination_reason=agent_result.termination_reason if agent_result else outcome,
        turns=agent_result.turns if agent_result else 0,
        wall_time_ms=int((time.monotonic() - started) * 1000),
        tokens_in=agent_result.tokens_in if agent_result else None,
        tokens_out=agent_result.tokens_out if agent_result else None,
        cost_usd=agent_result.cost_usd if agent_result else None,
    )


def _preparation_failure() -> ReviewPhaseResult:
    return ReviewPhaseResult(
        phase="first_attempt",
        outcome="preparation_failed",
        passed=False,
        infra_error=True,
        agent_claimed_success=False,
        termination_reason="preparation_failed",
        turns=0,
        wall_time_ms=0,
        tokens_in=None,
        tokens_out=None,
        cost_usd=None,
    )


def _feedback_for(first_attempt: ReviewPhaseResult) -> ReviewFeedback:
    category = first_attempt.outcome
    if category == "success":
        category = "verification_passed"
    elif category not in _FEEDBACK_MESSAGES:
        category = "verification_failed"
    return ReviewFeedback(category=category, message=_FEEDBACK_MESSAGES[category])


def _correction_prompt(public_prompt: str, feedback: ReviewFeedback) -> str:
    return (
        f"{CORRECTION_PROMPT_MARKER}\n"
        "Original developer task:\n"
        f"{public_prompt}\n\n"
        f"Classified feedback ({feedback.category}):\n"
        f"{feedback.message}\n\n"
        "Work in the existing workspace. Return a terminal result after the correction."
    )


def run_paired_review_trial(
    manifest: AgentTaskManifest,
    environment: TaskEnvironment,
    agent: AgentAdapter,
    *,
    correction_budget: AgentBudget,
    trial: int,
) -> PairedReviewTrialResult:
    """Run two independently budgeted attempts in one prepared workspace."""
    handle: EnvironmentHandle | None = None
    first_attempt = _preparation_failure()
    correction: ReviewPhaseResult | None = None
    feedback: ReviewFeedback | None = None
    try:
        prepared = environment.prepare(manifest, trial)
        handle = prepared.handle
        first_attempt = _phase_result(
            "first_attempt",
            environment,
            agent,
            handle,
            prepared.prompt,
            manifest.budget,
        )
        if not first_attempt.infra_error:
            feedback = _feedback_for(first_attempt)
            correction = _phase_result(
                "correction",
                environment,
                agent,
                handle,
                _correction_prompt(prepared.prompt, feedback),
                correction_budget,
            )
    except Exception:
        pass
    finally:
        environment.dispose(handle)

    pair_complete = correction is not None and not correction.infra_error
    final = correction if correction is not None else first_attempt
    corrected_failure = pair_complete and not first_attempt.passed and correction.passed
    introduced_regression = pair_complete and first_attempt.passed and not correction.passed
    no_change = pair_complete and first_attempt.passed == correction.passed
    return PairedReviewTrialResult(
        task_id=manifest.task_id,
        category=manifest.category,
        trial=trial,
        outcome=final.outcome,
        passed=final.passed if pair_complete else False,
        infra_error=first_attempt.infra_error
        or bool(correction and correction.infra_error),
        pair_complete=pair_complete,
        first_attempt=first_attempt,
        correction=correction,
        feedback=feedback,
        corrected_failure=bool(corrected_failure),
        introduced_regression=bool(introduced_regression),
        no_change=bool(no_change),
        initial_state_sha256=handle.initial_state_sha256 if handle else None,
        workspace_disposed=environment.is_disposed(handle),
    )


def _legacy_trial(result: PairedReviewTrialResult) -> AgentTrialResult:
    final = result.correction if result.correction is not None else result.first_attempt
    phases = [result.first_attempt] + (
        [result.correction] if result.correction is not None else []
    )
    return AgentTrialResult(
        task_id=result.task_id,
        category=result.category,
        trial=result.trial,
        outcome="execution_failed" if result.infra_error else final.outcome,
        passed=result.passed,
        detail="pass" if result.passed else "fail",
        agent_claimed_success=final.agent_claimed_success,
        termination_reason=final.termination_reason,
        turns=sum(phase.turns for phase in phases),
        wall_time_ms=sum(phase.wall_time_ms for phase in phases),
        tokens_in=_complete_sum([phase.tokens_in for phase in phases]),
        tokens_out=_complete_sum([phase.tokens_out for phase in phases]),
        cost_usd=_complete_sum([phase.cost_usd for phase in phases]),
        initial_state_sha256=result.initial_state_sha256,
        workspace_disposed=result.workspace_disposed,
    )


def _complete_sum(values: list[int | float | None]) -> int | float | None:
    """Sum usage only when every contributing phase reported the field."""
    if not values or any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _terminal_outcome(trials: list[PairedReviewTrialResult]) -> str:
    if any(trial.infra_error for trial in trials):
        return "infrastructure_failed"
    return (
        "success"
        if trials and all(trial.passed for trial in trials)
        else "verification_failed"
    )


def _artifact_trial(result: PairedReviewTrialResult) -> dict[str, Any]:
    """Keep paired evidence while satisfying the established import contract."""
    legacy = asdict(_legacy_trial(result))
    legacy["score"] = 1.0 if result.passed else 0.0
    legacy["latency_ms"] = legacy["wall_time_ms"]
    return {**legacy, **asdict(result)}


def build_self_review_artifact(
    manifest: AgentTaskManifest,
    trials: list[PairedReviewTrialResult],
    correction_budget: AgentBudget,
) -> dict[str, Any]:
    """Build a legacy-loadable artifact with nested paired phase evidence."""
    artifact = build_agent_artifact(manifest, [_legacy_trial(trial) for trial in trials])
    first_eligible = [trial for trial in trials if not trial.first_attempt.infra_error]
    complete = [trial for trial in trials if trial.pair_complete]
    count = len(complete)
    first_count = len(first_eligible)
    first_passes = sum(trial.first_attempt.passed for trial in first_eligible)
    paired_first_passes = sum(trial.first_attempt.passed for trial in complete)
    final_passes = sum(trial.passed for trial in complete)
    first_rate = first_passes / first_count if first_count else None
    paired_first_rate = paired_first_passes / count if count else None
    final_rate = final_passes / count if count else None
    trial_costs = [_legacy_trial(trial).cost_usd for trial in trials]
    if any(cost is None for cost in trial_costs):
        artifact["summary"]["cost_usd_total"] = None
        artifact["summary"]["cost_usd_per_task"] = None
    artifact["provenance"]["budgets"] = {
        "first_attempt": asdict(manifest.budget),
        "correction": asdict(correction_budget),
    }
    artifact["provenance"]["terminal_outcome"] = _terminal_outcome(trials)
    artifact["summary"]["decoding"]["correction_budget"] = asdict(
        correction_budget
    )
    artifact["summary"].update(
        {
            "evaluation_type": "agent_harness_self_review",
            "n_infra_errors": sum(
                trial.first_attempt.infra_error
                + bool(trial.correction and trial.correction.infra_error)
                for trial in trials
            ),
            "n_first_attempts": first_count,
            "n_paired_trials": count,
            "first_pass_completion": first_rate,
            "paired_first_pass_completion": paired_first_rate,
            "final_completion": final_rate,
            "first_attempt_usage": {
                "turns_total": sum(
                    trial.first_attempt.turns for trial in first_eligible
                ),
                "wall_time_ms_total": sum(
                    trial.first_attempt.wall_time_ms for trial in first_eligible
                ),
                "tokens_in_total": _complete_sum(
                    [trial.first_attempt.tokens_in for trial in first_eligible]
                ),
                "tokens_out_total": _complete_sum(
                    [trial.first_attempt.tokens_out for trial in first_eligible]
                ),
                "cost_usd_total": _complete_sum(
                    [trial.first_attempt.cost_usd for trial in first_eligible]
                ),
            },
            "corrected_failures": sum(trial.corrected_failure for trial in complete),
            "introduced_regressions": sum(
                trial.introduced_regression for trial in complete
            ),
            "no_change_outcomes": sum(trial.no_change for trial in complete),
            "self_correction_lift": (
                final_rate - paired_first_rate
                if paired_first_rate is not None and final_rate is not None
                else None
            ),
        }
    )
    artifact["trials"] = [_artifact_trial(trial) for trial in trials]
    return artifact


def write_self_review_artifact(
    path: str | Path,
    manifest: AgentTaskManifest,
    trials: list[PairedReviewTrialResult],
    correction_budget: AgentBudget,
) -> dict[str, Any]:
    artifact = build_self_review_artifact(manifest, trials, correction_budget)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


class GeneratedRepairSelfReviewAgent:
    """Offline reference: no-op first, known behavioral repair on correction."""

    def execute(self, prompt: str, workspace: Path, budget: Any) -> AgentResult:
        if CORRECTION_PROMPT_MARKER not in prompt:
            budget.consume(turns=1)
            return AgentResult(
                "completed",
                claimed_success=False,
                turns=1,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
            )
        from agentbench.generated_repairs import GeneratedRepairGoldAgent

        return GeneratedRepairGoldAgent().execute(prompt, workspace, budget)


def run_generated_offline(seed: int, trials: int, out: str | Path) -> int:
    """Run the paired contract over the existing seeded repair fixture."""
    from agentbench.agent_tasks import AGENT_GRADER_VERSION
    from agentbench.generated_repairs import (
        FIXTURE_VERSION,
        HARNESS,
        GeneratedRepairEnvironment,
        generate_fixture,
        manifest_for,
    )

    if trials < 1:
        raise ValueError("trials must be positive")
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)
    correction_budget = AgentBudget(
        max_turns=2,
        wall_time_seconds=5,
        max_tokens=200,
        max_cost_usd=0.0,
    )
    results = [
        run_paired_review_trial(
            manifest,
            GeneratedRepairEnvironment(fixture),
            GeneratedRepairSelfReviewAgent(),
            correction_budget=correction_budget,
            trial=trial,
        )
        for trial in range(1, trials + 1)
    ]
    artifact = build_self_review_artifact(manifest, results, correction_budget)
    artifact["provenance"].update(
        {
            "fixture_version": FIXTURE_VERSION,
            "mutation_template_sha256": fixture.template_hash,
            "seed_sha256": fixture.seed_hash,
            "harness": HARNESS,
            "harness_version": AGENT_GRADER_VERSION,
        }
    )
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], indent=2))
    return 0 if all(result.passed and result.workspace_disposed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a paired self-review on a seeded repository-repair fixture."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")
    return run_generated_offline(args.seed, args.trials, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
