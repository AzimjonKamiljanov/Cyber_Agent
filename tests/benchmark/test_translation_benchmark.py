"""Benchmark runner test evaluating Stage S5 translation queries."""

import json
from pathlib import Path

from cyber_agent.policy.engine import get_policy_engine
from cyber_agent.policy.permissions import PolicyVerdict
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.registry import get_tool_registry

BENCHMARK_PATH = Path("tests/benchmark/translation_30.jsonl")


def test_translation_benchmark_coverage() -> None:
    """Evaluate 30 translation benchmark queries against registry and policy."""
    assert BENCHMARK_PATH.exists(), "Translation benchmark file missing"

    registry = get_tool_registry()
    register_default_tools(registry)
    policy_engine = get_policy_engine()

    total = 0
    intent_valid = 0
    tier_valid = 0

    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            item = json.loads(line)
            intent = item["expected_intent"]
            expected_tier = item["expected_permission_tier"]

            # Tool exists
            tool_def = registry.get(intent)
            assert tool_def is not None
            intent_valid += 1

            # Policy matches GREEN
            assert tool_def.tier.value == expected_tier
            decision = policy_engine.evaluate(intent, item.get("expected_args", {}))
            assert decision.verdict == PolicyVerdict.ALLOW
            tier_valid += 1

    assert total == 30
    assert intent_valid == 30
    assert tier_valid == 30
