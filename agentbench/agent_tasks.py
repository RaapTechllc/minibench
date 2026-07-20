"""Offline task-environment contract for the Real-Work Agent Cabinet.

This module is deliberately separate from :mod:`agentbench.run`. Stateful
fixtures expose one lifecycle to the runner while keeping preparation and
hidden verification inside the environment implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from agentbench.stats import bootstrap_ci_by_task, pass_hat_k, percentile, wilson_ci


MANIFEST_VERSION = "1"
AGENT_GRADER_VERSION = "agent-1"
_INITIAL_CONTENT = "status=BROKEN\n"
_EXPECTED_CONTENT = "status=READY\n"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class AgentBudget:
    max_turns: int
    wall_time_seconds: int
    max_tokens: int
    max_cost_usd: float

    @classmethod
    def from_dict(cls, raw: Any) -> "AgentBudget":
        if not isinstance(raw, dict):
            raise ValueError("budget must be an object")
        max_turns = raw.get("max_turns")
        wall_time_seconds = raw.get("wall_time_seconds")
        max_tokens = raw.get("max_tokens")
        max_cost_usd = raw.get("max_cost_usd")
        if not isinstance(max_turns, int) or isinstance(max_turns, bool) or max_turns < 1:
            raise ValueError("budget.max_turns must be a positive integer")
        if (
            not isinstance(wall_time_seconds, int)
            or isinstance(wall_time_seconds, bool)
            or wall_time_seconds < 1
        ):
            raise ValueError("budget.wall_time_seconds must be a positive integer")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 0:
            raise ValueError("budget.max_tokens must be a non-negative integer")
        if (
            not isinstance(max_cost_usd, (int, float))
            or isinstance(max_cost_usd, bool)
            or max_cost_usd < 0
        ):
            raise ValueError("budget.max_cost_usd must be a non-negative number")
        return cls(max_turns, wall_time_seconds, max_tokens, float(max_cost_usd))


@dataclass(frozen=True)
class FixtureReference:
    reference: str
    digest: str

    @classmethod
    def from_dict(cls, raw: Any) -> "FixtureReference":
        if not isinstance(raw, dict):
            raise ValueError("fixture must be an object")
        reference = _required_text(raw.get("reference"), "fixture.reference")
        digest = _required_text(raw.get("digest"), "fixture.digest")
        if "@" not in reference or reference.endswith("@latest"):
            raise ValueError("fixture.reference must contain an immutable version")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("fixture.digest must be a sha256 digest")
        try:
            int(digest.removeprefix("sha256:"), 16)
        except ValueError as exc:
            raise ValueError("fixture.digest must be a sha256 digest") from exc
        return cls(reference=reference, digest=digest)


@dataclass(frozen=True)
class VerificationReference:
    strategy: str

    @classmethod
    def from_dict(cls, raw: Any) -> "VerificationReference":
        if not isinstance(raw, dict):
            raise ValueError("verification must be an object")
        return cls(strategy=_required_text(raw.get("strategy"), "verification.strategy"))


@dataclass(frozen=True)
class PreparationReference:
    strategy: str

    @classmethod
    def from_dict(cls, raw: Any) -> "PreparationReference":
        if not isinstance(raw, dict):
            raise ValueError("preparation must be an object")
        return cls(strategy=_required_text(raw.get("strategy"), "preparation.strategy"))


@dataclass(frozen=True)
class AgentTaskManifest:
    manifest_version: str
    suite: str
    task_id: str
    category: str
    scenario_type: str
    fixture: FixtureReference
    public_prompt: str
    preparation: PreparationReference
    verification: VerificationReference
    required_capabilities: tuple[str, ...]
    budget: AgentBudget
    private: bool

    @classmethod
    def from_dict(cls, raw: Any) -> "AgentTaskManifest":
        if not isinstance(raw, dict):
            raise ValueError("manifest must be an object")
        version = _required_text(raw.get("manifest_version"), "manifest_version")
        if version != MANIFEST_VERSION:
            raise ValueError(f"unsupported manifest_version: {version}")
        capabilities = raw.get("required_capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise ValueError("required_capabilities must be a non-empty list")
        normalized = tuple(
            _required_text(capability, "required_capabilities item")
            for capability in capabilities
        )
        private = raw.get("private")
        if not isinstance(private, bool):
            raise ValueError("private must be a boolean")
        return cls(
            manifest_version=version,
            suite=_required_text(raw.get("suite"), "suite"),
            task_id=_required_text(raw.get("task_id"), "task_id"),
            category=_required_text(raw.get("category"), "category"),
            scenario_type=_required_text(raw.get("scenario_type"), "scenario_type"),
            fixture=FixtureReference.from_dict(raw.get("fixture")),
            public_prompt=_required_text(raw.get("public_prompt"), "public_prompt"),
            preparation=PreparationReference.from_dict(raw.get("preparation")),
            verification=VerificationReference.from_dict(raw.get("verification")),
            required_capabilities=normalized,
            budget=AgentBudget.from_dict(raw.get("budget")),
            private=private,
        )


def load_agent_manifest(path: str | Path) -> AgentTaskManifest:
    return AgentTaskManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class EnvironmentHandle:
    workspace: Path
    initial_state_sha256: str


@dataclass(frozen=True)
class PreparedEnvironment:
    prompt: str
    handle: EnvironmentHandle


@dataclass(frozen=True)
class AgentResult:
    termination_reason: str
    claimed_success: bool = False
    turns: int = 1
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


class AgentBudgetGuard:
    """Adapter-side meter that rejects usage before a tool/model call exceeds limits."""

    def __init__(self, budget: AgentBudget):
        self._budget = budget
        self.turns = 0
        self.tokens = 0
        self.cost_usd = 0.0

    @property
    def max_turns(self) -> int:
        return self._budget.max_turns

    @property
    def wall_time_seconds(self) -> int:
        return self._budget.wall_time_seconds

    @property
    def max_tokens(self) -> int:
        return self._budget.max_tokens

    @property
    def max_cost_usd(self) -> float:
        return self._budget.max_cost_usd

    def consume(self, *, turns: int = 0, tokens: int = 0, cost_usd: float = 0.0) -> None:
        if turns < 0 or tokens < 0 or cost_usd < 0:
            raise ValueError("resource usage increments must be non-negative")
        if self.turns + turns > self.max_turns:
            raise TimeoutError("turn budget exceeded")
        if self.tokens + tokens > self.max_tokens:
            raise TimeoutError("token budget exceeded")
        if self.cost_usd + cost_usd > self.max_cost_usd:
            raise TimeoutError("cost budget exceeded")
        self.turns += turns
        self.tokens += tokens
        self.cost_usd += cost_usd


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    detail: str


class TaskEnvironment(Protocol):
    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment: ...
    def execute(
        self,
        agent: "AgentAdapter",
        handle: EnvironmentHandle,
        prompt: str,
        budget: AgentBudget,
    ) -> AgentResult: ...
    def verify(self, handle: EnvironmentHandle) -> VerificationResult: ...
    def dispose(self, handle: EnvironmentHandle | None) -> None: ...
    def is_disposed(self, handle: EnvironmentHandle | None) -> bool: ...


class AgentAdapter(Protocol):
    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult: ...


class OfflineTextEnvironment:
    """Small deterministic fixture used to exercise the complete lifecycle offline."""

    def __init__(self, root: str | Path | None = None, *, fail_preparation: bool = False):
        self.root = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="mba-root-"))
        self._owns_root = root is None
        self.fail_preparation = fail_preparation

    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment:
        if manifest.scenario_type != "offline-text-repair":
            raise ValueError(f"unsupported scenario_type: {manifest.scenario_type}")
        if manifest.preparation.strategy != "offline-text-repair-v1":
            raise ValueError(f"unsupported preparation strategy: {manifest.preparation.strategy}")
        workspace = self.root / f"{manifest.task_id}-trial-{trial}"
        try:
            workspace.mkdir(parents=True, exist_ok=False)
            fixture = workspace / "service.conf"
            fixture.write_bytes(_INITIAL_CONTENT.encode("utf-8"))
            digest = "sha256:" + hashlib.sha256(fixture.read_bytes()).hexdigest()
            if digest != manifest.fixture.digest:
                raise RuntimeError("prepared fixture does not match its declared digest")
            if self.fail_preparation:
                raise RuntimeError("scripted preparation failure")
            return PreparedEnvironment(manifest.public_prompt, EnvironmentHandle(workspace, digest))
        except BaseException:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def execute(
        self,
        agent: AgentAdapter,
        handle: EnvironmentHandle,
        prompt: str,
        budget: AgentBudget,
    ) -> AgentResult:
        return execute_agent_with_budget(agent, prompt, handle.workspace, budget)

    def verify(self, handle: EnvironmentHandle) -> VerificationResult:
        # Expected state lives in the verifier, never in the agent workspace.
        candidate = handle.workspace / "service.conf"
        passed = candidate.is_file() and candidate.read_text(encoding="utf-8") == _EXPECTED_CONTENT
        return VerificationResult(passed=passed, detail="hidden verification passed" if passed else "hidden verification failed")

    def dispose(self, handle: EnvironmentHandle | None) -> None:
        if handle is not None:
            shutil.rmtree(handle.workspace, ignore_errors=True)
        if self._owns_root:
            shutil.rmtree(self.root, ignore_errors=True)

    def is_disposed(self, handle: EnvironmentHandle | None) -> bool:
        return (handle is None or not handle.workspace.exists()) and (
            not self._owns_root or not self.root.exists()
        )


class DeterministicFakeAgent:
    """Reference adapter for CI; performs one known edit without network access."""

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        budget.consume(turns=1)
        target = workspace / "service.conf"
        target.write_text(target.read_text(encoding="utf-8").replace("BROKEN", "READY"), encoding="utf-8")
        return AgentResult(
            termination_reason="completed",
            claimed_success=True,
            turns=1,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
        )


_RESULT_PAYLOAD_LIMIT = 4096
_RESULT_FIELDS = {
    "termination_reason",
    "claimed_success",
    "turns",
    "tokens_in",
    "tokens_out",
    "cost_usd",
}


def _agent_result_payload(result: Any) -> bytes:
    if not isinstance(result, AgentResult):
        return b'{"kind":"malformed"}'
    try:
        return json.dumps(
            {"kind": "result", "result": asdict(result)},
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return b'{"kind":"malformed"}'


def _execute_agent_child(connection, agent, prompt, workspace, budget) -> None:
    try:
        connection.send_bytes(
            _agent_result_payload(agent.execute(prompt, workspace, AgentBudgetGuard(budget)))
        )
    except TimeoutError:
        connection.send_bytes(b'{"kind":"timeout"}')
    except BaseException:
        connection.send_bytes(b'{"kind":"error"}')
    finally:
        connection.close()


def execute_agent_with_budget(
    agent: AgentAdapter,
    prompt: str,
    workspace: Path,
    budget: AgentBudget,
    *,
    start_method: str | None = None,
) -> AgentResult:
    method = start_method or ("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
    context = multiprocessing.get_context(method)
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_execute_agent_child,
        args=(child, agent, prompt, workspace, budget),
        daemon=True,
    )
    try:
        process.start()
    except BaseException:
        parent.close()
        child.close()
        raise
    child.close()
    if not parent.poll(budget.wall_time_seconds):
        process.terminate()
        process.join()
        parent.close()
        raise TimeoutError("wall-time budget exceeded")
    try:
        payload = json.loads(parent.recv_bytes(_RESULT_PAYLOAD_LIMIT).decode("utf-8"))
    except (EOFError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = {"kind": "error"}
    finally:
        parent.close()
        process.join(timeout=1)
        if process.is_alive():
            process.terminate()
            process.join()
    if not isinstance(payload, dict) or not isinstance(payload.get("kind"), str):
        raise RuntimeError("invalid agent result protocol")
    kind = payload["kind"]
    if kind == "timeout":
        raise TimeoutError("agent reported timeout")
    if kind == "error":
        raise RuntimeError("agent execution failed")
    if kind == "malformed":
        return None
    raw_result = payload.get("result")
    if kind != "result" or set(payload) != {"kind", "result"} or not isinstance(raw_result, dict) or set(raw_result) != _RESULT_FIELDS:
        return None
    return AgentResult(**raw_result)


def _valid_agent_result(result: Any) -> bool:
    if not isinstance(result, AgentResult):
        return False
    if not isinstance(result.termination_reason, str) or not result.termination_reason.strip():
        return False
    if not isinstance(result.claimed_success, bool):
        return False
    if not isinstance(result.turns, int) or isinstance(result.turns, bool) or result.turns < 0:
        return False
    for value in (result.tokens_in, result.tokens_out):
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            return False
    return result.cost_usd is None or (
        isinstance(result.cost_usd, (int, float))
        and not isinstance(result.cost_usd, bool)
        and result.cost_usd >= 0
    )


def _over_budget(result: AgentResult, budget: AgentBudget) -> bool:
    tokens = (result.tokens_in or 0) + (result.tokens_out or 0)
    return (
        result.turns > budget.max_turns
        or tokens > budget.max_tokens
        or (result.cost_usd or 0.0) > budget.max_cost_usd
    )


@dataclass(frozen=True)
class AgentTrialResult:
    task_id: str
    category: str
    trial: int
    outcome: str
    passed: bool
    detail: str
    agent_claimed_success: bool
    termination_reason: str
    turns: int
    wall_time_ms: int
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    initial_state_sha256: str | None
    workspace_disposed: bool


def run_agent_trial(
    manifest: AgentTaskManifest,
    environment: TaskEnvironment,
    agent: AgentAdapter,
    *,
    trial: int,
) -> AgentTrialResult:
    """Run one prepare/execute/verify/dispose lifecycle with explicit outcomes."""
    started = time.monotonic()
    handle: EnvironmentHandle | None = None
    agent_result: AgentResult | None = None
    outcome = "preparation_failed"
    detail = "environment preparation failed"
    try:
        prepared = environment.prepare(manifest, trial)
        handle = prepared.handle
        try:
            candidate = environment.execute(agent, handle, prepared.prompt, manifest.budget)
            if not _valid_agent_result(candidate):
                outcome = "malformed_agent_result"
                detail = "agent returned a malformed terminal result"
            elif _over_budget(candidate, manifest.budget):
                agent_result = candidate
                outcome = "timeout"
                detail = "agent exceeded its resource budget"
            else:
                agent_result = candidate
                verification = environment.verify(handle)
                outcome = "success" if verification.passed else "verification_failed"
                detail = verification.detail
        except TimeoutError:
            outcome = "timeout"
            detail = "agent exceeded its resource budget"
        except Exception:
            outcome = "execution_failed"
            detail = "agent execution failed"
    except Exception:
        pass
    finally:
        environment.dispose(handle)

    elapsed = int((time.monotonic() - started) * 1000)
    return AgentTrialResult(
        task_id=manifest.task_id,
        category=manifest.category,
        trial=trial,
        outcome=outcome,
        passed=outcome == "success",
        detail=detail,
        agent_claimed_success=agent_result.claimed_success if agent_result else False,
        termination_reason=agent_result.termination_reason if agent_result else outcome,
        turns=agent_result.turns if agent_result else 0,
        wall_time_ms=elapsed,
        tokens_in=agent_result.tokens_in if agent_result else None,
        tokens_out=agent_result.tokens_out if agent_result else None,
        cost_usd=agent_result.cost_usd if agent_result else None,
        initial_state_sha256=handle.initial_state_sha256 if handle else None,
        workspace_disposed=environment.is_disposed(handle),
    )


def build_agent_artifact(
    manifest: AgentTaskManifest, trials: list[AgentTrialResult]
) -> dict[str, Any]:
    infra_outcomes = {"preparation_failed", "execution_failed"}
    scored = [trial for trial in trials if trial.outcome not in infra_outcomes]
    passes = sum(trial.passed for trial in scored)
    count = len(scored)
    rate = passes / count if count else 0.0
    ci_low, ci_high = wilson_ci(passes, count)
    boot_low, boot_high = bootstrap_ci_by_task([rate] if scored else [])
    costs = [trial.cost_usd for trial in scored if trial.cost_usd is not None]
    total_cost = sum(costs) if costs else None
    latencies = [float(trial.wall_time_ms) for trial in scored]
    effective_k = count
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
        "provenance": {
            "model": "deterministic-fake-agent",
            "harness": "minibench-reference",
            "harness_version": "1",
            "tool_contract": list(manifest.required_capabilities),
            "fixture_reference": manifest.fixture.reference,
            "fixture_digest": manifest.fixture.digest,
            "manifest_version": manifest.manifest_version,
            "private_split": manifest.private,
        },
        "summary": {
            "suite": manifest.suite,
            "moa_config": {
                "name": "minibench-reference",
                "self_moa": False,
                "models": ["deterministic-fake-agent"],
            },
            "grader_version": AGENT_GRADER_VERSION,
            "decoding": {
                "temperature": None,
                "top_p": None,
                "max_tokens": manifest.budget.max_tokens,
                "system_prompt": "agent-harness",
            },
            "n_tasks": 1,
            "n_trials": len(trials),
            "pass_hat_k_effective_k": effective_k,
            "pass_rate": round(rate, 4),
            "pass_capability": round(rate, 4),
            "pass_format": round(rate, 4),
            "pass_rate_ci95": [round(ci_low, 4), round(ci_high, 4)],
            "pass_rate_ci95_boot": [round(boot_low, 4), round(boot_high, 4)],
            "pass_hat_k": (
                round(pass_hat_k([passes], [count], k=effective_k), 4)
                if count
                else 0.0
            ),
            "n_infra_errors": len(trials) - len(scored),
            "n_canary_flags": 0,
            "cost_usd_total": round(total_cost, 6) if total_cost is not None else None,
            "cost_usd_per_task": round(total_cost, 6) if total_cost is not None else None,
            "latency_p50_ms": round(percentile(latencies, 50), 1),
            "latency_p95_ms": round(percentile(latencies, 95), 1),
            "evaluation_type": "agent_harness",
        },
        "trials": [asdict(trial) for trial in trials],
    }


def write_agent_artifact(
    path: str | Path,
    manifest: AgentTaskManifest,
    trials: list[AgentTrialResult],
) -> dict[str, Any]:
    artifact = build_agent_artifact(manifest, trials)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline Real-Work Agent tracer")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")

    manifest = load_agent_manifest(args.manifest)
    results = [
        run_agent_trial(manifest, OfflineTextEnvironment(), DeterministicFakeAgent(), trial=i)
        for i in range(1, args.trials + 1)
    ]
    artifact = write_agent_artifact(args.out, manifest, results)
    print(json.dumps(artifact["summary"], indent=2))
    return 0 if all(result.passed and result.workspace_disposed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
