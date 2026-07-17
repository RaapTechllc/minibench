import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.agent_tasks import AgentResult, run_agent_trial
from agentbench.generated_repairs import (
    FIXTURE_VERSION,
    GeneratedRepairEnvironment,
    GeneratedRepairGoldAgent,
    build_generated_artifact,
    generate_fixture,
    manifest_for,
    run_offline,
)


def test_seeded_generation_replays_byte_for_byte_and_varies_validly():
    first = generate_fixture(101)
    replay = generate_fixture(101)
    other = generate_fixture(102)

    assert first.public_snapshot() == replay.public_snapshot()
    assert first.gold_snapshot() == replay.gold_snapshot()
    assert first.public_snapshot() != other.public_snapshot()
    assert other.broken_files
    assert len({generate_fixture(seed).template.name for seed in (0, 1, 2)}) == 3


def test_public_prompt_does_not_expose_private_fixture_atoms():
    for seed in (0, 1, 2, 101):
        fixture = generate_fixture(seed)
        prompt = fixture.prompt.lower()
        changed_paths = {
            path
            for path, content in fixture.repaired_files.items()
            if fixture.broken_files[path] != content
        }
        forbidden = {fixture.template.name, str(fixture.seed), fixture.probe, *changed_paths}
        for path in changed_paths:
            forbidden.update(Path(path).parts)
        for text in fixture.repaired_files.values():
            forbidden.update(token for token in ("timeout", "fields", "cache_key", "split(',')") if token in text)

        assert all(atom.lower() not in prompt for atom in forbidden if atom)
        assert "repair" not in prompt


def test_gold_repair_passes_and_noop_fails(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)

    passed = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "pass"),
        GeneratedRepairGoldAgent(fixture),
        trial=1,
    )
    assert passed.passed is True

    class NoOp:
        def execute(self, prompt, workspace, budget):
            return AgentResult("completed", claimed_success=True)

    failed = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "noop"),
        NoOp(),
        trial=1,
    )
    assert failed.outcome == "verification_failed"


def test_generated_harness_terminates_agent_at_wall_time_budget(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)
    manifest = replace(manifest, budget=replace(manifest.budget, wall_time_seconds=1))

    class SlowAgent:
        def execute(self, prompt, workspace, budget):
            time.sleep(2)
            return AgentResult("completed", claimed_success=True)

    started = time.monotonic()
    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path),
        SlowAgent(),
        trial=1,
    )

    assert result.outcome == "timeout"
    assert time.monotonic() - started < 1.8
    assert result.workspace_disposed is True


def test_oracle_ignores_runtime_cache_artifacts(tmp_path):
    fixture = generate_fixture(1)
    manifest = manifest_for(fixture)

    class CorrectRepairWithCaches:
        def execute(self, prompt, workspace, budget):
            budget.consume(turns=1)
            target = next(
                path for path, content in fixture.repaired_files.items()
                if fixture.broken_files[path] != content
            )
            (workspace / target).write_text(fixture.repaired_files[target], encoding="utf-8")
            (workspace / "app" / "__pycache__").mkdir(parents=True)
            (workspace / "app" / "__pycache__" / "records.cpython-312.pyc").write_bytes(b"cache")
            (workspace / ".pytest_cache").mkdir()
            (workspace / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
            return AgentResult("completed", claimed_success=True)

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path),
        CorrectRepairWithCaches(),
        trial=1,
    )

    assert result.outcome == "success"


@pytest.mark.parametrize("seed", [1, 2])
def test_oracle_rejects_symptom_only_and_collateral_repairs(tmp_path, seed):
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)

    class BadRepair:
        def execute(self, prompt, workspace, budget):
            budget.consume(turns=1)
            target = next(path for path in fixture.repaired_files if path.startswith("app/"))
            (workspace / target).write_text(fixture.repaired_files[target], encoding="utf-8")
            (workspace / "README.md").write_text("symptom hidden\n", encoding="utf-8")
            return AgentResult("completed", claimed_success=True)

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / str(seed)),
        BadRepair(),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_rejects_test_only_symptom_suppression(tmp_path):
    fixture = generate_fixture(1)
    manifest = manifest_for(fixture)

    class SymptomOnly:
        def execute(self, prompt, workspace, budget):
            budget.consume(turns=1)
            test_file = next(path for path in fixture.broken_files if path.startswith("tests/"))
            (workspace / test_file).write_text("def test_symptom_is_gone():\n    assert True\n", encoding="utf-8")
            return AgentResult("completed", claimed_success=True)

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "test-only"),
        SymptomOnly(),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_artifact_has_sanitized_generated_provenance(tmp_path):
    fixture = generate_fixture(987654321)
    manifest = manifest_for(fixture)
    trial = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "artifact"),
        GeneratedRepairGoldAgent(fixture),
        trial=1,
    )
    artifact = build_generated_artifact(manifest, fixture, [trial])
    encoded = json.dumps(artifact)

    assert artifact["provenance"]["fixture_version"] == FIXTURE_VERSION
    assert artifact["provenance"]["mutation_template_sha256"] == hashlib.sha256(fixture.template.name.encode()).hexdigest()
    assert artifact["provenance"]["seed_sha256"] == fixture.seed_hash
    assert artifact["provenance"]["harness"] == "agent-cabinet-generated-repair"
    assert artifact["provenance"]["budgets"]["max_turns"] == 3
    assert artifact["provenance"]["terminal_outcome"] == "success"
    assert str(fixture.seed) not in encoded
    assert fixture.probe not in encoded
    assert "hidden behavioral" not in encoded
    assert fixture.template.name not in encoded
    assert "app/" not in encoded


def test_offline_cli_requires_no_model_and_writes_artifact(tmp_path):
    out = tmp_path / "generated.json"
    assert run_offline(5, 2, out) == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["dry_run"] is True
    assert artifact["summary"]["n_trials"] == 2
    assert all(trial["workspace_disposed"] for trial in artifact["trials"])
