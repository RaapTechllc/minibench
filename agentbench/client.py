"""One OpenAI-compatible chat client for OpenRouter + Ollama.

Only ``base_url``/``api_key``/``model`` change between backends, so a single
client covers all three (OpenRouter cloud, Ollama local, Ollama cloud). The
network boundary is a single ``_post`` method; unit tests subclass and override
it (or inject a transport) so no key or socket is needed to exercise callers.

Cost accounting is real: we send ``usage: {include: true}`` so OpenRouter's
response ``usage`` object carries ``cost`` (actual $/credits charged). Ollama
returns no cost, so it stays ``None`` and callers price it as free/local.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

# Well-known OpenAI-compatible endpoints. base_url + api_key + model are the only
# things that differ between providers (the brief's "one client covers all three").
PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "ollama": {  # local
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,  # ignored by Ollama; we send a dummy
    },
    "ollama-cloud": {
        "base_url": "https://ollama.com/v1",
        "api_key_env": "OLLAMA_API_KEY",
    },
}


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # OpenRouter-only: actual money charged for this call. None for local Ollama.
    cost_usd: float | None = None
    # The upstream provider OpenRouter actually routed to — store it, because the
    # same model id can fan out to different providers at different price/quant.
    provider: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @staticmethod
    def from_response(body: dict[str, Any]) -> "Usage":
        u = body.get("usage") or {}
        cost = u.get("cost")
        return Usage(
            prompt_tokens=int(u.get("prompt_tokens", 0) or 0),
            completion_tokens=int(u.get("completion_tokens", 0) or 0),
            cost_usd=float(cost) if cost is not None else None,
            provider=body.get("provider") or u.get("provider"),
        )


@dataclass(frozen=True)
class ChatResult:
    text: str
    usage: Usage
    latency_ms: int = 0
    model: str = ""


class Transport(Protocol):
    """The single network seam. Return the parsed JSON body of a POST."""

    def post_json(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        ...


class HttpxTransport:
    """Real transport. httpx is imported lazily so offline tests never need it."""

    def __init__(self, timeout: float = 300.0) -> None:
        self._timeout = timeout

    def post_json(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        import httpx  # lazy: only required when actually hitting the network

        resp = httpx.post(url, headers=headers, json=json, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        import httpx

        resp = httpx.get(url, headers=headers, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()


class OpenAICompatClient:
    """Minimal chat-completions client against any OpenAI-compatible backend.

    ``model`` ids may be provider-namespaced (``openrouter/anthropic/claude-...``).
    The leading ``openrouter/`` / ``ollama/`` segment, if present, selects the
    backend and is stripped before being sent upstream.
    """

    def __init__(
        self,
        provider: str = "openrouter",
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        if provider not in PROVIDERS:
            raise ValueError(f"unknown provider '{provider}' (known: {list(PROVIDERS)})")
        spec = PROVIDERS[provider]
        self.provider = provider
        self.base_url = (base_url or spec["base_url"]).rstrip("/")
        env = spec["api_key_env"]
        self.api_key = api_key or (os.environ.get(env) if env else None) or "ollama"
        self._transport = transport or HttpxTransport()

    @staticmethod
    def _strip_provider_prefix(model: str) -> str:
        for prefix in ("openrouter/", "ollama-cloud/", "ollama/"):
            if model.startswith(prefix):
                return model[len(prefix):]
        return model

    def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        clock=None,
    ) -> ChatResult:
        """One chat-completion call. ``clock`` is an injectable monotonic ns source."""
        upstream_model = self._strip_provider_prefix(model)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": upstream_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Ask OpenRouter to include real cost accounting in the response.
            "usage": {"include": True},
        }
        started = clock() if clock else _monotonic_ns()
        body = self._transport.post_json(f"{self.base_url}/chat/completions", headers, payload)
        ended = clock() if clock else _monotonic_ns()

        text = _extract_text(body)
        return ChatResult(
            text=text,
            usage=Usage.from_response(body),
            latency_ms=max(0, (ended - started) // 1_000_000),
            model=model,
        )

    def list_models(self) -> list[dict[str, Any]]:
        """OpenRouter model catalog (no auth needed). Used by the tracker."""
        transport = self._transport
        url = f"{self.base_url}/models"
        if hasattr(transport, "get_json"):
            body = transport.get_json(url, {})  # type: ignore[attr-defined]
        else:  # a POST-only fake in tests can still answer here
            body = transport.post_json(url, {}, {})
        return list(body.get("data", []))


def _extract_text(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def _monotonic_ns() -> int:
    import time

    return time.monotonic_ns()
