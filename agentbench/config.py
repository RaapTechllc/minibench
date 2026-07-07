"""MoA config schema + loader.

The whole pipeline is expressed as data so swapping a model is a one-line edit
(the brief's "swappable MoA config"). We validate aggressively at load time —
a benchmark that silently runs a mis-typed config is how the old prototype
drifted from ``moa-presets.yaml`` in the first place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a MoA config is missing required fields or malformed."""


# The canonical Wang et al. 2024 "Aggregate-and-Synthesize" system prompt.
# Kept here (not just referenced) so a run is reproducible from this repo alone.
AGGREGATE_AND_SYNTHESIZE = (
    "You have been provided with a set of responses from various open-source "
    "models to the latest user query. Your task is to synthesize these responses "
    "into a single, high-quality response. It is crucial to critically evaluate "
    "the information provided in these responses, recognizing that some of it may "
    "be biased or incorrect. Your response should not simply replicate the given "
    "answers but should offer a refined, accurate, and comprehensive reply to the "
    "instruction. Ensure your response is well-structured, coherent, and adheres "
    "to the highest standards of accuracy and reliability.\n\nResponses from models:"
)

# Named, reusable aggregator system prompts. A config references one by key so
# the YAML stays terse; unknown keys are treated as a literal inline prompt.
SYSTEM_PROMPTS = {
    "aggregate_and_synthesize": AGGREGATE_AND_SYNTHESIZE,
}


@dataclass(frozen=True)
class ProposerConfig:
    model: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 2048

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ProposerConfig":
        if "model" not in d:
            raise ConfigError("proposer entry missing required 'model'")
        return ProposerConfig(
            model=str(d["model"]),
            temperature=float(d.get("temperature", 0.7)),
            top_p=float(d.get("top_p", 1.0)),
            max_tokens=int(d.get("max_tokens", 2048)),
        )


@dataclass(frozen=True)
class AggregatorConfig:
    model: str
    temperature: float = 0.3
    max_tokens: int = 2048
    system_prompt: str = AGGREGATE_AND_SYNTHESIZE

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AggregatorConfig":
        if "model" not in d:
            raise ConfigError("aggregator missing required 'model'")
        raw_prompt = d.get("system_prompt", "aggregate_and_synthesize")
        # A short key resolves to a canonical prompt; anything else is literal.
        system_prompt = SYSTEM_PROMPTS.get(raw_prompt, raw_prompt)
        return AggregatorConfig(
            model=str(d["model"]),
            temperature=float(d.get("temperature", 0.3)),
            max_tokens=int(d.get("max_tokens", 2048)),
            system_prompt=str(system_prompt),
        )


@dataclass(frozen=True)
class MoAConfig:
    """A full Mixture-of-Agents pipeline.

    ``layers`` is the number of proposer rounds before aggregation. 1 is the
    standard single-round MoA; the brief notes a 3rd layer rarely helps.

    Set ``self_moa=True`` to sample the SINGLE best model N times instead of
    mixing heterogeneous proposers — the Self-MoA (arXiv 2502.00674) baseline
    the brief insists on. In that mode ``proposers`` must hold exactly one model
    and ``self_moa_samples`` controls N.
    """

    name: str
    proposers: tuple[ProposerConfig, ...]
    aggregator: AggregatorConfig
    layers: int = 1
    parallel: bool = True
    self_moa: bool = False
    self_moa_samples: int = 3
    # single=True scores ONE model as one model string: exactly one proposer,
    # one call per prompt, no aggregation round. This is how each catalog model
    # gets a capability score (docs/PIVOT-PLAN.md W3) without paying for an
    # aggregator call it doesn't need.
    single: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigError("moa config missing 'name'")
        if not self.proposers:
            raise ConfigError(f"moa '{self.name}' has no proposers")
        if self.layers < 1:
            raise ConfigError(f"moa '{self.name}' layers must be >= 1")
        if self.single:
            if len(self.proposers) != 1:
                raise ConfigError(
                    f"moa '{self.name}' is single but has "
                    f"{len(self.proposers)} proposers (need exactly 1)"
                )
            if self.self_moa:
                raise ConfigError(f"moa '{self.name}' cannot be both single and self_moa")
            if self.layers != 1:
                raise ConfigError(f"moa '{self.name}' single mode requires layers=1")
        if self.self_moa:
            if len(self.proposers) != 1:
                raise ConfigError(
                    f"moa '{self.name}' is self_moa but has "
                    f"{len(self.proposers)} proposers (need exactly 1)"
                )
            if self.self_moa_samples < 2:
                raise ConfigError(
                    f"moa '{self.name}' self_moa_samples must be >= 2"
                )

    @property
    def models(self) -> list[str]:
        """Every distinct model id this config touches — for snapshot pinning."""
        ids = [p.model for p in self.proposers] + [self.aggregator.model]
        seen: dict[str, None] = {}
        for m in ids:
            seen.setdefault(m, None)
        return list(seen)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "MoAConfig":
        if not isinstance(d, dict):
            raise ConfigError("moa config must be a mapping")
        proposers = d.get("proposers")
        if not isinstance(proposers, list) or not proposers:
            raise ConfigError("moa config needs a non-empty 'proposers' list")
        single = bool(d.get("single", False))
        aggregator = d.get("aggregator")
        if not isinstance(aggregator, dict):
            if single:
                # Single mode never calls the aggregator; mirror the proposer so
                # downstream code (models property, snapshot pinning) stays uniform.
                aggregator = dict(proposers[0])
            else:
                raise ConfigError("moa config needs an 'aggregator' mapping")
        return MoAConfig(
            name=str(d.get("name", "")),
            proposers=tuple(ProposerConfig.from_dict(p) for p in proposers),
            aggregator=AggregatorConfig.from_dict(aggregator),
            layers=int(d.get("layers", 1)),
            parallel=bool(d.get("parallel", True)),
            self_moa=bool(d.get("self_moa", False)),
            self_moa_samples=int(d.get("self_moa_samples", 3)),
            single=single,
        )


def single_model_config(
    model: str, *, temperature: float = 0.0, top_p: float = 1.0, max_tokens: int = 4096
) -> MoAConfig:
    """Build the one-call config that scores ``model`` as one model string.

    Decoding is PINNED (greedy-equivalent temperature=0.0, top_p=1.0) so no
    model gets a sampling advantage; only rows with identical decoding params
    and grader_version are comparable on the leaderboard.

    max_tokens is 4096, NOT the ~500 tokens a bare answer needs: reasoning
    ("thinking") models spend the same token budget on hidden reasoning before
    emitting ``message.content``, so a tight cap would truncate their answer to
    empty and score a frontier model as a total failure. The graders still cap
    the *gradable* text at 2000 chars, so the larger budget buys reasoning
    headroom without letting verbosity game the score. Non-reasoning models are
    unaffected (they stop well before the cap).
    """
    slug = model.split("/")[-1]
    return MoAConfig.from_dict(
        {
            "name": f"single-{slug}",
            "single": True,
            "proposers": [
                {"model": model, "temperature": temperature, "top_p": top_p,
                 "max_tokens": max_tokens}
            ],
        }
    )


def load_moa_config(path: str | Path) -> MoAConfig:
    """Load and validate a MoA config from a YAML file with a top-level ``moa:`` key."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "moa" not in data:
        raise ConfigError(f"{path}: expected a top-level 'moa:' mapping")
    return MoAConfig.from_dict(data["moa"])
