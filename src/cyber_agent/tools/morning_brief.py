"""Morning brief tool for Cyber Agent (Stage S5).

Implements:
- get_morning_brief (GREEN tier, "Ertalabki xulosa")
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.memory.morning_brief import generate_morning_brief
from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import GetMorningBriefArgs, ToolResult

logger = logging.getLogger(__name__)


async def handle_get_morning_brief(args: Any) -> ToolResult:
    """Compose and return the daily morning brief."""
    brief = await generate_morning_brief()
    return ToolResult(
        success=True,
        output=brief.get("spoken_text", ""),
    )


def register_morning_brief_tools(registry: ToolRegistry) -> None:
    """Register morning brief tool into the registry."""
    registry.register(
        ToolDefinition(
            name="get_morning_brief",
            description="Bugungi kun uchun ertalabki umumiy xulosani (ob-havo, eslatmalar, taqvim) taqdim etadi ('Ertalabki xulosa').",
            tier=PolicyTier.GREEN,
            args_schema=GetMorningBriefArgs,
            handler=handle_get_morning_brief,
        )
    )
