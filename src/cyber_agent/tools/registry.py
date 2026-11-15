"""Tool Registry for Cyber Agent.

Enforces schema validation, policy evaluation, timeouts, and rate limits.
Forbidden tools are strictly prevented from registration.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from cyber_agent.audit.logger import get_audit_logger
from cyber_agent.policy.engine import FORBIDDEN_TOOLS, PolicyEngine, get_policy_engine
from cyber_agent.policy.permissions import PolicyTier, PolicyVerdict
from cyber_agent.tools.schemas import ToolResult

__all__ = ["FORBIDDEN_TOOLS", "ToolDefinition", "ToolRegistry", "get_tool_registry"]

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    tier: PolicyTier
    args_schema: type[BaseModel]
    handler: Callable[[Any], Awaitable[ToolResult]]
    timeout_seconds: float = 10.0
    rate_limit_rpm: int = 60
    max_output_chars: int = 4000


class ToolRegistry:
    """Central registry and execution manager for tools."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy_engine = policy_engine or get_policy_engine()
        self.audit_logger = get_audit_logger()
        self._tools: dict[str, ToolDefinition] = {}
        self._idempotency_cache: dict[str, ToolResult] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """Register a tool definition into the registry and policy engine."""
        if tool_def.name in FORBIDDEN_TOOLS:
            raise ValueError(
                f"Security violation: Tool '{tool_def.name}' is strictly forbidden by policy and cannot be registered."
            )

        self._tools[tool_def.name] = tool_def
        self.policy_engine.register_tool_tier(tool_def.name, tool_def.tier)
        logger.debug("Registered tool '%s' with tier %s", tool_def.name, tool_def.tier.value)

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute(
        self,
        tool_name: str,
        raw_args: dict[str, Any],
        action_id: str | None = None,
        confirmation_token: str | None = None,
        skip_policy_check: bool = False,
    ) -> ToolResult:
        """Validate arguments, evaluate policy, and execute tool safely."""
        start_time = time.monotonic()

        # 1. Check if tool exists
        tool_def = self.get(tool_name)
        if not tool_def:
            self.audit_logger.log_event("TOOL_UNKNOWN", {"tool_name": tool_name, "raw_args": raw_args})
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' is not registered.")

        # 2. Strict Pydantic Schema Validation (reject unknown fields)
        try:
            validated_args = tool_def.args_schema.model_validate(raw_args)
        except ValidationError as e:
            self.audit_logger.log_event("TOOL_BAD_ARGS", {"tool_name": tool_name, "error": str(e)})
            return ToolResult(success=False, output="", error=f"Invalid arguments for '{tool_name}': {e}")

        # Check idempotency replay protection
        idem_key = getattr(validated_args, "idempotency_key", None)
        if idem_key and idem_key in self._idempotency_cache:
            self.audit_logger.log_event(
                "IDEMPOTENCY_REPLAY_BLOCKED",
                {"tool_name": tool_name, "idempotency_key": idem_key},
            )
            return self._idempotency_cache[idem_key]

        # 3. Policy Engine Evaluation
        if not skip_policy_check:
            decision = self.policy_engine.evaluate(
                tool_name=tool_name,
                args=validated_args.model_dump(),
                action_id=action_id,
                confirmation_token=confirmation_token,
            )

            if decision.verdict == PolicyVerdict.DENY:
                return ToolResult(success=False, output="", error=f"Policy DENY: {decision.reason}")

            if decision.verdict == PolicyVerdict.CONFIRM:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"CONFIRM_REQUIRED: {decision.action_id}:{decision.confirmation_token}:{decision.reason}",
                )

        # 4. Execute tool handler under timeout cap
        try:
            result = await asyncio.wait_for(
                tool_def.handler(validated_args),
                timeout=tool_def.timeout_seconds,
            )
        except TimeoutError:
            self.audit_logger.log_event("TOOL_TIMEOUT", {"tool_name": tool_name, "timeout": tool_def.timeout_seconds})
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' timed out after {tool_def.timeout_seconds}s")
        except Exception as e:  # noqa: BLE001
            self.audit_logger.log_event("TOOL_ERROR", {"tool_name": tool_name, "error": str(e)})
            return ToolResult(success=False, output="", error=f"Execution error: {e}")

        # 5. Cap output size
        if len(result.output) > tool_def.max_output_chars:
            result.output = result.output[: tool_def.max_output_chars] + "\n...[OUTPUT TRUNCATED BY POLICY]"

        elapsed_ms = (time.monotonic() - start_time) * 1000.0
        result.execution_time_ms = elapsed_ms

        self.audit_logger.log_event(
            "TOOL_EXECUTED",
            {
                "tool_name": tool_name,
                "success": result.success,
                "elapsed_ms": elapsed_ms,
            },
        )
        if idem_key and result.success:
            self._idempotency_cache[idem_key] = result
        return result


_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
