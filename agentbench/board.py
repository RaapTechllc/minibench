"""Join OpenRouter Data API feeds into a cited Usage Board snapshot."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentbench.openrouter_data import fetch_payloads, load_fixture_payloads

CITE_TEMPLATE = "Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0."
BOARD_PATH_ENV = "OPENROUTER_BOARD_PATH"
DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "openrouter_board.json"


def env_board_path() -> Path | None:
    raw = (os.environ.get(BOARD_PATH_ENV) or "").strip()
    return Path(raw) if raw else None


def resolve_write_path(out: Path | None = None) -> Path:
    """Poll destination: explicit --out, else board path, else gitignored default."""
    if out is not None:
        return out
    env = env_board_path()
    if env is not None:
        return env
    return DEFAULT_SNAPSHOT_PATH


def citation(as_of: str) -> str:
    return CITE_TEMPLATE.format(as_of=as_of)


def _parse_as_of(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) == 10 and text[4] == "-":
        text = text + "T00:00:00Z"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def conservative_as_of(payloads: dict[str, Any]) -> str:
    stamps: list[datetime] = []
    feeds = payloads.get("feeds") or {}
    for body in feeds.values():
        if not isinstance(body, dict):
            continue
        meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
        for candidate in (meta.get("as_of"), (body.get("data") or {}).get("as_of") if isinstance(body.get("data"), dict) else None):
            parsed = _parse_as_of(candidate)
            if parsed:
                stamps.append(parsed)
    if not stamps:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    earliest = min(stamps)
    return earliest.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def blended_per_million(prompt: float | None, completion: float | None) -> float | None:
    """USD per 1M tokens at a 1:3 in:out mix. Prices on /models are per-token."""
    if prompt is None and completion is None:
        return None
    p = (prompt or 0.0) * 1_000_000
    c = (completion or 0.0) * 1_000_000
    return round(0.25 * p + 0.75 * c, 6)


def _model_url(model_id: str) -> str:
    return f"https://openrouter.ai/{model_id}"


def _index_models(models_body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in models_body.get("data") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        mid = str(item["id"])
        pricing = item.get("pricing") or {}
        out[mid] = {
            "id": mid,
            "name": str(item.get("name") or mid),
            "prompt_price": _f(pricing.get("prompt")),
            "completion_price": _f(pricing.get("completion")),
            "latency_ms": _i(item.get("latency")) or _i((item.get("top_provider") or {}).get("latency")),
        }
    return out


def _latest_rankings(rankings_body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    latest_date = ""
    by_id: dict[str, dict[str, Any]] = {}
    for row in rankings_body.get("data") or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("model_permaslug") or "")
        if not slug or slug == "other":
            continue
        date = str(row.get("date") or "")
        if date > latest_date:
            latest_date = date
            by_id = {}
        if date == latest_date:
            by_id[slug] = {
                "daily_tokens": _i(row.get("total_tokens")),
                "ranking_date": date,
            }
    return by_id


def _eval_and_latency(benchmarks_body: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    evals: dict[str, dict[str, Any]] = {}
    latencies: dict[str, int] = {}
    for item in benchmarks_body.get("data") or []:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("model_permaslug") or item.get("id") or "")
        if not slug:
            continue
        source = str(item.get("source") or "openrouter")
        score = None
        task = None
        if item.get("intelligence_index") is not None:
            score = _f(item.get("intelligence_index"))
            task = "intelligence_index"
        elif item.get("primary_score") is not None:
            score = _f(item.get("primary_score"))
            task = str(item.get("benchmark_type") or "official")
        elif item.get("accuracy") is not None:
            score = _f(item.get("accuracy"))
            task = str(item.get("benchmark_type") or "official")
        elif item.get("elo") is not None:
            score = _f(item.get("elo"))
            task = str(item.get("category") or "design-arena")
        if score is not None and slug not in evals:
            evals[slug] = {"eval_score": score, "eval_source": source, "eval_task": task}
        for key in ("avg_latency_per_task_ms", "avg_generation_time_ms", "latency_ms"):
            lat = _i(item.get(key))
            if lat is not None:
                latencies.setdefault(slug, lat)
                break
    return evals, latencies


def _task_shares(classifications_body: dict[str, Any]) -> dict[str, dict[str, float]]:
    shares: dict[str, dict[str, float]] = {}
    data = classifications_body.get("data") if isinstance(classifications_body.get("data"), dict) else classifications_body
    for cls in (data or {}).get("classifications") or []:
        if not isinstance(cls, dict):
            continue
        tag = str(cls.get("tag") or "")
        macro = str(cls.get("macro_category") or "")
        for model in cls.get("models") or []:
            if not isinstance(model, dict) or not model.get("id"):
                continue
            mid = str(model["id"])
            share = _f(model.get("tag_usage_share"))
            if share is None:
                continue
            bucket = shares.setdefault(mid, {})
            if tag:
                bucket[tag] = share
            if macro:
                bucket[macro] = max(share, bucket.get(macro, 0.0))
    return shares


def join_board(payloads: dict[str, Any]) -> dict[str, Any]:
    feeds = payloads.get("feeds") or {}
    as_of = conservative_as_of(payloads)
    cite = citation(as_of)
    models = _index_models(feeds.get("/models") or {})
    ranks = _latest_rankings(feeds.get("/datasets/rankings-daily") or {})
    evals, bench_lat = _eval_and_latency(feeds.get("/benchmarks") or {})
    tasks = _task_shares(feeds.get("/classifications/task") or {})

    ids = set(models) | set(ranks) | set(evals) | set(tasks)
    rows: list[dict[str, Any]] = []
    for mid in sorted(ids):
        catalog = models.get(mid) or {"id": mid, "name": mid, "prompt_price": None, "completion_price": None, "latency_ms": None}
        rank = ranks.get(mid) or {}
        ev = evals.get(mid) or {}
        latency = catalog.get("latency_ms") or bench_lat.get(mid)
        row = {
            "id": mid,
            "name": catalog.get("name") or mid,
            "openrouter_url": _model_url(mid),
            "prompt_price": catalog.get("prompt_price"),
            "completion_price": catalog.get("completion_price"),
            "blended_per_million": blended_per_million(catalog.get("prompt_price"), catalog.get("completion_price")),
            "daily_tokens": rank.get("daily_tokens"),
            "ranking_date": rank.get("ranking_date"),
            "eval_score": ev.get("eval_score"),
            "eval_source": ev.get("eval_source"),
            "eval_task": ev.get("eval_task"),
            "latency_ms": latency,
            "task_shares": tasks.get(mid) or {},
            "citation": cite,
            "as_of": as_of,
        }
        rows.append(row)
    return {
        "live": bool(payloads.get("live")),
        "meta": {
            "as_of": as_of,
            "citation": cite,
            "live": bool(payloads.get("live")),
            "source": payloads.get("source") or "fixture",
            "row_count": len(rows),
        },
        "rows": rows,
    }


def load_board(*, snapshot_path: Path | None = None, client=None) -> dict[str, Any]:
    """Load a cached snapshot, else the committed fixture.

    Reader rule (persist-live A2): an explicit ``snapshot_path`` that exists
    wins; else ``OPENROUTER_BOARD_PATH`` when set and the file exists; else
    the committed fixture (never labelled live). Recommend and the public
    board never live-call OpenRouter. The poller is the only live GET path.
    An injected ``client`` is for tests / fake transports only.
    """
    if snapshot_path is not None and snapshot_path.exists():
        return json.loads(snapshot_path.read_text())
    env = env_board_path()
    if env is not None and env.exists():
        return json.loads(env.read_text())
    if client is not None:
        return join_board(fetch_payloads(client))
    return join_board(load_fixture_payloads())


def write_board(board: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or DEFAULT_SNAPSHOT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(board, indent=2) + "\n")
    return dest


def best_by_cost(board: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [r for r in board.get("rows") or [] if r.get("blended_per_million") is not None]
    return sorted(rows, key=lambda r: (r["blended_per_million"], r["id"]))


def best_by_latency(board: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [r for r in board.get("rows") or [] if r.get("latency_ms") is not None]
    return sorted(rows, key=lambda r: (r["latency_ms"], r["id"]))


def _task_share(row: dict[str, Any], task: str) -> float | None:
    shares = row.get("task_shares") or {}
    if task in shares:
        return shares[task]
    # allow macro or prefix match: "code" matches "code:general_impl" if macro stored
    if task:
        matches = [v for k, v in shares.items() if k == task or k.startswith(task + ":")]
        if matches:
            return max(matches)
    return None


def best_by_task(board: dict[str, Any], task: str) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in board.get("rows") or []:
        share = _task_share(row, task)
        if share is None:
            continue
        scored.append((share, row))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("blended_per_million") or 1e9, pair[1]["id"]))
    return [row for _, row in scored]
