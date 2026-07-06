"""Master model catalog: turn the live OpenRouter feed into seed-ready rows.

The pivot (docs/PIVOT-PLAN.md W2) makes model capability the primary axis, so
the backend needs the full list of models we intend to track — not the ~7 open
models the original seed shipped with. This module is catalog-DRIVEN, not
memory-driven: the strategic list below names ids we care about, but every row
that reaches the seed file is looked up in the live ``GET /api/v1/models`` feed
for its real name, context length and prices. An id that disappears from the
feed fails loudly instead of silently seeding stale data.

Usage (writes the committed seed file):

    python -m agentbench.catalog --feed <models.json>          # from a saved feed
    python -m agentbench.catalog --fetch                       # live fetch

Output: ``backend/app/data/known_models_seed.json`` — consumed by
``backend/app/seed.py:seed_known_models`` with ``benchmarked=false`` so new
rows surface in the "New — not yet benchmarked" panel.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
SEED_PATH = Path(__file__).resolve().parents[1] / "backend" / "app" / "data" / "known_models_seed.json"

# Strategic families and the pinned ids we track (verified against the live
# feed on 2026-07-06 — regenerate with --fetch, never edit prices by hand).
# license: "open" = downloadable weights, "closed" = API-only.
# Dictated-name resolution: "QEM"→qwen, "MIMO"→xiaomi/mimo, "K2/K2.7"→moonshotai
# kimi-k2.x. Yi (01-ai) and InternLM are NOT on the OpenRouter feed (checked
# 2026-07-06) and therefore have no rows — add them when they appear.
STRATEGIC_MODELS: list[dict[str, str]] = [
    # Alibaba Qwen
    {"id": "qwen/qwen3.7-max", "family": "Qwen", "license": "closed"},
    {"id": "qwen/qwen3.7-plus", "family": "Qwen", "license": "closed"},
    {"id": "qwen/qwen3.6-flash", "family": "Qwen", "license": "closed"},
    {"id": "qwen/qwen3.5-9b", "family": "Qwen", "license": "open"},
    # Xiaomi MiMo
    {"id": "xiaomi/mimo-v2.5-pro", "family": "MiMo", "license": "open"},
    {"id": "xiaomi/mimo-v2.5", "family": "MiMo", "license": "open"},
    # MiniMax
    {"id": "minimax/minimax-m3", "family": "MiniMax", "license": "open"},
    {"id": "minimax/minimax-m2.7", "family": "MiniMax", "license": "open"},
    # Moonshot Kimi
    {"id": "moonshotai/kimi-k2.7-code", "family": "Kimi", "license": "open"},
    {"id": "moonshotai/kimi-k2.6", "family": "Kimi", "license": "open"},
    {"id": "moonshotai/kimi-k2-thinking", "family": "Kimi", "license": "open"},
    # DeepSeek
    {"id": "deepseek/deepseek-v4-pro", "family": "DeepSeek", "license": "open"},
    {"id": "deepseek/deepseek-v4-flash", "family": "DeepSeek", "license": "open"},
    {"id": "deepseek/deepseek-r1-0528", "family": "DeepSeek", "license": "open"},
    # Zhipu GLM
    {"id": "z-ai/glm-5.2", "family": "GLM", "license": "open"},
    {"id": "z-ai/glm-5", "family": "GLM", "license": "open"},
    {"id": "z-ai/glm-4.7-flash", "family": "GLM", "license": "open"},
    # NVIDIA Nemotron
    {"id": "nvidia/nemotron-3-ultra-550b-a55b", "family": "Nemotron", "license": "open"},
    {"id": "nvidia/nemotron-3-super-120b-a12b", "family": "Nemotron", "license": "open"},
    {"id": "nvidia/nemotron-3-nano-30b-a3b", "family": "Nemotron", "license": "open"},
    # OpenAI
    {"id": "openai/gpt-5.5", "family": "GPT", "license": "closed"},
    {"id": "openai/gpt-5.4-mini", "family": "GPT", "license": "closed"},
    {"id": "openai/gpt-5.4-nano", "family": "GPT", "license": "closed"},
    {"id": "openai/gpt-5.3-codex", "family": "GPT", "license": "closed"},
    # Anthropic
    {"id": "anthropic/claude-sonnet-5", "family": "Claude", "license": "closed"},
    {"id": "anthropic/claude-fable-5", "family": "Claude", "license": "closed"},
    {"id": "anthropic/claude-opus-4.8", "family": "Claude", "license": "closed"},
    {"id": "anthropic/claude-haiku-4.5", "family": "Claude", "license": "closed"},
    # Google
    {"id": "google/gemini-3.5-flash", "family": "Gemini", "license": "closed"},
    {"id": "google/gemini-3.1-pro-preview", "family": "Gemini", "license": "closed"},
    {"id": "google/gemma-4-31b-it", "family": "Gemma", "license": "open"},
    {"id": "google/gemma-4-26b-a4b-it", "family": "Gemma", "license": "open"},
    # Meta
    {"id": "meta-llama/llama-4-maverick", "family": "Llama", "license": "open"},
    {"id": "meta-llama/llama-4-scout", "family": "Llama", "license": "open"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "family": "Llama", "license": "open"},
    # Mistral
    {"id": "mistralai/mistral-medium-3-5", "family": "Mistral", "license": "closed"},
    {"id": "mistralai/mistral-small-2603", "family": "Mistral", "license": "open"},
    {"id": "mistralai/devstral-2512", "family": "Mistral", "license": "open"},
    # xAI
    {"id": "x-ai/grok-4.3", "family": "Grok", "license": "closed"},
    {"id": "x-ai/grok-4.20", "family": "Grok", "license": "closed"},
    # Microsoft
    {"id": "microsoft/phi-4", "family": "Phi", "license": "open"},
    # Cohere
    {"id": "cohere/command-a", "family": "Command", "license": "open"},
]


def build_catalog(feed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join the strategic list against a live feed; missing ids are an error."""
    by_id = {m["id"]: m for m in feed}
    missing = [s["id"] for s in STRATEGIC_MODELS if s["id"] not in by_id]
    if missing:
        raise KeyError(
            "strategic ids absent from the OpenRouter feed (renamed or removed?): "
            + ", ".join(missing)
        )
    rows = []
    for s in STRATEGIC_MODELS:
        m = by_id[s["id"]]
        pricing = m.get("pricing") or {}

        def _price(key: str) -> float | None:
            try:
                return float(pricing[key]) if pricing.get(key) is not None else None
            except (TypeError, ValueError):
                return None

        created = m.get("created")
        rows.append(
            {
                "provider": "openrouter",
                "model_id": s["id"],
                "display_name": m.get("name") or s["id"],
                "family": s["family"],
                "license": s["license"],
                "context_length": m.get("context_length"),
                "prompt_price": _price("prompt"),
                "completion_price": _price("completion"),
                "snapshot_date": (
                    datetime.fromtimestamp(created, tz=timezone.utc).date().isoformat()
                    if created
                    else None
                ),
            }
        )
    return rows


def fetch_feed() -> list[dict[str, Any]]:
    with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["data"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the committed known_models seed file.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--fetch", action="store_true", help="fetch the live OpenRouter feed")
    src.add_argument("--feed", help="path to a saved GET /api/v1/models JSON response")
    ap.add_argument("--out", default=str(SEED_PATH))
    args = ap.parse_args(argv)

    if args.fetch:
        feed = fetch_feed()
    else:
        feed = json.loads(Path(args.feed).read_text(encoding="utf-8"))["data"]

    rows = build_catalog(feed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": OPENROUTER_MODELS_URL,
        "models": rows,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} catalog rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
