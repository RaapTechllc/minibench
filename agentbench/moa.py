"""MoA-as-a-model: a whole Mixture-of-Agents pipeline behind one generate().

Proposers answer the prompt (in parallel by default); their outputs are
concatenated as numbered "references" and handed to the aggregator under the
Aggregate-and-Synthesize system prompt (Together AI / Wang et al. 2024). The
harness sees the entire pipeline as a single model string.

``self_moa=True`` samples one model N times instead of mixing — the matched-cost
baseline the brief requires so we never compare MoA against a single cheap call.

Cost/latency/tokens are aggregated across every underlying call so the
leaderboard can put accuracy next to real spend.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from agentbench.client import ChatMessage, ChatResult, OpenAICompatClient
from agentbench.config import MoAConfig, ProposerConfig


@dataclass
class MoAResult:
    text: str
    # Rolled-up accounting across all proposer + aggregator calls.
    cost_usd: float | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    n_calls: int
    proposer_texts: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _aggregate_usage(results: list[ChatResult]) -> tuple[float | None, int, int]:
    """Sum tokens; sum cost only if every call reported one (else unknown)."""
    prompt = sum(r.usage.prompt_tokens for r in results)
    completion = sum(r.usage.completion_tokens for r in results)
    costs = [r.usage.cost_usd for r in results]
    total_cost = sum(c for c in costs if c is not None) if any(c is not None for c in costs) else None
    return total_cost, prompt, completion


def _number_references(texts: list[str]) -> str:
    return "\n\n".join(f"{i}. {t}" for i, t in enumerate(texts, start=1))


class MoAModel:
    """Runs a :class:`MoAConfig` against a client, exposing ``generate``."""

    def __init__(self, config: MoAConfig, client: OpenAICompatClient) -> None:
        self.config = config
        self.client = client

    # ── proposer round ────────────────────────────────────────────────────────
    def _run_proposer(self, proposer: ProposerConfig, prompt: str, prior: str | None) -> ChatResult:
        messages = [ChatMessage(role="user", content=prompt)]
        if prior:
            # Layer > 1: feed the previous round's synthesis back as context.
            messages.append(
                ChatMessage(
                    role="user",
                    content=(
                        "Here is a previous aggregated answer to improve upon. "
                        "Produce a better, corrected response:\n\n" + prior
                    ),
                )
            )
        return self.client.chat(
            proposer.model,
            messages,
            temperature=proposer.temperature,
            max_tokens=proposer.max_tokens,
        )

    def _proposer_specs(self) -> list[ProposerConfig]:
        if self.config.self_moa:
            # Sample the single model N times (matched-cost Self-MoA baseline).
            only = self.config.proposers[0]
            return [only] * self.config.self_moa_samples
        return list(self.config.proposers)

    def _propose(self, prompt: str, prior: str | None) -> list[ChatResult]:
        specs = self._proposer_specs()
        if self.config.parallel and len(specs) > 1:
            with ThreadPoolExecutor(max_workers=len(specs)) as pool:
                return list(pool.map(lambda p: self._run_proposer(p, prompt, prior), specs))
        return [self._run_proposer(p, prompt, prior) for p in specs]

    # ── aggregator ────────────────────────────────────────────────────────────
    def _aggregate(self, prompt: str, proposer_texts: list[str]) -> ChatResult:
        agg = self.config.aggregator
        system = agg.system_prompt + "\n\n" + _number_references(proposer_texts)
        messages = [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=prompt),
        ]
        return self.client.chat(
            agg.model,
            messages,
            temperature=agg.temperature,
            max_tokens=agg.max_tokens,
        )

    # ── public API ────────────────────────────────────────────────────────────
    def generate(self, prompt: str) -> MoAResult:
        if self.config.single:
            # One model, one call — no aggregation round to pay for.
            call = self._run_proposer(self.config.proposers[0], prompt, None)
            cost, prompt_tok, completion_tok = _aggregate_usage([call])
            return MoAResult(
                text=call.text,
                cost_usd=cost,
                prompt_tokens=prompt_tok,
                completion_tokens=completion_tok,
                latency_ms=call.latency_ms,
                n_calls=1,
                proposer_texts=[call.text],
            )

        all_calls: list[ChatResult] = []
        prior: str | None = None
        last_proposer_texts: list[str] = []

        for _ in range(self.config.layers):
            proposals = self._propose(prompt, prior)
            all_calls.extend(proposals)
            last_proposer_texts = [p.text for p in proposals]
            agg = self._aggregate(prompt, last_proposer_texts)
            all_calls.append(agg)
            prior = agg.text  # becomes context for the next layer, and the final answer

        cost, prompt_tok, completion_tok = _aggregate_usage(all_calls)
        latency = sum(c.latency_ms for c in all_calls)
        return MoAResult(
            text=prior or "",
            cost_usd=cost,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            latency_ms=latency,
            n_calls=len(all_calls),
            proposer_texts=last_proposer_texts,
        )
