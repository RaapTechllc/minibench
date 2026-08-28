import gc
import hashlib
import json
import socket
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.agent_tasks import AgentResult, run_agent_trial
from agentbench.generated_features import (
    CATEGORY,
    FIXTURE_VERSION,
    NETWORK_POLICY,
    REQUIRED_CAPABILITIES,
    SCENARIO_TYPE,
    TEMPLATES,
    GeneratedFeatureEnvironment,
    GeneratedFeatureGoldAgent,
    build_generated_feature_artifact,
    generate_fixture,
    manifest_for,
    run_offline,
)


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


class _CacheGoldAgent(GeneratedFeatureGoldAgent):
    def execute(self, prompt, workspace, budget):
        result = super().execute(prompt, workspace, budget)
        (workspace / "app" / "__pycache__").mkdir(parents=True, exist_ok=True)
        (workspace / "app" / "__pycache__" / "cart.cpython-312.pyc").write_bytes(b"cache")
        (workspace / ".pytest_cache").mkdir(exist_ok=True)
        (workspace / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
        return result


class _PrivateHeapAgent:
    def __init__(self, marker):
        self.marker = marker

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        for candidate in gc.get_objects():
            if type(candidate).__name__ == "GeneratedFeatureFixture":
                self.marker.write_text("private fixture found", encoding="utf-8")
                for path, repaired in candidate.gold_files.items():
                    if candidate.baseline_files[path] != repaired:
                        (workspace / path).write_text(repaired, encoding="utf-8")
                break
        return AgentResult("completed", claimed_success=True)


class _ForgedProbeAgent:
    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        (workspace / "app/handler.py").write_text(
            """import inspect
def serve(client_id):
    frame = inspect.currentframe()
    while frame is not None:
        for value in frame.f_locals.values():
            if hasattr(value, 'send_bytes'):
                value.send_bytes(b'1')
                return {'ok': True, 'client': client_id, 'remaining': 0}
        frame = frame.f_back
    return {'ok': True, 'client': client_id}
""",
            encoding="utf-8",
        )
        return AgentResult("completed", claimed_success=True)


class _MainRequestOracleAgent:
    """Uses probe-global ``__main__.request`` instead of implementing the feature."""

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        (workspace / "app/notes.py").write_text(
            """import sys

def _hidden_request():
    return getattr(sys.modules.get("__main__"), "request", None)

class Notebook:
    def __init__(self):
        self._notes = []

    def add(self, title, body, tags=None):
        note = {
            "id": len(self._notes) + 1,
            "title": title,
            "body": body,
            "tags": list(tags or []),
        }
        self._notes.append(note)
        return note["id"]

    def get(self, note_id):
        note = self._notes[note_id - 1]
        return {"id": note["id"], "title": note["title"], "body": note["body"]}

    def all(self):
        return [self.get(note["id"]) for note in self._notes]

    def tags_for(self, note_id):
        request = _hidden_request()
        if request is None:
            return []
        return list(request["notes"][request["tagged_index"]][2])
""",
            encoding="utf-8",
        )
        (workspace / "app/search.py").write_text(
            """import sys

def find(notebook, query):
    request = getattr(sys.modules.get("__main__"), "request", None)
    if request is None:
        return []
    hits = []
    for index, (title, _body, tags) in enumerate(request["notes"], start=1):
        if query == request["tag_query"] and query in tags:
            hits.append(index)
        if query == request["title_query"] and query in title:
            hits.append(index)
    return hits
""",
            encoding="utf-8",
        )
        return AgentResult("completed", claimed_success=True)


class _LoopbackThenGoldAgent:
    def __init__(self, fixture, host, port, marker):
        self.fixture = fixture
        self.host = host
        self.port = port
        self.marker = marker

    def execute(self, prompt, workspace, budget):
        budget.consume(turns=1)
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5) as conn:
                conn.sendall(b"open")
            self.marker.write_text("connected", encoding="utf-8")
            for relative in self.fixture.mutable_paths:
                (workspace / relative).write_text(self.fixture.gold_files[relative], encoding="utf-8")
        except OSError:
            self.marker.write_text("denied", encoding="utf-8")
        return AgentResult("completed", claimed_success=True)


def _run(tmp_path, seed, agent, trial=1):
    fixture = generate_fixture(seed)
    return fixture, run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        agent,
        trial=trial,
    )


def _gold_writes(fixture, extra=None):
    writes = {path: fixture.gold_files[path] for path in fixture.mutable_paths}
    if extra:
        writes.update(extra)
    return writes


def test_seeded_generation_replays_and_covers_three_feature_families():
    first = generate_fixture(101)
    replay = generate_fixture(101)
    other = generate_fixture(102)

    assert first.public_snapshot() == replay.public_snapshot()
    assert first.gold_snapshot() == replay.gold_snapshot()
    assert first.public_snapshot() != other.public_snapshot()
    assert {generate_fixture(seed).template.name for seed in (0, 1, 2)} == {
        "promo-receipt",
        "tagged-search",
        "quota-guard",
    }
    assert {generate_fixture(seed).template.family for seed in (0, 1, 2)} == {
        "checkout-promotion",
        "label-lookup",
        "client-allowance",
    }


def test_templates_require_cross_file_behavior_not_one_line_constants():
    for seed in (0, 1, 2):
        fixture = generate_fixture(seed)
        changed = [
            path
            for path in fixture.mutable_paths
            if fixture.baseline_files[path] != fixture.gold_files[path]
        ]
        assert len(changed) >= 2
        total_diffs = 0
        for path in changed:
            before = fixture.baseline_files[path].splitlines()
            after = fixture.gold_files[path].splitlines()
            diffs = [right for left, right in zip(before, after) if left != right]
            diffs.extend(after[len(before) :] if len(after) > len(before) else before[len(after) :])
            total_diffs += len(diffs)
        assert total_diffs >= 6


def test_each_template_declares_identity_capabilities_budgets_and_denied_network():
    for template in TEMPLATES:
        assert template.network_policy == NETWORK_POLICY == "denied"
        assert template.capabilities == REQUIRED_CAPABILITIES
        assert "network" not in template.capabilities

    for seed in (0, 1, 2):
        fixture = generate_fixture(seed)
        manifest = manifest_for(fixture)
        assert manifest.fixture.reference == FIXTURE_VERSION
        assert "@" in manifest.fixture.reference
        assert not manifest.fixture.reference.endswith("@latest")
        assert manifest.required_capabilities == REQUIRED_CAPABILITIES
        assert manifest.budget.max_turns == 3
        assert manifest.budget.wall_time_seconds == 5
        assert manifest.budget.max_tokens == 300
        assert manifest.budget.max_cost_usd == 0.0
        assert manifest.category == CATEGORY
        assert manifest.scenario_type == SCENARIO_TYPE
        snapshot = json.loads(fixture.public_snapshot())
        assert snapshot["network_policy"] == "denied"
        assert snapshot["capabilities"] == list(REQUIRED_CAPABILITIES)


def test_public_prompt_does_not_expose_private_fixture_atoms():
    symbols = {
        "promotion_savings",
        "tags_for",
        "ALLOWANCE",
        "remaining",
        "checkout",
        "render",
        "find",
        "serve",
        "Cart",
        "Notebook",
    }
    for seed in (0, 1, 2, 101):
        fixture = generate_fixture(seed)
        prompt = fixture.prompt.lower()
        forbidden = {fixture.template.name, fixture.template.family, str(fixture.seed), *symbols}
        forbidden.update(fixture.mutable_paths)
        for path in fixture.mutable_paths:
            forbidden.update(Path(path).parts)
        assert all(atom.lower() not in prompt for atom in forbidden if atom)
        assert "gold" not in prompt
        assert "patch" not in prompt


def test_prepared_workspace_excludes_hidden_tests_and_gold(tmp_path):
    for seed in (0, 1, 2):
        fixture = generate_fixture(seed)
        environment = GeneratedFeatureEnvironment(fixture, tmp_path / str(seed))
        prepared = environment.prepare(manifest_for(fixture), trial=1)
        visible = "\n".join(
            path.read_text(encoding="utf-8")
            for path in prepared.handle.workspace.rglob("*")
            if path.is_file()
        )

        assert "assert " not in visible
        for path in fixture.mutable_paths:
            assert fixture.gold_files[path] not in visible
            assert (prepared.handle.workspace / path).read_text(encoding="utf-8") == fixture.baseline_files[path]
        assert not (prepared.handle.workspace / "tests").exists()
        assert fixture.oracle["kind"] not in prepared.prompt
        environment.dispose(prepared.handle)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_gold_passes_and_noop_fails_for_every_template(tmp_path, seed):
    fixture = generate_fixture(seed)
    gold = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path / "gold"),
        GeneratedFeatureGoldAgent(fixture),
        trial=1,
    )
    noop = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path / "noop"),
        _NoOpAgent(),
        trial=1,
    )
    assert gold.outcome == "success"
    assert gold.workspace_disposed is True
    assert noop.outcome == "verification_failed"
    assert noop.workspace_disposed is True


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_equivalent_non_gold_implementations_pass(tmp_path, seed):
    fixture = generate_fixture(seed)
    if fixture.template.name == "promo-receipt":
        writes = {
            "app/cart.py": fixture.gold_files["app/cart.py"].replace(
                "return self.subtotal() * percent // 100",
                "return percent * self.subtotal() // 100",
            ),
            "app/receipt.py": fixture.gold_files["app/receipt.py"],
        }
    elif fixture.template.name == "tagged-search":
        writes = {
            "app/notes.py": fixture.gold_files["app/notes.py"].replace(
                "return list(self._notes[note_id - 1]['tags'])",
                "return [*self._notes[note_id - 1]['tags']]",
            ),
            "app/search.py": (
                "def find(notebook, query):\n"
                "    found = []\n"
                "    for note in notebook.all():\n"
                "        labels = notebook.tags_for(note['id'])\n"
                "        if query in note['title'] or query in labels:\n"
                "            found.append(note['id'])\n"
                "    return found\n"
            ),
        }
    else:
        writes = {
            "app/clients.py": fixture.gold_files["app/clients.py"].replace(
                "    left = ALLOWANCE - count(client_id)\n    return left if left > 0 else 0\n",
                "    return max(0, ALLOWANCE - count(client_id))\n",
            ),
            "app/handler.py": fixture.gold_files["app/handler.py"],
        }
    assert any(writes[path] != fixture.gold_files[path] for path in writes)
    _, result = _run(tmp_path, seed, _WriteAgent(writes))
    assert result.outcome == "success"


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hard_coded_incomplete_and_overbroad_implementations_fail(tmp_path, seed):
    fixture = generate_fixture(seed)
    if fixture.template.name == "promo-receipt":
        hard_coded = {
            "app/cart.py": fixture.gold_files["app/cart.py"],
            "app/receipt.py": (
                "def render(cart, promotion=None):\n"
                f"    return {fixture.oracle['plain_receipt']!r} if promotion is None else 'due 1\\n'\n"
            ),
        }
    elif fixture.template.name == "tagged-search":
        hard_coded = {
            "app/notes.py": fixture.gold_files["app/notes.py"],
            "app/search.py": "def find(notebook, query):\n    return [2]\n",
        }
    else:
        hard_coded = {
            "app/clients.py": fixture.gold_files["app/clients.py"],
            "app/handler.py": (
                "def serve(client_id):\n"
                "    return {'ok': True, 'client': client_id, 'remaining': 1}\n"
            ),
        }

    incomplete_path = fixture.mutable_paths[0]
    incomplete = {incomplete_path: fixture.gold_files[incomplete_path]}
    overbroad = _gold_writes(fixture, {"app/build.py": "BUILD = 'tampered'\n"})

    hard = _run(tmp_path / "hard", seed, _WriteAgent(hard_coded))[1]
    missing = _run(tmp_path / "incomplete", seed, _WriteAgent(incomplete))[1]
    extra = _run(tmp_path / "overbroad", seed, _WriteAgent(overbroad))[1]

    assert hard.outcome == "verification_failed"
    assert missing.outcome == "verification_failed"
    assert extra.outcome == "verification_failed"


def test_oracle_rejects_test_only_and_new_files(tmp_path):
    fixture = generate_fixture(1)
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _WriteAgent({"tests/test_feature.py": "def test_ok():\n    assert True\n"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_treats_unreadable_candidate_as_failure(tmp_path):
    fixture = generate_fixture(0)
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _WriteAgent({"app/cart.py": b"\xff\xfe"}),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_oracle_bounds_private_probe_and_converts_child_failures(tmp_path):
    fixture = generate_fixture(0)
    environment = GeneratedFeatureEnvironment(fixture, tmp_path)
    prepared = environment.prepare(manifest_for(fixture), trial=1)
    (prepared.handle.workspace / "app/cart.py").write_text(
        "class Cart:\n    def add(self, sku, quantity):\n        while True:\n            pass\n",
        encoding="utf-8",
    )
    started = time.monotonic()
    result = environment.verify(prepared.handle)
    environment.dispose(prepared.handle)
    assert result.passed is False
    assert time.monotonic() - started < 5


def test_generated_feature_agent_cannot_discover_private_parent_heap(tmp_path):
    fixture = generate_fixture(0)
    marker = tmp_path / "private-heap-found"
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path / "workspace"),
        _PrivateHeapAgent(marker),
        trial=1,
    )
    assert result.outcome == "verification_failed"
    assert not marker.exists()


def test_candidate_frames_cannot_forge_private_probe_ipc(tmp_path):
    fixture = generate_fixture(2)
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _ForgedProbeAgent(),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_candidate_cannot_read_probe_request_from_main_to_bypass_hidden_oracle(tmp_path):
    fixture = generate_fixture(1)
    assert fixture.template.name == "tagged-search"
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _MainRequestOracleAgent(),
        trial=1,
    )
    assert result.outcome == "verification_failed"


def test_execute_spawn_enforces_denied_network_policy(tmp_path):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()
    accepted: list[bytes] = []

    def accept_once() -> None:
        server.settimeout(2)
        try:
            conn, _addr = server.accept()
            accepted.append(conn.recv(16))
            conn.close()
        except OSError:
            pass

    listener = threading.Thread(target=accept_once)
    listener.start()
    fixture = generate_fixture(0)
    marker = tmp_path / "network-status"
    try:
        result = run_agent_trial(
            manifest_for(fixture),
            GeneratedFeatureEnvironment(fixture, tmp_path / "workspace"),
            _LoopbackThenGoldAgent(fixture, host, port, marker),
            trial=1,
        )
    finally:
        listener.join(timeout=3)
        server.close()

    assert result.outcome == "verification_failed"
    assert marker.read_text(encoding="utf-8") == "denied"
    assert accepted == []


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
        GeneratedFeatureEnvironment(fixture, tmp_path).prepare(manifest, trial=1)


def test_prepare_rejects_foreign_cabinet_categories(tmp_path):
    fixture = generate_fixture(0)
    manifest = replace(manifest_for(fixture), category="repository-repair")
    with pytest.raises(ValueError, match="unsupported"):
        GeneratedFeatureEnvironment(fixture, tmp_path).prepare(manifest, trial=1)


def test_digest_mismatch_fails_preparation_and_cleans_workspace(tmp_path):
    fixture = generate_fixture(0)
    other = manifest_for(generate_fixture(1))
    mismatched = replace(manifest_for(fixture), fixture=replace(manifest_for(fixture).fixture, digest=other.fixture.digest))
    result = run_agent_trial(
        mismatched,
        GeneratedFeatureEnvironment(fixture, tmp_path),
        GeneratedFeatureGoldAgent(fixture),
        trial=1,
    )
    assert result.outcome == "preparation_failed"
    assert result.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_generated_harness_terminates_agent_at_wall_time_budget(tmp_path):
    fixture = generate_fixture(0)
    manifest = replace(manifest_for(fixture), budget=replace(manifest_for(fixture).budget, wall_time_seconds=1))
    started = time.monotonic()
    result = run_agent_trial(
        manifest,
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _SlowAgent(),
        trial=1,
    )
    assert result.outcome == "timeout"
    assert time.monotonic() - started < 1.8
    assert result.workspace_disposed is True


def test_oracle_ignores_runtime_cache_artifacts(tmp_path):
    fixture = generate_fixture(0)
    result = run_agent_trial(
        manifest_for(fixture),
        GeneratedFeatureEnvironment(fixture, tmp_path),
        _CacheGoldAgent(fixture),
        trial=1,
    )
    assert result.outcome == "success"


def test_repeated_prepare_is_isolated_and_identical(tmp_path):
    fixture = generate_fixture(1)
    manifest = manifest_for(fixture)
    environment = GeneratedFeatureEnvironment(fixture, tmp_path)
    first = environment.prepare(manifest, trial=1)
    second = environment.prepare(manifest, trial=2)
    assert first.handle.workspace != second.handle.workspace
    assert first.handle.initial_state_sha256 == second.handle.initial_state_sha256
    assert first.prompt == second.prompt == fixture.prompt
    environment.dispose(first.handle)
    environment.dispose(second.handle)
    assert environment.is_disposed(first.handle)
    assert environment.is_disposed(second.handle)


def test_artifact_uses_shared_shape_and_sanitizes_feature_provenance(tmp_path):
    fixture = generate_fixture(987654321)
    manifest = manifest_for(fixture)
    trial = run_agent_trial(
        manifest,
        GeneratedFeatureEnvironment(fixture, tmp_path),
        GeneratedFeatureGoldAgent(fixture),
        trial=1,
    )
    artifact = build_generated_feature_artifact(manifest, fixture, [trial])
    encoded = json.dumps(artifact)

    assert artifact["summary"]["evaluation_type"] == "agent_harness"
    assert artifact["provenance"]["fixture_version"] == FIXTURE_VERSION
    assert artifact["provenance"]["harness"] == "agent-cabinet-generated-feature"
    assert artifact["provenance"]["network_policy"] == "denied"
    assert artifact["provenance"]["mutation_template_sha256"] == hashlib.sha256(fixture.template.name.encode()).hexdigest()
    assert artifact["provenance"]["seed_sha256"] == fixture.seed_hash
    assert artifact["provenance"]["budgets"]["max_turns"] == 3
    assert artifact["provenance"]["terminal_outcome"] == "success"
    assert artifact["trials"][0]["detail"] == "pass"
    assert str(fixture.seed) not in encoded
    assert fixture.template.name not in encoded
    assert fixture.gold_files[fixture.mutable_paths[0]] not in encoded
    assert "hidden behavioral" not in encoded
    assert fixture.oracle["kind"] not in encoded
    for value in fixture.oracle.values():
        if isinstance(value, str) and len(value) > 3:
            assert value not in encoded


def test_offline_cli_requires_no_model_and_writes_artifact(tmp_path):
    out = tmp_path / "generated-feature.json"
    assert run_offline(5, 2, out) == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["dry_run"] is True
    assert artifact["summary"]["n_trials"] == 2
    assert artifact["summary"]["suite"] == "minibench-agent-generated-feature-v1"
    assert all(trial["workspace_disposed"] for trial in artifact["trials"])
