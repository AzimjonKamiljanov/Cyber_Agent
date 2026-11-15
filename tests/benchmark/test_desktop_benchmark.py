"""Benchmark runner test evaluating Stage S4 desktop queries against policy and intent schemas."""

import json
from pathlib import Path

from cyber_agent.policy.engine import get_policy_engine
from cyber_agent.policy.permissions import PolicyVerdict
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.registry import get_tool_registry

BENCHMARK_PATH = Path("tests/benchmark/desktop_benchmark.jsonl")


def test_desktop_benchmark_policy_and_intent_coverage() -> None:
    """Evaluate 15 desktop benchmark test cases against registered tools and policy tiers."""
    assert BENCHMARK_PATH.exists(), "Desktop benchmark file missing"

    registry = get_tool_registry()
    register_default_tools(registry)
    policy_engine = get_policy_engine()

    total = 0
    tier_matches = 0
    intent_valid = 0

    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            item = json.loads(line)
            intent = item["expected_intent"]
            expected_tier = item["expected_permission_tier"]

            # 1. Intent must be a valid registered tool
            tool_def = registry.get(intent)
            assert tool_def is not None, f"Tool '{intent}' not found in registry"
            intent_valid += 1

            # 2. Permission tier must match policy
            registered_tier = tool_def.tier.value
            assert (
                registered_tier == expected_tier
            ), f"Tool {intent} tier mismatch: got {registered_tier}, expected {expected_tier}"
            tier_matches += 1

            # 3. Policy evaluation behavior
            decision = policy_engine.evaluate(intent, item.get("expected_args", {}))
            if expected_tier == "GREEN":
                assert decision.verdict == PolicyVerdict.ALLOW
            elif expected_tier == "YELLOW":
                assert decision.verdict == PolicyVerdict.CONFIRM

    assert total == 15
    assert intent_valid == 15
    assert tier_matches == 15
