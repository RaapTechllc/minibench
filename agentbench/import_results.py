"""Publish committed result artifacts to the backend — no provider key needed.

``agentbench/results/*.json`` holds real, auditable runs, but ``run.py
--publish`` only fires *after executing a suite* — so a fresh database stays
empty unless someone re-runs every model against a live provider. This module
closes that loop: it replays committed artifacts through the exact same
payload builder and POST endpoint the live path uses.

    # Validate + preview only (no network):
    python -m agentbench.import_results agentbench/results/*.json --check

    # Publish to a running backend:
    python -m agentbench.import_results agentbench/results/*.json \
        --api http://localhost:3070

Honesty gates (mirrors of run.py's publish gates — an import must never be a
back door around them):

- ``dry_run: true`` artifacts are refused unconditionally. StubModel numbers
  are not benchmark data; there is deliberately no override flag.
- Canary-echo trials refuse the import (training contamination — quarantine).
- Infra-error trials refuse the import unless ``--allow-infra-errors``.

Legacy artifacts (pre-grader-v3: no ``provenance``, no per-trial
``infra_error``/``canary_flag``/``passed_format``) import with those fields at
their documented defaults, exactly as ``TrialResult`` defines them. Anything
the artifact does not state is left null — never guessed.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from agentbench.run import TrialResult, publish_run, to_agent_run_submit

_TRIAL_FIELDS = {f.name for f in dataclasses.fields(TrialResult)}

# Provenance keys forwarded from the artifact to the submit payload when
# present (current-schema artifacts; legacy files have none of them).
_PROVENANCE_KEYS = ("seed_sha256", "generator_sha256", "git_commit", "is_private_split")


class ImportRefused(Exception):
    """Artifact failed an honesty gate; message says which and why."""


def load_trials(raw_trials: list[dict[str, Any]]) -> list[TrialResult]:
    """Rebuild TrialResult objects, tolerating older and newer field sets."""
    return [
        TrialResult(**{k: v for k, v in t.items() if k in _TRIAL_FIELDS})
        for t in raw_trials
    ]


def derive_provider(summary: dict[str, Any]) -> str:
    """Provider from the model-string prefixes (e.g. ``openrouter/anthropic/...``)."""
    models = (summary.get("moa_config") or {}).get("models") or []
    prefixes = {m.split("/", 1)[0] for m in models if "/" in m}
    if len(prefixes) == 1:
        return prefixes.pop()
    raise ImportRefused(
        f"cannot derive a single provider from models={models!r}; pass --provider"
    )


def artifact_to_payload(
    data: dict[str, Any],
    *,
    source: str,
    provider: str | None = None,
    allow_infra_errors: bool = False,
) -> dict[str, Any]:
    """Validate one artifact and build the ``AgentRunSubmit`` payload for it."""
    if data.get("dry_run", False):
        raise ImportRefused(
            f"{source}: dry_run artifact — StubModel output is not benchmark data; "
            "refusing (no override)."
        )

    summary = data.get("summary")
    raw_trials = data.get("trials")
    if not summary or not raw_trials:
        raise ImportRefused(f"{source}: missing summary or trials — not a run artifact.")

    trials = load_trials(raw_trials)

    n_canary = summary.get("n_canary_flags", sum(t.canary_flag for t in trials))
    if n_canary > 0:
        raise ImportRefused(
            f"{source}: {n_canary} canary-echo trial(s) — training contamination; "
            "quarantine this artifact."
        )
    n_infra = summary.get("n_infra_errors", sum(t.infra_error for t in trials))
    if n_infra > 0 and not allow_infra_errors:
        raise ImportRefused(
            f"{source}: {n_infra} infra-error trial(s) — partial run; rerun it or "
            "pass --allow-infra-errors."
        )

    provenance = {
        k: v
        for k, v in (data.get("provenance") or {}).items()
        if k in _PROVENANCE_KEYS and v is not None
    }
    return to_agent_run_submit(
        summary,
        trials,
        provider=provider or derive_provider(summary),
        provenance=provenance,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Publish committed agentbench result artifacts to the backend."
    )
    ap.add_argument("files", nargs="+", help="result JSON artifact(s)")
    ap.add_argument("--api", default=None, metavar="API_URL",
                    help="backend base URL (e.g. http://localhost:3070)")
    ap.add_argument("--provider", default=None,
                    help="override provider (default: derived from model strings)")
    ap.add_argument("--check", action="store_true",
                    help="validate and summarize payloads without POSTing")
    ap.add_argument("--allow-infra-errors", action="store_true",
                    help="import runs containing infra-error trials")
    args = ap.parse_args(argv)

    if not args.check and not args.api:
        ap.error("either --api API_URL or --check is required")

    imported = refused = failed = 0
    for path_str in args.files:
        path = Path(path_str)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            payload = artifact_to_payload(
                data,
                source=path.name,
                provider=args.provider,
                allow_infra_errors=args.allow_infra_errors,
            )
        except ImportRefused as e:
            print(f"REFUSED  {e}", file=sys.stderr)
            refused += 1
            continue
        except (OSError, ValueError, TypeError) as e:
            print(f"ERROR    {path.name}: {e}", file=sys.stderr)
            failed += 1
            continue

        config_name = (payload.get("moa_config") or {}).get("name", "?")
        line = (
            f"{payload['benchmark_suite']}  {config_name}  "
            f"pass_rate={payload['pass_rate']}%  trials={len(payload['results'])}"
        )
        if args.check:
            print(f"OK       {path.name}: {line}")
            imported += 1
            continue

        try:
            published = publish_run(args.api, payload)
        except (RuntimeError, OSError) as e:
            print(f"ERROR    {path.name}: {e}", file=sys.stderr)
            failed += 1
            continue
        print(f"PUBLISHED {path.name}: {line}  run_id={published.get('run_id')}")
        imported += 1

    verb = "validated" if args.check else "published"
    print(f"\n{imported} {verb}, {refused} refused, {failed} failed "
          f"of {len(args.files)} artifact(s)")
    return 0 if failed == 0 and imported > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
