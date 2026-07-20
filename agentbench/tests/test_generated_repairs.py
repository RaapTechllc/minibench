import hashlib
import gc
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


class _ForgedProbeAgent:
    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        (workspace / "app/cache.py").write_text(
            """import inspect
def cache_key(user, locale):
    frame = inspect.currentframe()
    while frame is not None:
        for value in frame.f_locals.values():
            if hasattr(value, 'send_bytes'):
                value.send_bytes(b'{\"completed\":true,\"outputs\":[\"x\",\"y\",\"x\",\"z\"]}')
                return 'broken'
        frame = frame.f_back
    return 'broken'
""",
            encoding="utf-8",
        )
        return AgentResult("completed", claimed_success=True)


class _PrivateHeapAgent:
    def __init__(self, marker):
        self.marker = marker

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        for candidate in gc.get_objects():
            if type(candidate).__name__ == "GeneratedRepairFixture":
                self.marker.write_text("private fixture found", encoding="utf-8")
                for path, repaired in candidate.repaired_files.items():
                    if candidate.broken_files[path] != repaired:
                        (workspace / path).write_text(repaired, encoding="utf-8")
                break
        return AgentResult("completed", claimed_success=True)


class _NoOpAgent:
    def execute(self, prompt, workspace, budget):
        return AgentResult("completed", claimed_success=True)


class _WriteAgent:
    def __init__(self, writes):
        self.writes = writes

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        for relative, content in self.writes.items():
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
        return AgentResult("completed", claimed_success=True)


class _SlowAgent:
    def execute(self, prompt, workspace, budget):
        time.sleep(2)
        return AgentResult("completed", claimed_success=True)


class _CacheRepairAgent(_WriteAgent):
    def execute(self, prompt, workspace, budget):
        result = super().execute(prompt, workspace, budget)
        (workspace / "app" / "__pycache__").mkdir(parents=True)
        (workspace / "app" / "__pycache__" / "records.cpython-312.pyc").write_bytes(b"cache")
        (workspace / ".pytest_cache").mkdir()
        (workspace / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
        return result


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


def test_prepared_workspace_excludes_private_assertions(tmp_path):
    for seed in (0, 1, 2):
        fixture = generate_fixture(seed)
        environment = GeneratedRepairEnvironment(fixture, tmp_path / str(seed))
        prepared = environment.prepare(manifest_for(fixture), trial=1)
        visible = "\n".join(
            path.read_text(encoding="utf-8")
            for path in prepared.handle.workspace.rglob("*")
            if path.is_file()
        )

        assert "assert " not in visible
        assert fixture.probe not in visible
        assert not (prepared.handle.workspace / "tests").exists()
        environment.dispose(prepared.handle)


def test_gold_repair_passes_and_noop_fails(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)

    passed = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "pass"),
        GeneratedRepairGoldAgent(),
        trial=1,
    )
    assert passed.passed is True

    failed = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "noop"),
        _NoOpAgent(),
        trial=1,
    )
    assert failed.outcome == "verification_failed"


@pytest.mark.parametrize(
    ("seed", "equivalent_source"),
    [
        (0, "def timeout(value=None):\n    if value is None:\n        return 46\n    return value\n"),
        (1, "def fields(line):\n    return [part for part in line.split(',')]\n"),
        (2, "def cache_key(user, locale):\n    return '{}|{}'.format(user, locale)\n"),
    ],
)
def test_oracle_accepts_behaviorally_equivalent_non_gold_repairs(tmp_path, seed, equivalent_source):
    fixture = generate_fixture(seed)

    target = next(
        path for path, content in fixture.repaired_files.items()
        if fixture.broken_files[path] != content
    )
    assert equivalent_source != fixture.repaired_files[target]

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path / str(seed)),
        _WriteAgent({target: equivalent_source}),
        trial=1,
    )

    assert result.outcome == "success"


def test_oracle_rejects_changed_seed_specific_default(tmp_path):
    fixture = generate_fixture(0)

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path),
        _WriteAgent({"app/config.py": "def timeout(value=None):\n    return 44 if value is None else value\n"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_treats_probe_errors_as_failed_repairs(tmp_path):
    fixture = generate_fixture(1)

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path),
        _WriteAgent({"app/records.py": "def unrelated():\n    return []\n"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


@pytest.mark.parametrize(
    "source",
    ["raise SystemExit(0)\n", "def fields(line):\n    while True:\n        pass\n"],
)
def test_oracle_bounds_private_probe_and_converts_child_failures(tmp_path, source):
    fixture = generate_fixture(1)
    environment = GeneratedRepairEnvironment(fixture, tmp_path)
    prepared = environment.prepare(manifest_for(fixture), trial=1)
    (prepared.handle.workspace / "app/records.py").write_text(source, encoding="utf-8")
    started = time.monotonic()
    result = environment.verify(prepared.handle)
    environment.dispose(prepared.handle)

    assert result.passed is False
    assert time.monotonic() - started < 5


def test_oracle_converts_unreadable_candidate_to_verification_failure(tmp_path):
    fixture = generate_fixture(1)

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path),
        _WriteAgent({"app/records.py": b"\xff\xfe"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_keeps_gold_source_out_of_candidate_frames(tmp_path):
    fixture = generate_fixture(0)
    gold = fixture.repaired_files["app/config.py"]
    hostile = """import inspect
def timeout(value=None):
    frame = inspect.currentframe()
    while frame is not None:
        if any(candidate == %r for candidate in frame.f_locals.values()):
            return 46 if value is None else value
        frame = frame.f_back
    return -1
""" % gold

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path),
        _WriteAgent({"app/config.py": hostile}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_never_unpickles_candidate_controlled_outputs(tmp_path):
    fixture = generate_fixture(1)
    marker = tmp_path / "pickle-executed"
    hostile = """import os
class Hostile:
    def __reduce__(self):
        return (os.system, (%r,))
def fields(line):
    return Hostile()
""" % f"touch {marker}"

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path / "workspace"),
        _WriteAgent({"app/records.py": hostile}),
        trial=1,
    )
    assert result.outcome == "verification_failed"
    assert not marker.exists()


def test_candidate_frames_cannot_forge_private_probe_ipc(tmp_path):
    fixture = generate_fixture(2)

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path),
        _ForgedProbeAgent(),
        trial=1,
    )

    assert result.outcome == "verification_failed"


def test_generated_repair_agent_cannot_discover_private_parent_heap(tmp_path):
    fixture = generate_fixture(0)
    marker = tmp_path / "private-heap-found"

    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedRepairEnvironment(fixture, tmp_path / "workspace"),
        _PrivateHeapAgent(marker),
        trial=1,
    )

    assert result.outcome == "verification_failed"
    assert not marker.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [("fixture", "wrong-fixture"), ("preparation", "wrong-preparation"), ("verification", "wrong-verification")],
)
def test_prepare_rejects_incompatible_manifest_metadata(tmp_path, field, value):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)
    if field == "fixture":
        manifest = replace(manifest, fixture=replace(manifest.fixture, reference=value))
    elif field == "preparation":
        manifest = replace(manifest, preparation=replace(manifest.preparation, strategy=value))
    else:
        manifest = replace(manifest, verification=replace(manifest.verification, strategy=value))

    with pytest.raises(ValueError, match="unsupported"):
        GeneratedRepairEnvironment(fixture, tmp_path).prepare(manifest, trial=1)


def test_digest_mismatch_fails_preparation_and_cleans_workspace(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)
    other = manifest_for(generate_fixture(1))
    mismatched = replace(manifest, fixture=replace(manifest.fixture, digest=other.fixture.digest))
    result = run_agent_trial(
        mismatched,
        GeneratedRepairEnvironment(fixture, tmp_path),
        GeneratedRepairGoldAgent(),
        trial=1,
    )
    assert result.outcome == "preparation_failed"
    assert result.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_generated_harness_terminates_agent_at_wall_time_budget(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)
    manifest = replace(manifest, budget=replace(manifest.budget, wall_time_seconds=1))

    started = time.monotonic()
    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path),
        _SlowAgent(),
        trial=1,
    )

    assert result.outcome == "timeout"
    assert time.monotonic() - started < 1.8
    assert result.workspace_disposed is True


def test_oracle_ignores_runtime_cache_artifacts(tmp_path):
    fixture = generate_fixture(1)
    manifest = manifest_for(fixture)

    target = next(
        path for path, content in fixture.repaired_files.items()
        if fixture.broken_files[path] != content
    )

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path),
        _CacheRepairAgent({target: fixture.repaired_files[target]}),
        trial=1,
    )

    assert result.outcome == "success"


@pytest.mark.parametrize("seed", [1, 2])
def test_oracle_rejects_symptom_only_and_collateral_repairs(tmp_path, seed):
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)

    target = next(path for path in fixture.repaired_files if path.startswith("app/"))

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / str(seed)),
        _WriteAgent({target: fixture.repaired_files[target], "README.md": "symptom hidden\n"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_rejects_test_only_symptom_suppression(tmp_path):
    fixture = generate_fixture(1)
    manifest = manifest_for(fixture)

    result = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "test-only"),
        _WriteAgent({"tests/test_symptom.py": "def test_symptom_is_gone():\n    assert True\n"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_artifact_has_sanitized_generated_provenance(tmp_path):
    fixture = generate_fixture(987654321)
    manifest = manifest_for(fixture)
    trial = run_agent_trial(
        manifest,
        GeneratedRepairEnvironment(fixture, tmp_path / "artifact"),
        GeneratedRepairGoldAgent(),
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
