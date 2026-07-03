"""Offline test doubles — no network, no API keys.

``FakeTransport`` answers chat-completions and /models from canned data so the
whole MoA/tracker stack is exercised deterministically.
"""
from __future__ import annotations

from typing import Any, Callable

from agentbench.client import OpenAICompatClient


class FakeTransport:
    """Records requests and returns scripted responses.

    ``responder(payload) -> (text, usage_dict)`` lets a test decide the reply per
    call (e.g. echo the model id). ``models`` is returned from /models.
    """

    def __init__(
        self,
        responder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]] | None = None,
        models: list[dict[str, Any]] | None = None,
    ) -> None:
        self.responder = responder or (lambda p: (f"answer from {p['model']}", {}))
        self._models = models or []
        self.requests: list[dict[str, Any]] = []

    def post_json(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(json)
        if url.endswith("/models"):
            return {"data": self._models}
        text, usage = self.responder(json)
        return {
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": usage,
            "provider": usage.get("provider"),
        }

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        return {"data": self._models}


def make_client(**kwargs: Any) -> OpenAICompatClient:
    transport = FakeTransport(**kwargs)
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    return client
