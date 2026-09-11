"""Genuine-path dogfood for the Real-Work Agent Cabinet.

Reuses ``AgentAdapter``, ``run_agent_trial``, ``OfflineTextEnvironment``,
``OpenAICompatClient``, and ``publication_receipt``. This is a binding, not a
second runner. See ``docs/validation/agent-eval-reuse-preflight.md``.

Paid OpenRouter / Ollama Cloud calls are refused. Local Ollama is the only
live-provider class this CLI will attempt. Scripted transports stay
``dry_run: true``. The CLI never POSTs a cabinet run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from agentbench.agent_cabinet import (
    EVALUATION_CLASS_INJECTED_TRANSPORT,
    EVALUATION_CLASS_LIVE_LOCAL,
    EVALUATION_CLASS_OFFLINE_REFERENCE,
    PAID_LIVE_PROVIDERS,
    honest_dry_run,
    product_receipt,
)
from agentbench.agent_tasks import (
    AgentBudgetGuard,
    AgentResult,
    AgentTaskManifest,
    DeterministicFakeAgent,
    OfflineTextEnvironment,
    load_agent_manifest,
    run_agent_trial,
    write_agent_artifact,
)
from agentbench.client import ChatMessage, InfraError, OpenAICompatClient, PROVIDERS


HARNESS = "minibench-reference"
HARNESS_VERSION = "1"
AGENT_KIND_FAKE = "deterministic-fake"
AGENT_KIND_MODEL = "filesystem-model"
DEFAULT_OLLAMA_PROBE = "http://127.0.0.1:11434/api/tags"
PAID_REFUSAL = (
    "REFUSED: paid live model calls (openrouter / ollama-cloud) require "
    "explicit owner authorization. Use --agent fake, --scripted-reply-file, "
    "or --provider ollama against a local daemon."
)

_SYSTEM = (
    "You edit files in a local workspace. Read the user request and the file "
    "listing. Reply with JSON only: "
    '{"writes": {"relative/path": "full file contents"}}'
)


class ScriptedTransport:
    """Picklable OpenAI-compatible transport for injected-transport dogfood."""

    def __init__(self, text: str, usage: dict[str, Any] | None = None):
        self.text = text
        self.usage = usage or {"prompt_tokens": 8, "completion_tokens": 12, "cost": 0}

    def post_json(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        return {
            "choices": [{"message": {"role": "assistant", "content": self.text}}],
            "usage": dict(self.usage),
        }


class NoopAgent:
    """Known-wrong adapter for the fixture gold/bad self-check."""

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        budget.consume(turns=1)
        return AgentResult(
            termination_reason="completed",
            claimed_success=False,
            turns=1,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
        )


class FilesystemModelAgent:
    """``AgentAdapter`` that inspects the workspace and applies model writes.

    Hidden gold is never consulted. Verification stays in the environment.
    """

    def __init__(self, client: OpenAICompatClient, model: str, *, max_output_tokens: int = 256):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be a positive integer")
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        listing = _workspace_listing(workspace)
        user = (
            f"{prompt}\n\nWorkspace files:\n{listing}\n\n"
            'Reply with JSON only: {"writes": {"relative/path": "full file contents"}}'
        )
        try:
            result = self.client.chat(
                self.model,
                [ChatMessage(role="system", content=_SYSTEM), ChatMessage(role="user", content=user)],
                temperature=0.0,
                top_p=1.0,
                max_tokens=min(budget.max_tokens, self.max_output_tokens) or 1,
            )
        except InfraError:
            raise
        tokens = result.usage.total_tokens
        cost = 0.0 if result.usage.cost_usd is None else float(result.usage.cost_usd)
        budget.consume(turns=1, tokens=tokens, cost_usd=cost)
        writes = parse_model_writes(result.text)
        applied = _apply_writes(workspace, writes)
        return AgentResult(
            termination_reason="completed",
            claimed_success=applied > 0,
            turns=1,
            tokens_in=result.usage.prompt_tokens,
            tokens_out=result.usage.completion_tokens,
            cost_usd=cost,
        )


def _workspace_listing(workspace: Path) -> str:
    parts: list[str] = []
    for path in sorted(p for p in workspace.rglob("*") if p.is_file()):
        relative = path.relative_to(workspace).as_posix()
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            body = "(binary)"
        parts.append(f"--- {relative} ---\n{body}")
    return "\n".join(parts) if parts else "(empty workspace)"


def parse_model_writes(text: str) -> dict[str, str]:
    payload = _extract_json_object(text)
    raw = payload.get("writes")
    if not isinstance(raw, dict):
        return {}
    writes: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and key.strip() and isinstance(value, str):
            writes[key] = value
    return writes


def _extract_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {}
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


def _apply_writes(workspace: Path, writes: dict[str, str]) -> int:
    root = workspace.resolve()
    applied = 0
    for relative, content in writes.items():
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            continue
        target = (workspace / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        applied += 1
    return applied


def load_scripted_reply(path: str | Path) -> str:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("scripted reply file is empty")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(parsed, dict) and "writes" in parsed:
        return json.dumps(parsed, separators=(",", ":"))
    if isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
        return parsed["text"]
    return raw


def fixture_self_check(manifest: AgentTaskManifest, root: Path) -> str:
    gold = run_agent_trial(
        manifest, OfflineTextEnvironment(root / "gold"), DeterministicFakeAgent(), trial=1
    )
    bad = run_agent_trial(manifest, OfflineTextEnvironment(root / "bad"), NoopAgent(), trial=1)
    return "passed" if gold.passed and not bad.passed else "failed"


def ollama_reachable(url: str = DEFAULT_OLLAMA_PROBE, timeout: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (URLError, OSError, TimeoutError, ValueError):
        return False


def resolve_run_mode(
    *,
    agent: str,
    provider: str,
    scripted_reply: str | None,
) -> tuple[str, str, bool]:
    """Return ``(evaluation_class, agent_kind, dry_run)``."""
    if agent == "fake":
        return EVALUATION_CLASS_OFFLINE_REFERENCE, AGENT_KIND_FAKE, True
    if agent != "model":
        raise ValueError(f"unsupported --agent: {agent}")
    if provider in PAID_LIVE_PROVIDERS:
        raise PermissionError(PAID_REFUSAL)
    if scripted_reply is not None:
        return EVALUATION_CLASS_INJECTED_TRANSPORT, AGENT_KIND_MODEL, True
    if provider == "ollama":
        return EVALUATION_CLASS_LIVE_LOCAL, AGENT_KIND_MODEL, False
    raise ValueError(
        "model agent requires --scripted-reply-file (injected-transport) "
        "or --provider ollama with a local daemon"
    )


def build_agent(
    *,
    agent: str,
    provider: str,
    model: str,
    scripted_reply: str | None,
    client: OpenAICompatClient | None = None,
) -> Any:
    evaluation_class, agent_kind, _dry = resolve_run_mode(
        agent=agent, provider=provider, scripted_reply=scripted_reply
    )
    if agent_kind == AGENT_KIND_FAKE:
        return DeterministicFakeAgent(), evaluation_class, agent_kind
    if client is None:
        if scripted_reply is not None:
            client = OpenAICompatClient(provider="ollama", transport=ScriptedTransport(scripted_reply))
        else:
            client = OpenAICompatClient(provider=provider)
    return FilesystemModelAgent(client, model), evaluation_class, agent_kind


def run_dogfood(
    manifest: AgentTaskManifest,
    *,
    agent: str,
    provider: str,
    model: str,
    trials: int,
    out: Path,
    receipt_out: Path,
    scripted_reply: str | None = None,
    client: OpenAICompatClient | None = None,
    work_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if trials < 1:
        raise ValueError("trials must be positive")
    adapter, evaluation_class, agent_kind = build_agent(
        agent=agent,
        provider=provider,
        model=model,
        scripted_reply=scripted_reply,
        client=client,
    )
    dry_run = honest_dry_run(evaluation_class)
    if evaluation_class == EVALUATION_CLASS_LIVE_LOCAL and not ollama_reachable():
        raise RuntimeError(
            "local Ollama daemon is not reachable at 127.0.0.1:11434; "
            "install/start ollama or use --scripted-reply-file"
        )
    root = Path(work_root) if work_root is not None else Path(out).parent
    self_check = fixture_self_check(manifest, root / "self-check")
    results = [
        run_agent_trial(manifest, OfflineTextEnvironment(root / f"trial-{i}"), adapter, trial=i)
        for i in range(1, trials + 1)
    ]
    artifact = write_agent_artifact(
        out,
        manifest,
        results,
        model=model if agent_kind == AGENT_KIND_MODEL else "deterministic-fake-agent",
        provider="offline" if dry_run and evaluation_class != EVALUATION_CLASS_LIVE_LOCAL else provider,
        harness=HARNESS,
        harness_version=HARNESS_VERSION,
        dry_run=dry_run,
        evaluation_class=evaluation_class,
        agent_kind=agent_kind,
    )
    artifact["provenance"]["self_check"] = self_check
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    receipt = product_receipt(artifact, artifact_path=str(out), published=False)
    receipt_out.parent.mkdir(parents=True, exist_ok=True)
    receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return artifact, receipt


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(repo_root / "agentbench" / ".env", override=False)


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(
        description="Dogfood the Agent Cabinet contract through a local product receipt."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--agent", choices=("fake", "model"), default="model")
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="ollama")
    parser.add_argument("--model", default="injected-filesystem-model")
    parser.add_argument("--scripted-reply-file", default=None)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt-out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")

    try:
        scripted = load_scripted_reply(args.scripted_reply_file) if args.scripted_reply_file else None
        resolve_run_mode(agent=args.agent, provider=args.provider, scripted_reply=scripted)
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    try:
        artifact, receipt = run_dogfood(
            load_agent_manifest(args.manifest),
            agent=args.agent,
            provider=args.provider,
            model=args.model,
            trials=args.trials,
            out=Path(args.out),
            receipt_out=Path(args.receipt_out),
            scripted_reply=scripted,
        )
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"summary": artifact["summary"], "receipt": receipt}, indent=2))
    if artifact["provenance"].get("self_check") == "failed":
        return 1
    if not all(trial.get("workspace_disposed") for trial in artifact["trials"]):
        return 1
    # Injected/fake dogfood is a path proof, not a leaderboard publish.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
