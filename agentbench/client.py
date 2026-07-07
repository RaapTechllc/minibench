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
import random
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class InfraError(RuntimeError):
    """A transient infrastructure failure (rate limit, 5xx, timeout) that
    survived every retry. Callers must NOT score this as a model failure —
    doing so corrupts rankings with provider luck."""

    def __init__(self, message: str, *, status: int | None = None, attempts: int = 0) -> None:
        super().__init__(message)
        self.status = status
        self.attempts = attempts


# Transient statuses worth retrying. Other 4xx (401/403/404/422) are config
# bugs and raise immediately.
RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504, 529})
MAX_ATTEMPTS = 5
BACKOFF_BASE_S = 2.0
BACKOFF_CAP_S = 60.0

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
    """Real transport with retry/backoff. httpx is imported lazily so offline
    tests never need it; ``post``/``sleep`` are injectable for retry tests.

    Rate limits, 5xx and timeouts are retried with exponential backoff + full
    jitter (honoring ``Retry-After``); exhaustion raises :class:`InfraError` so
    the harness can account the trial as infrastructure, not capability.
    """

    def __init__(
        self,
        timeout: float = 300.0,
        *,
        post: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self._timeout = timeout
        self._post = post
        self._sleep = sleep
        self._max_attempts = max_attempts

    def _backoff_s(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                # Clamp to [0, cap]: a malformed/negative Retry-After (e.g. "-1")
                # must never reach time.sleep, which raises on a negative delay.
                return max(0.0, min(float(retry_after), BACKOFF_CAP_S))
            except ValueError:
                pass
        cap = min(BACKOFF_CAP_S, BACKOFF_BASE_S * (2 ** attempt))
        return random.uniform(0, cap)  # full jitter

    def post_json(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> dict[str, Any]:
        import httpx  # lazy: only required when actually hitting the network

        post = self._post or httpx.post
        sleep = self._sleep or __import__("time").sleep
        last_status: int | None = None
        last_err: str = "unknown"

        for attempt in range(self._max_attempts):
            try:
                resp = post(url, headers=headers, json=json, timeout=self._timeout)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_status, last_err = None, f"{type(e).__name__}: {e}"
                if attempt + 1 < self._max_attempts:
                    sleep(self._backoff_s(attempt, None))
                continue
            if resp.status_code in RETRYABLE_STATUSES:
                last_status, last_err = resp.status_code, f"HTTP {resp.status_code}"
                if attempt + 1 < self._max_attempts:
                    sleep(self._backoff_s(attempt, resp.headers.get("Retry-After")))
                continue
            resp.raise_for_status()  # non-retryable 4xx: config bug, fail fast
            return resp.json()

        raise InfraError(
            f"transient failure after {self._max_attempts} attempts: {last_err}",
            status=last_status,
            attempts=self._max_attempts,
        )

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
        top_p: float | None = None,
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
        if top_p is not None:
            payload["top_p"] = top_p
        started = clock() if clock else _monotonic_ns()
        body = self._transport.post_json(f"{self.base_url}/chat/completions", headers, payload)
        text = _extract_text(body)
        if not text:
            # A 200 with empty text is retried ONCE; if it repeats, it is a
            # MODEL failure (it produced nothing) — never laundered as infra.
            body = self._transport.post_json(f"{self.base_url}/chat/completions", headers, payload)
            text = _extract_text(body)
        ended = clock() if clock else _monotonic_ns()
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
