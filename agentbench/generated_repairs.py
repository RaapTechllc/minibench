"""Offline, seeded repository-repair tasks for the Agent Cabinet harness.

The generated fixture is intentionally small but shaped like a real Python
repository.  Only the symptom prompt and broken files are public; the repair,
mutation metadata, and oracle expectations remain in this module's private
fixture state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agentbench.agent_tasks import (
    AGENT_GRADER_VERSION,
    AgentAdapter,
    AgentBudget,
    AgentBudgetGuard,
    AgentResult,
    AgentTaskManifest,
    EnvironmentHandle,
    PreparedEnvironment,
    TaskEnvironment,
    VerificationResult,
    build_agent_artifact,
    execute_agent_with_budget,
    run_agent_trial,
)


FIXTURE_VERSION = "generated-repository-repair@1"
HARNESS = "agent-cabinet-generated-repair"
_BUDGET = AgentBudget(max_turns=3, wall_time_seconds=5, max_tokens=300, max_cost_usd=0.0)
_IGNORED_RUNTIME_PATH_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


@dataclass(frozen=True)
class RepairTemplate:
    name: str
    build: Callable[[int], tuple[dict[str, str], dict[str, str], str, str]]


@dataclass(frozen=True)
class GeneratedRepairFixture:
    seed: int
    template: RepairTemplate
    broken_files: dict[str, str]
    repaired_files: dict[str, str]
    prompt: str
    probe: str

    @property
    def seed_hash(self) -> str:
        return hashlib.sha256(str(self.seed).encode()).hexdigest()

    @property
    def template_hash(self) -> str:
        return hashlib.sha256(self.template.name.encode()).hexdigest()

    def public_snapshot(self) -> bytes:
        payload = {"version": FIXTURE_VERSION, "files": self.broken_files, "prompt": self.prompt}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def gold_snapshot(self) -> bytes:
        payload = {"version": FIXTURE_VERSION, "files": self.repaired_files, "probe": self.probe}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _variant(seed: int, label: str) -> str:
    return hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()[:8]


def _config_template(seed: int) -> tuple[dict[str, str], dict[str, str], str, str]:
    timeout = 10 + int(_variant(seed, "timeout"), 16) % 50
    broken = f"def timeout(value=None):\n    return value or {timeout}\n"
    repaired = f"def timeout(value=None):\n    return {timeout} if value is None else value\n"
    files = {
        "pyproject.toml": "[project]\nname = 'cabinet-sample'\n",
        "app/config.py": broken,
    }
    repaired_files = {**files, "app/config.py": repaired}
    return files, repaired_files, "A configuration value is ignored when it is explicitly set to zero.", "timeout(0) == 0"


def _records_template(seed: int) -> tuple[dict[str, str], dict[str, str], str, str]:
    marker = _variant(seed, "records")
    broken = "def fields(line):\n    return line.split(';')\n"
    repaired = "def fields(line):\n    return line.split(',')\n"
    files = {
        "pyproject.toml": "[project]\nname = 'cabinet-sample'\n",
        "app/records.py": broken,
        "app/version.py": f"VERSION = '{marker}'\n",
    }
    repaired_files = {**files, "app/records.py": repaired}
    return files, repaired_files, "A two-column record is returned as one field instead of two.", "fields('a,b') == ['a', 'b']"


def _cache_template(seed: int) -> tuple[dict[str, str], dict[str, str], str, str]:
    prefix = _variant(seed, "cache")
    broken = "def cache_key(user, locale):\n    return f'{user}'\n"
    repaired = "def cache_key(user, locale):\n    return f'{user}:{locale}'\n"
    files = {
        "pyproject.toml": "[project]\nname = 'cabinet-sample'\n",
        "app/cache.py": broken,
        "app/build.py": f"BUILD = '{prefix}'\n",
    }
    repaired_files = {**files, "app/cache.py": repaired}
    return files, repaired_files, "Two users in different locales receive the same cached response.", "cache_key('u', 'en') != cache_key('u', 'fr')"


TEMPLATES = (
    RepairTemplate("explicit-zero-default", _config_template),
    RepairTemplate("csv-delimiter", _records_template),
    RepairTemplate("locale-cache-key", _cache_template),
)


def generate_fixture(seed: int, *, fixture_version: str = FIXTURE_VERSION) -> GeneratedRepairFixture:
    if fixture_version != FIXTURE_VERSION:
        raise ValueError(f"unsupported fixture version: {fixture_version}")
    template = TEMPLATES[seed % len(TEMPLATES)]
    broken, repaired, prompt, probe = template.build(seed)
    return GeneratedRepairFixture(seed, template, broken, repaired, prompt, probe)


def manifest_for(fixture: GeneratedRepairFixture) -> AgentTaskManifest:
    digest = "sha256:" + hashlib.sha256(fixture.public_snapshot()).hexdigest()
    return AgentTaskManifest.from_dict(
        {
            "manifest_version": "1",
            "suite": "minibench-agent-generated-repair-v1",
            "task_id": f"mba-generated-{fixture.seed_hash[:16]}",
            "category": "repository-repair",
            "scenario_type": "generated-repository-repair",
            "fixture": {"reference": FIXTURE_VERSION, "digest": digest},
            "public_prompt": fixture.prompt,
            "preparation": {"strategy": FIXTURE_VERSION},
            "verification": {"strategy": FIXTURE_VERSION},
            "required_capabilities": ["filesystem", "code-editing"],
            "budget": {
                "max_turns": _BUDGET.max_turns,
                "wall_time_seconds": _BUDGET.wall_time_seconds,
                "max_tokens": _BUDGET.max_tokens,
                "max_cost_usd": _BUDGET.max_cost_usd,
            },
            "private": True,
        }
    )


def _is_runtime_artifact(path: Path) -> bool:
    return any(part in _IGNORED_RUNTIME_PATH_PARTS for part in path.parts)


class GeneratedRepairEnvironment(TaskEnvironment):
    def __init__(self, fixture: GeneratedRepairFixture, root: str | Path | None = None):
        self.fixture = fixture
        self.root = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="mba-repair-"))
        self._owns_root = root is None

    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment:
        if manifest.scenario_type != "generated-repository-repair":
            raise ValueError("unsupported scenario type")
        if manifest.fixture.reference != FIXTURE_VERSION:
            raise ValueError("unsupported fixture reference")
        if manifest.preparation.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported preparation strategy")
        if manifest.verification.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported verification strategy")
        workspace = self.root / f"{manifest.task_id}-trial-{trial}"
        workspace.mkdir(parents=True, exist_ok=False)
        try:
            for relative, content in self.fixture.broken_files.items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(self.fixture.public_snapshot()).hexdigest()
            if digest != manifest.fixture.digest:
                raise RuntimeError("generated fixture digest mismatch")
            return PreparedEnvironment(manifest.public_prompt, EnvironmentHandle(workspace, digest))
        except BaseException:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def execute(self, agent: AgentAdapter, handle: EnvironmentHandle, prompt: str, budget: AgentBudget) -> AgentResult:
        return execute_agent_with_budget(agent, prompt, handle.workspace, budget)

    def verify(self, handle: EnvironmentHandle) -> VerificationResult:
        actual = {
            str(path.relative_to(handle.workspace)): path.read_text(encoding="utf-8")
            for path in handle.workspace.rglob("*")
            if path.is_file() and not _is_runtime_artifact(path.relative_to(handle.workspace))
        }
        target = next(
            path for path, content in self.fixture.repaired_files.items()
            if content != self.fixture.broken_files[path]
        )
        if set(actual) != set(self.fixture.broken_files):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if any(
            actual[path] != content
            for path, content in self.fixture.broken_files.items()
            if path != target
        ):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if actual[target] == self.fixture.broken_files[target]:
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        namespace: dict[str, Any] = {}
        try:
            exec(compile(actual[target], target, "exec"), namespace)  # fixture source is generated locally
            if self.fixture.template.name == "explicit-zero-default":
                expected_namespace: dict[str, Any] = {}
                exec(compile(self.fixture.repaired_files[target], target, "exec"), expected_namespace)
                behavior_passed = (
                    namespace["timeout"]() == expected_namespace["timeout"]()
                    and namespace["timeout"](0) == 0
                    and namespace["timeout"](7) == 7
                )
            elif self.fixture.template.name == "csv-delimiter":
                behavior_passed = (
                    namespace["fields"]("a,b") == ["a", "b"]
                    and namespace["fields"]("a,b,c") == ["a", "b", "c"]
                    and namespace["fields"]("single") == ["single"]
                )
            else:
                behavior_passed = (
                    namespace["cache_key"]("u", "en") != namespace["cache_key"]("u", "fr")
                    and namespace["cache_key"]("u", "en") == namespace["cache_key"]("u", "en")
                    and namespace["cache_key"]("u", "en") != namespace["cache_key"]("v", "en")
                )
        except Exception:
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if not behavior_passed:
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        return VerificationResult(True, "hidden behavioral and regression checks passed")

    def dispose(self, handle: EnvironmentHandle | None) -> None:
        if handle is not None:
            shutil.rmtree(handle.workspace, ignore_errors=True)
        if self._owns_root:
            shutil.rmtree(self.root, ignore_errors=True)

    def is_disposed(self, handle: EnvironmentHandle | None) -> bool:
        return (handle is None or not handle.workspace.exists()) and (not self._owns_root or not self.root.exists())


class GeneratedRepairGoldAgent:
    """Offline-only reference agent; it is never used to grade model output."""

    def __init__(self, fixture: GeneratedRepairFixture):
        self.fixture = fixture

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        budget.consume(turns=1)
        target = {path for path, content in self.fixture.broken_files.items() if self.fixture.repaired_files[path] != content}
        for path in target:
            (workspace / path).write_text(self.fixture.repaired_files[path], encoding="utf-8")
        return AgentResult("completed", claimed_success=True, turns=1, tokens_in=0, tokens_out=0, cost_usd=0.0)


def build_generated_artifact(manifest: AgentTaskManifest, fixture: GeneratedRepairFixture, trials: list[Any]) -> dict[str, Any]:
    artifact = build_agent_artifact(manifest, trials)
    artifact["provenance"].update(
        {
            "fixture_version": FIXTURE_VERSION,
            "mutation_template_sha256": fixture.template_hash,
            "seed_sha256": fixture.seed_hash,
            "harness": HARNESS,
            "harness_version": AGENT_GRADER_VERSION,
            "budgets": {"max_turns": _BUDGET.max_turns, "wall_time_seconds": _BUDGET.wall_time_seconds, "max_tokens": _BUDGET.max_tokens, "max_cost_usd": _BUDGET.max_cost_usd},
            "terminal_outcome": "success" if artifact["summary"]["pass_rate"] == 1.0 else "verification_failed",
        }
    )
    for trial in artifact["trials"]:
        trial["detail"] = "pass" if trial["passed"] else "fail"
    return artifact


def run_offline(seed: int, trials: int, out: str | Path) -> int:
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)
    environment = GeneratedRepairEnvironment(fixture)
    results = [run_agent_trial(manifest, environment, GeneratedRepairGoldAgent(fixture), trial=i) for i in range(1, trials + 1)]
    artifact = build_generated_artifact(manifest, fixture, results)
    Path(out).write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], indent=2))
    return 0 if all(result.passed and result.workspace_disposed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a seeded generated repository-repair task offline.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")
    return run_offline(args.seed, args.trials, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
