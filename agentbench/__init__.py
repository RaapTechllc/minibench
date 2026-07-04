"""agentbench — a contamination-resistant agent/MoA benchmark platform.

This is the clean module the AGENT-BENCH-BRIEF recommends building (rather than
extending the drifted ``benchmarks/`` prototype). Design goals:

- **MoA-as-a-model:** a Mixture-of-Agents pipeline is expressed as data and wrapped
  behind a single ``generate(prompt) -> MoAResult`` adapter, so the rest of the
  harness treats a whole MoA config as one "model".
- **One OpenAI-compatible client** covers OpenRouter (cloud) and Ollama (local &
  cloud); only ``base_url``/``api_key``/``model`` differ. Real per-call cost comes
  from OpenRouter's ``usage.cost`` field.
- **Executable grading**, never keyword presence — a grader that cannot fail a
  deliberately-bad answer does not discriminate.
- **Offline-testable:** every network boundary is injectable, so the fan-out,
  grading and model-tracking logic is unit-tested with fakes and no API keys.

Live model calls are gated on the presence of provider API keys in the
environment; nothing here reaches the network unless you wire in a real client.
"""

from agentbench.config import (
    MoAConfig,
    ProposerConfig,
    AggregatorConfig,
    load_moa_config,
)
from agentbench.client import ChatMessage, ChatResult, Usage, OpenAICompatClient
from agentbench.moa import MoAModel, MoAResult
from agentbench.grading import (
    GradeResult,
    exact_match,
    numeric_match,
    json_fields,
    unit_test,
    grade,
)
from agentbench.tracker import ModelInfo, diff_models

__all__ = [
    "MoAConfig",
    "ProposerConfig",
    "AggregatorConfig",
    "load_moa_config",
    "ChatMessage",
    "ChatResult",
    "Usage",
    "OpenAICompatClient",
    "MoAModel",
    "MoAResult",
    "GradeResult",
    "exact_match",
    "numeric_match",
    "json_fields",
    "unit_test",
    "grade",
    "ModelInfo",
    "diff_models",
]
