import pytest

from agentbench.config import (
    AGGREGATE_AND_SYNTHESIZE,
    ConfigError,
    MoAConfig,
    load_moa_config,
)
from agentbench.resources import MOA_V1, SELF_MOA


def test_load_example_preset():
    cfg = load_moa_config(MOA_V1)
    assert cfg.name == "moa-v1"
    assert len(cfg.proposers) == 3
    assert cfg.aggregator.system_prompt == AGGREGATE_AND_SYNTHESIZE  # key resolved
    assert cfg.layers == 1
    # models() dedupes and includes the aggregator, for snapshot pinning.
    assert "openrouter/anthropic/claude-sonnet-4" in cfg.models


def test_self_moa_preset_valid():
    cfg = load_moa_config(SELF_MOA)
    assert cfg.self_moa is True
    assert cfg.self_moa_samples == 3
    assert len(cfg.proposers) == 1


def test_inline_system_prompt_is_literal():
    cfg = MoAConfig.from_dict(
        {
            "name": "x",
            "proposers": [{"model": "a"}],
            "aggregator": {"model": "b", "system_prompt": "be terse"},
        }
    )
    assert cfg.aggregator.system_prompt == "be terse"


def test_missing_proposers_rejected():
    with pytest.raises(ConfigError):
        MoAConfig.from_dict({"name": "x", "aggregator": {"model": "b"}})


def test_self_moa_requires_single_proposer():
    with pytest.raises(ConfigError):
        MoAConfig.from_dict(
            {
                "name": "x",
                "self_moa": True,
                "proposers": [{"model": "a"}, {"model": "b"}],
                "aggregator": {"model": "b"},
            }
        )


def test_aggregator_requires_model():
    with pytest.raises(ConfigError):
        MoAConfig.from_dict(
            {"name": "x", "proposers": [{"model": "a"}], "aggregator": {}}
        )
