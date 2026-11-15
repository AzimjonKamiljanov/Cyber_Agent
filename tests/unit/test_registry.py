"""Unit tests for tool registry and forbidden tools invariant."""

import asyncio

import pytest

from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import FORBIDDEN_TOOLS, ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import BaseToolArgs, ToolResult


class DummyArgs(BaseToolArgs):
    param: str


async def dummy_handler(args: DummyArgs) -> ToolResult:
    return ToolResult(success=True, output=f"result: {args.param}")


async def slow_handler(args: DummyArgs) -> ToolResult:
    await asyncio.sleep(0.5)
    return ToolResult(success=True, output="slow done")


def test_forbidden_tools_cannot_be_registered() -> None:
    registry = ToolRegistry()

    for forbidden in FORBIDDEN_TOOLS:
        with pytest.raises(ValueError, match="strictly forbidden"):
            registry.register(
                ToolDefinition(
                    name=forbidden,
                    description="Malicious tool attempt",
                    tier=PolicyTier.RED,
                    args_schema=DummyArgs,
                    handler=dummy_handler,
                )
            )

    # Assert active tools list never contains forbidden items
    active_names = {t.name for t in registry.list_tools()}
    assert active_names.isdisjoint(FORBIDDEN_TOOLS)


@pytest.mark.asyncio
async def test_tool_extra_arguments_rejected() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="dummy_tool",
            description="A test tool",
            tier=PolicyTier.GREEN,
            args_schema=DummyArgs,
            handler=dummy_handler,
        )
    )

    # Extra arguments injected (prompt injection style)
    bad_args = {"param": "ok", "extra_injected_cmd": "rm -rf"}
    result = await registry.execute("dummy_tool", bad_args)
    assert result.success is False
    assert "Invalid arguments" in (result.error or "")


@pytest.mark.asyncio
async def test_tool_timeout_and_output_cap() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="slow_tool",
            description="A slow tool",
            tier=PolicyTier.GREEN,
            args_schema=DummyArgs,
            handler=slow_handler,
            timeout_seconds=0.1,  # short timeout
            max_output_chars=20,
        )
    )

    # 1. Timeout check
    res_timeout = await registry.execute("slow_tool", {"param": "test"})
    assert res_timeout.success is False
    assert "timed out" in (res_timeout.error or "")

    # 2. Output cap check
    async def verbose_handler(args: DummyArgs) -> ToolResult:
        return ToolResult(success=True, output="A" * 100)

    registry.register(
        ToolDefinition(
            name="verbose_tool",
            description="Verbose tool",
            tier=PolicyTier.GREEN,
            args_schema=DummyArgs,
            handler=verbose_handler,
            max_output_chars=20,
        )
    )
    res_cap = await registry.execute("verbose_tool", {"param": "test"})
    assert res_cap.success is True
    assert len(res_cap.output) < 60
    assert "TRUNCATED BY POLICY" in res_cap.output
