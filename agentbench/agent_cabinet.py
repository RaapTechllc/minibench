"""Agent Cabinet provenance, reliability fields, and the two gate receipts.

This is the only definition site for ``AGENT_CABINET_POLICY``, the required
provenance key set, reliability summary fields, and the comparability /
publication receipts. Family overlays inherit the required set because
:func:`agentbench.agent_tasks.build_agent_artifact` calls into this module.

Comparability and publication are separate decisions: a pairing mismatch never
publish-refuses a run. There is no ``--allow-infra`` override on this path.
This module does not fetch an external schema.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


AGENT_CABINET_POLICY = "agent-cabinet-gates-v1"

REQUIRED_PROVENANCE_KEYS = (
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

RELIABILITY_SUMMARY_FIELDS = (
    "false_verification_rate",
    "regression_rate",
    "termination_reasons",
)

COMPARABILITY_FIELDS = (
    "task_set_sha256",
    "fixture_reference",
    "fixture_digest",
    "harness",
    "harness_version",
    "tool_contract_sha256",
    "budgets",
    "grader_version",
    "private_split_id",
)

_COMPARABILITY_REASON_BY_FIELD = {
    "task_set_sha256": "task_set_mismatch",
    "fixture_reference": "fixture_version_mismatch",
    "fixture_digest": "fixture_version_mismatch",
    "harness": "harness_contract_mismatch",
    "harness_version": "harness_contract_mismatch",
    "tool_contract_sha256": "harness_contract_mismatch",
    "budgets": "budget_mismatch",
    "grader_version": "grader_version_mismatch",
    "private_split_id": "private_split_mismatch",
}

PUBLISH_REFUSE_DRY_RUN = "dry_run"
PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS = "infrastructure_errors"
PUBLISH_REFUSE_CANARY_FLAGS = "canary_flags"
PUBLISH_REFUSE_MUTABLE_FIXTURE = "mutable_fixture_reference"
PUBLISH_REFUSE_MISSING_PROVENANCE = "missing_provenance"
PUBLISH_REFUSE_INCOMPLETE_DISPOSAL = "incomplete_disposal"
PUBLISH_REFUSE_INVALID_SELF_CHECK = "invalid_task_self_check"

PUBLICATION_REFUSE_REASONS = (
    PUBLISH_REFUSE_DRY_RUN,
    PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS,
    PUBLISH_REFUSE_CANARY_FLAGS,
    PUBLISH_REFUSE_MUTABLE_FIXTURE,
    PUBLISH_REFUSE_MISSING_PROVENANCE,
    PUBLISH_REFUSE_INCOMPLETE_DISPOSAL,
    PUBLISH_REFUSE_INVALID_SELF_CHECK,
)

AGENT_EVALUATION_TYPES = frozenset({"agent_harness", "agent_harness_self_review"})
INFRA_OUTCOMES = frozenset({"preparation_failed", "execution_failed"})
_STRUCTURED_REGRESSION_KEYS = ("introduced_regression", "regression", "regression_failed")
_FORBIDDEN_PROVENANCE_KEYS = frozenset(
    {
        "gold",
        "gold_sql",
        "gold_files",
        "gold_patch",
        "gold_implementation",
        "hidden_tests",
        "hidden_test",
        "probe",
        "private_rows",
        "private_row",
        "seed",
        "MINIBENCH_SEED",
        "minibench_seed",
        "workspace",
        "workspace_path",
    }
)
_FAILED_SELF_CHECK_VALUES = frozenset({False, "failed", "fail", "invalid"})


def _canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _present(value: Any) -> bool:
    if value is None:
        return False
    if value == "":
        return False
    if value == [] or value == {}:
        return False
    return True


def _trial_mapping(trial: Any) -> dict[str, Any]:
    if isinstance(trial, dict):
        return trial
    if is_dataclass(trial):
        return asdict(trial)
    return {
        "task_id": getattr(trial, "task_id", None),
        "outcome": getattr(trial, "outcome", None),
        "passed": getattr(trial, "passed", False),
        "agent_claimed_success": getattr(trial, "agent_claimed_success", False),
        "termination_reason": getattr(trial, "termination_reason", None),
        "workspace_disposed": getattr(trial, "workspace_disposed", True),
        "infra_error": getattr(trial, "infra_error", False),
    }


def git_commit() -> str | None:
    """Record HEAD without writing a workspace path into provenance."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).resolve().parent,
        )
        return completed.stdout.strip() or None if completed.returncode == 0 else None
    except OSError:
        return None


def model_route(provider: str, model: str) -> str:
    if "/" in model:
        return model
    return f"{provider}/{model}"


def tool_contract_sha256(tool_contract: Sequence[str]) -> str:
    return _sha256_text(_canonical_dumps(list(tool_contract)))


def prompt_config_sha256(*, public_prompt: str, max_tokens: int | None) -> str:
    return _sha256_text(
        _canonical_dumps(
            {
                "public_prompt": public_prompt,
                "system_prompt": "agent-harness",
                "max_tokens": max_tokens,
            }
        )
    )


def task_set_sha256(
    *,
    suite: str,
    task_ids: Iterable[str],
    fixture_reference: str,
    fixture_digest: str,
) -> str:
    return _sha256_text(
        _canonical_dumps(
            {
                "suite": suite,
                "tasks": sorted(set(task_ids)),
                "fixture_reference": fixture_reference,
                "fixture_digest": fixture_digest,
            }
        )
    )


def private_split_id(*, suite: str, private_split: bool, fixture_digest: str) -> str:
    kind = "private" if private_split else "public"
    return _sha256_text(f"{suite}|{kind}|{fixture_digest}")


def default_generator_sha256(
    *, preparation_strategy: str, verification_strategy: str, fixture_reference: str
) -> str:
    return _sha256_text(
        f"{preparation_strategy}|{verification_strategy}|{fixture_reference}"
    )


def sanitize_agent_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    """Drop gold, hidden tests, private rows, raw seed, and workspace paths."""
    cleaned: dict[str, Any] = {}
    for key, value in provenance.items():
        if key in _FORBIDDEN_PROVENANCE_KEYS:
            continue
        if isinstance(value, dict):
            cleaned[key] = sanitize_agent_provenance(value)
        else:
            cleaned[key] = value
    return cleaned


def build_required_provenance(
    *,
    model: str,
    provider: str,
    harness: str,
    harness_version: str,
    tool_contract: Sequence[str],
    fixture_reference: str,
    fixture_digest: str,
    generator_sha256: str,
    suite: str,
    task_ids: Iterable[str],
    budgets: dict[str, Any],
    grader_version: str,
    private_split: bool,
    public_prompt: str,
    git_commit_sha: str | None = None,
) -> dict[str, Any]:
    contract = list(tool_contract)
    return sanitize_agent_provenance(
        {
            "model": model,
            "provider": provider,
            "model_route": model_route(provider, model),
            "harness": harness,
            "harness_version": harness_version,
            "tool_contract": contract,
            "tool_contract_sha256": tool_contract_sha256(contract),
            "prompt_config_sha256": prompt_config_sha256(
                public_prompt=public_prompt,
                max_tokens=budgets.get("max_tokens") if isinstance(budgets, dict) else None,
            ),
            "fixture_reference": fixture_reference,
            "fixture_digest": fixture_digest,
            "generator_sha256": generator_sha256,
            "suite": suite,
            "task_set_sha256": task_set_sha256(
                suite=suite,
                task_ids=task_ids,
                fixture_reference=fixture_reference,
                fixture_digest=fixture_digest,
            ),
            "budgets": budgets,
            "git_commit": git_commit_sha if git_commit_sha is not None else git_commit(),
            "grader_version": grader_version,
            "private_split": private_split,
            "private_split_id": private_split_id(
                suite=suite, private_split=private_split, fixture_digest=fixture_digest
            ),
            "policy_version": AGENT_CABINET_POLICY,
        }
    )


def _is_infra(trial: dict[str, Any]) -> bool:
    if trial.get("infra_error"):
        return True
    return trial.get("outcome") in INFRA_OUTCOMES


def _is_false_verification(trial: dict[str, Any]) -> bool:
    """Claim AND oracle fail only. Silence or ordinary failure is not counted."""
    if not trial.get("agent_claimed_success"):
        return False
    return trial.get("outcome") == "verification_failed"


def _structured_regression_rate(trials: list[dict[str, Any]]) -> float | None:
    flags: list[bool] = []
    for trial in trials:
        for key in _STRUCTURED_REGRESSION_KEYS:
            value = trial.get(key)
            if isinstance(value, bool):
                flags.append(value)
                break
    if not flags:
        return None
    return round(sum(flags) / len(flags), 4)


def reliability_summary_fields(trials: Iterable[Any]) -> dict[str, Any]:
    rows = [_trial_mapping(trial) for trial in trials]
    scored = [trial for trial in rows if not _is_infra(trial)]
    n_scored = len(scored)
    false_n = sum(1 for trial in scored if _is_false_verification(trial))
    reasons = Counter(
        str(trial.get("termination_reason") or "unknown") for trial in rows
    )
    return {
        "false_verification_rate": round(false_n / n_scored, 4) if n_scored else 0.0,
        "regression_rate": _structured_regression_rate(scored),
        "termination_reasons": dict(sorted(reasons.items())),
    }


def apply_reliability_fields(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.setdefault("summary", {})
    summary.update(reliability_summary_fields(artifact.get("trials") or []))
    return artifact


def apply_agent_cabinet_to_artifact(
    artifact: dict[str, Any],
    *,
    model: str,
    provider: str,
    harness: str,
    harness_version: str,
    tool_contract: Sequence[str],
    fixture_reference: str,
    fixture_digest: str,
    generator_sha256: str,
    suite: str,
    task_ids: Iterable[str],
    budgets: dict[str, Any],
    grader_version: str,
    private_split: bool,
    public_prompt: str,
    git_commit_sha: str | None = None,
) -> dict[str, Any]:
    """Fill the required provenance set and reliability fields on one artifact."""
    provenance = dict(artifact.get("provenance") or {})
    provenance.update(
        build_required_provenance(
            model=model,
            provider=provider,
            harness=harness,
            harness_version=harness_version,
            tool_contract=tool_contract,
            fixture_reference=fixture_reference,
            fixture_digest=fixture_digest,
            generator_sha256=generator_sha256,
            suite=suite,
            task_ids=task_ids,
            budgets=budgets,
            grader_version=grader_version,
            private_split=private_split,
            public_prompt=public_prompt,
            git_commit_sha=git_commit_sha,
        )
    )
    artifact["provenance"] = sanitize_agent_provenance(provenance)
    apply_reliability_fields(artifact)
    return artifact


def is_agent_cabinet_artifact(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    evaluation = (data.get("summary") or {}).get("evaluation_type")
    if evaluation in AGENT_EVALUATION_TYPES:
        return True
    return (data.get("provenance") or {}).get("policy_version") == AGENT_CABINET_POLICY


def _comparability_value(artifact: dict[str, Any], field: str) -> Any:
    provenance = artifact.get("provenance") or {}
    if field == "grader_version":
        return provenance.get("grader_version", (artifact.get("summary") or {}).get("grader_version"))
    if field == "budgets":
        return json.loads(_canonical_dumps(provenance.get("budgets")))
    return provenance.get(field)


def comparability_receipt(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Are these two Agent Cabinet runs equivalent enough to compare?"""
    failing_fields: list[str] = []
    reasons: list[str] = []
    for field in COMPARABILITY_FIELDS:
        if _comparability_value(left, field) != _comparability_value(right, field):
            failing_fields.append(field)
            reason = _COMPARABILITY_REASON_BY_FIELD[field]
            if reason not in reasons:
                reasons.append(reason)
    return {
        "policy_version": AGENT_CABINET_POLICY,
        "comparable": not failing_fields,
        "failing_fields": failing_fields,
        "reasons": reasons,
    }


def _missing_provenance_keys(provenance: dict[str, Any]) -> list[str]:
    return [key for key in REQUIRED_PROVENANCE_KEYS if not _present(provenance.get(key))]


def _fixture_reference_is_mutable(reference: Any) -> bool:
    if not isinstance(reference, str) or not reference.strip():
        return False
    if "@" not in reference:
        return True
    return reference.endswith("@latest") or "@latest" in reference


def _has_infrastructure_errors(artifact: dict[str, Any]) -> bool:
    summary = artifact.get("summary") or {}
    trials = [_trial_mapping(trial) for trial in artifact.get("trials") or []]
    n_summary = summary.get("n_infra_errors") or 0
    n_trials = sum(1 for trial in trials if _is_infra(trial))
    return max(n_summary, n_trials) > 0


def _has_canary_flags(artifact: dict[str, Any]) -> bool:
    summary = artifact.get("summary") or {}
    trials = artifact.get("trials") or []
    n_summary = summary.get("n_canary_flags") or 0
    n_trials = sum(1 for trial in trials if isinstance(trial, dict) and trial.get("canary_flag"))
    return max(n_summary, n_trials) > 0


def _has_incomplete_disposal(artifact: dict[str, Any]) -> bool:
    for trial in artifact.get("trials") or []:
        row = _trial_mapping(trial)
        if row.get("workspace_disposed") is False:
            return True
    return False


def _self_check_is_invalid(artifact: dict[str, Any]) -> bool:
    provenance = artifact.get("provenance") or {}
    summary = artifact.get("summary") or {}
    if provenance.get("self_check_failed") or summary.get("gold_self_check_failed"):
        return True
    value = provenance.get("self_check", summary.get("self_check"))
    return value in _FAILED_SELF_CHECK_VALUES


def publication_receipt(artifact: dict[str, Any]) -> dict[str, Any]:
    """Is this individual Agent Cabinet result trustworthy enough to publish?"""
    provenance = artifact.get("provenance") or {}
    failing_fields: list[str] = []
    reasons: list[str] = []

    if artifact.get("dry_run"):
        reasons.append(PUBLISH_REFUSE_DRY_RUN)
        failing_fields.append("dry_run")

    missing = _missing_provenance_keys(provenance)
    if missing:
        reasons.append(PUBLISH_REFUSE_MISSING_PROVENANCE)
        failing_fields.extend(missing)

    if _fixture_reference_is_mutable(provenance.get("fixture_reference")):
        reasons.append(PUBLISH_REFUSE_MUTABLE_FIXTURE)
        failing_fields.append("fixture_reference")

    if _has_infrastructure_errors(artifact):
        reasons.append(PUBLISH_REFUSE_INFRASTRUCTURE_ERRORS)
        failing_fields.append("n_infra_errors")

    if _has_canary_flags(artifact):
        reasons.append(PUBLISH_REFUSE_CANARY_FLAGS)
        failing_fields.append("n_canary_flags")

    if _has_incomplete_disposal(artifact):
        reasons.append(PUBLISH_REFUSE_INCOMPLETE_DISPOSAL)
        failing_fields.append("workspace_disposed")

    if _self_check_is_invalid(artifact):
        reasons.append(PUBLISH_REFUSE_INVALID_SELF_CHECK)
        failing_fields.append("self_check")

    return {
        "policy_version": AGENT_CABINET_POLICY,
        "publishable": not reasons,
        "failing_fields": failing_fields,
        "reasons": reasons,
    }
