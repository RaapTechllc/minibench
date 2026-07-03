"""New-model tracker: poll OpenRouter's catalog and detect launches.

``GET /api/v1/models`` (no auth) returns ``{data:[{id, name, created, pricing,
context_length, ...}]}``. The diff logic is pure so it's unit-tested against
fixtures; the poll wrapper just feeds a client's ``list_models()`` through it.
The result upserts the backend ``known_models`` table so the UI can surface
"new — not yet benchmarked" models.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from agentbench.client import OpenAICompatClient


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    created: int | None = None
    context_length: int | None = None
    prompt_price: float | None = None
    completion_price: float | None = None

    @staticmethod
    def from_openrouter(d: dict[str, Any]) -> "ModelInfo":
        pricing = d.get("pricing") or {}

        def _price(key: str) -> float | None:
            v = pricing.get(key)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        return ModelInfo(
            id=str(d["id"]),
            name=str(d.get("name", d["id"])),
            created=int(d["created"]) if d.get("created") is not None else None,
            context_length=int(d["context_length"]) if d.get("context_length") is not None else None,
            prompt_price=_price("prompt"),
            completion_price=_price("completion"),
        )


def diff_models(
    known_ids: Iterable[str],
    current: Iterable[ModelInfo],
) -> list[ModelInfo]:
    """Return models present in ``current`` whose id is not in ``known_ids``.

    Order is preserved from ``current`` so the caller can rank by ``created``.
    """
    known = set(known_ids)
    return [m for m in current if m.id not in known]


def poll_openrouter(client: OpenAICompatClient) -> list[ModelInfo]:
    """Fetch the live catalog as :class:`ModelInfo` records."""
    return [ModelInfo.from_openrouter(d) for d in client.list_models()]
