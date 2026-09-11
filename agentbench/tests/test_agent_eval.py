"""Genuine-path dogfood: model adapter + product receipt, honestly labeled.

Injected transports and fake agents stay ``dry_run: true``. Paid providers are
refused. This module does not call OpenRouter or Ollama Cloud.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentbench.agent_cabinet import (
    EVALUATION_CLASS_INJECTED_TRANSPORT,
    EVALUATION_CLASS_LIVE_LOCAL,
    EVALUATION_CLASS_OFFLINE_REFERENCE,
    PRODUCT_RECEIPT_KIND,
    PUBLISH_REFUSE_DRY_RUN,
    honest_dry_run,
    product_receipt,
    publication_receipt,
    scorecard_from_artifact,
)
from agentbench.agent_eval import (
    FilesystemModelAgent,
    PAID_REFUSAL,
    ScriptedTransport,
    fixture_self_check,
    load_scripted_reply,
    main,
    parse_model_writes,
    resolve_run_mode,
    run_dogfood,
)
from agentbench.agent_tasks import (
    AgentBudgetGuard,
    AgentBudget,
    DeterministicFakeAgent,
    OfflineTextEnvironment,
    build_agent_artifact,
    load_agent_manifest,
    run_agent_trial,
)
from agentbench.client import InfraError, OpenAICompatClient
from agentbench.import_results import ImportRefused, artifact_to_payload


DOGFOOD = Path(__file__).resolve().parents[1] / "tasks" / "minibench-agent-v1-dogfood.json"
SCRIPTED = Path(__file__).resolve().parents[1] / "tasks" / "dogfood-scripted-reply.json"
OFFLINE = Path(__file__).resolve().parents[1] / "tasks" / "minibench-agent-v1-offline.json"


def _scripted_client(text: str) -> OpenAICompatClient:
    return OpenAICompatClient(provider="ollama", transport=ScriptedTransport(text))


def test_reuse_preflight_prefers_existing_contract():
    preflight = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "validation"
        / "agent-eval-reuse-preflight.md"
    ).read_text(encoding="utf-8")
    assert "AgentAdapter.execute" in preflight
    assert "publication_receipt" in preflight
    assert "OpenAICompatClient" in preflight
    assert "Do not add a second lifecycle" in preflight or "not a new" in preflight.lower()


def test_scripted_reply_and_write_parser():
    text = load_scripted_reply(SCRIPTED)
    writes = parse_model_writes(text)
    assert writes == {"service.conf": "status=READY\n"}
    wrapped = parse_model_writes('Sure.\n{"writes": {"service.conf": "status=READY\\n"}}\n')
    assert wrapped["service.conf"] == "status=READY\n"
    assert parse_model_writes("not json") == {}
    assert parse_model_writes('{"writes": {"../escape": "x"}}') == {"../escape": "x"}


def test_model_agent_applies_model_writes_not_gold(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "service.conf").write_text("status=BROKEN\n", encoding="utf-8")
    agent = FilesystemModelAgent(
        _scripted_client(json.dumps({"writes": {"service.conf": "status=READY\n"}})),
        "injected-filesystem-model",
    )
    result = agent.execute(
        "Repair service.conf so the service status is READY.",
        workspace,
        AgentBudgetGuard(AgentBudget(1, 5, 512, 0.0)),
    )
    assert result.claimed_success is True
    assert (workspace / "service.conf").read_text(encoding="utf-8") == "status=READY\n"
    assert result.tokens_in == 8
    assert result.cost_usd == 0.0


def test_model_agent_wrong_write_is_not_forced_to_gold(tmp_path):
    manifest = load_agent_manifest(DOGFOOD)
    agent = FilesystemModelAgent(
        _scripted_client(json.dumps({"writes": {"service.conf": "status=BROKEN\n"}})),
        "injected-filesystem-model",
    )
    trial = run_agent_trial(manifest, OfflineTextEnvironment(tmp_path), agent, trial=1)
    assert trial.passed is False
    assert trial.outcome == "verification_failed"
    assert trial.workspace_disposed is True


def test_model_agent_rejects_path_escape(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "service.conf").write_text("status=BROKEN\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    agent = FilesystemModelAgent(
        _scripted_client(json.dumps({"writes": {"../outside.txt": "owned\n"}})),
        "injected-filesystem-model",
    )
    result = agent.execute("x", workspace, AgentBudgetGuard(AgentBudget(1, 5, 512, 0.0)))
    assert result.claimed_success is False
    assert not outside.exists()


def test_fixture_self_check_gold_passes_and_noop_fails(tmp_path):
    assert fixture_self_check(load_agent_manifest(DOGFOOD), tmp_path) == "passed"


def test_injected_dogfood_writes_labeled_receipt(tmp_path):
    artifact, receipt = run_dogfood(
        load_agent_manifest(DOGFOOD),
        agent="model",
        provider="ollama",
        model="injected-filesystem-model",
        trials=2,
        out=tmp_path / "artifact.json",
        receipt_out=tmp_path / "receipt.json",
        scripted_reply=load_scripted_reply(SCRIPTED),
        work_root=tmp_path,
    )
    assert artifact["dry_run"] is True
    assert artifact["provenance"]["evaluation_class"] == EVALUATION_CLASS_INJECTED_TRANSPORT
    assert artifact["provenance"]["agent_kind"] == "filesystem-model"
    assert artifact["provenance"]["model"] == "injected-filesystem-model"
    assert artifact["provenance"]["self_check"] == "passed"
    assert artifact["summary"]["pass_rate"] == 1.0
    assert all(trial["workspace_disposed"] for trial in artifact["trials"])
    assert receipt["receipt_kind"] == PRODUCT_RECEIPT_KIND
    assert receipt["published"] is False
    assert receipt["dry_run"] is True
    assert receipt["scorecard"]["completion"] == 100.0
    assert receipt["scorecard"]["category_completion"]["repository-repair"] == 100.0
    assert receipt["publication"]["publishable"] is False
    assert PUBLISH_REFUSE_DRY_RUN in receipt["publication"]["reasons"]
    with pytest.raises(ImportRefused, match="dry_run"):
        artifact_to_payload(artifact, source="test")


def test_fake_dogfood_stays_offline_reference(tmp_path):
    artifact, receipt = run_dogfood(
        load_agent_manifest(OFFLINE),
        agent="fake",
        provider="ollama",
        model="ignored",
        trials=1,
        out=tmp_path / "artifact.json",
        receipt_out=tmp_path / "receipt.json",
        work_root=tmp_path,
    )
    assert artifact["dry_run"] is True
    assert artifact["provenance"]["evaluation_class"] == EVALUATION_CLASS_OFFLINE_REFERENCE
    assert artifact["provenance"]["model"] == "deterministic-fake-agent"
    assert receipt["publication"]["publishable"] is False


def test_default_artifact_builder_remains_dry_run_fake(tmp_path):
    manifest = load_agent_manifest(OFFLINE)
    trial = run_agent_trial(
        manifest, OfflineTextEnvironment(tmp_path), DeterministicFakeAgent(), trial=1
    )
    artifact = build_agent_artifact(manifest, [trial])
    assert artifact["dry_run"] is True
    assert artifact["provenance"]["model"] == "deterministic-fake-agent"
    assert publication_receipt(artifact)["publishable"] is False


def test_honest_dry_run_labels():
    assert honest_dry_run(EVALUATION_CLASS_OFFLINE_REFERENCE) is True
    assert honest_dry_run(EVALUATION_CLASS_INJECTED_TRANSPORT) is True
    assert honest_dry_run(EVALUATION_CLASS_LIVE_LOCAL) is False
    with pytest.raises(ValueError):
        honest_dry_run("live-paid")


def test_paid_providers_refused_even_with_scripted_reply():
    with pytest.raises(PermissionError, match="authorization"):
        resolve_run_mode(agent="model", provider="openrouter", scripted_reply="{}")
    with pytest.raises(PermissionError, match="authorization"):
        resolve_run_mode(agent="model", provider="ollama-cloud", scripted_reply=None)


def test_live_local_without_daemon_is_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr("agentbench.agent_eval.ollama_reachable", lambda url=None, timeout=2.0: False)
    with pytest.raises(RuntimeError, match="Ollama"):
        run_dogfood(
            load_agent_manifest(DOGFOOD),
            agent="model",
            provider="ollama",
            model="llama3.2:1b",
            trials=1,
            out=tmp_path / "artifact.json",
            receipt_out=tmp_path / "receipt.json",
            work_root=tmp_path,
        )


def test_cli_scripted_dogfood(tmp_path):
    out = tmp_path / "artifact.json"
    receipt = tmp_path / "receipt.json"
    code = main(
        [
            "--manifest",
            str(DOGFOOD),
            "--agent",
            "model",
            "--scripted-reply-file",
            str(SCRIPTED),
            "--trials",
            "2",
            "--out",
            str(out),
            "--receipt-out",
            str(receipt),
        ]
    )
    assert code == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert artifact["dry_run"] is True
    assert payload["evaluation_class"] == EVALUATION_CLASS_INJECTED_TRANSPORT
    assert payload["published"] is False


def test_cli_refuses_openrouter(tmp_path, capsys):
    code = main(
        [
            "--manifest",
            str(DOGFOOD),
            "--agent",
            "model",
            "--provider",
            "openrouter",
            "--out",
            str(tmp_path / "a.json"),
            "--receipt-out",
            str(tmp_path / "r.json"),
        ]
    )
    assert code == 2
    assert "authorization" in capsys.readouterr().err
    assert PAID_REFUSAL


def test_infra_error_is_execution_failure(tmp_path):
    class _Boom:
        def post_json(self, url, headers, json):
            raise InfraError("provider down", status=503, attempts=5)

    manifest = load_agent_manifest(DOGFOOD)
    agent = FilesystemModelAgent(OpenAICompatClient(provider="ollama", transport=_Boom()), "x")
    trial = run_agent_trial(manifest, OfflineTextEnvironment(tmp_path), agent, trial=1)
    assert trial.outcome == "execution_failed"
    assert trial.passed is False


def test_scorecard_matches_product_receipt_shape():
    artifact = {
        "dry_run": True,
        "provenance": {"evaluation_class": EVALUATION_CLASS_INJECTED_TRANSPORT},
        "summary": {"pass_rate": 0.5, "cost_usd_per_task": 0.0, "latency_p50_ms": 12},
        "trials": [
            {"category": "repository-repair", "passed": True, "trial": 1, "outcome": "success", "termination_reason": "completed"},
            {"category": "repository-repair", "passed": False, "trial": 2, "outcome": "verification_failed", "termination_reason": "completed"},
        ],
    }
    score = scorecard_from_artifact(artifact)
    receipt = product_receipt(artifact)
    assert score == receipt["scorecard"]
    assert score["completion"] == 50.0
    assert score["category_completion"]["repository-repair"] == 50.0
