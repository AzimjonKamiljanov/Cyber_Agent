"""Google Calendar tools for Cyber Agent (Stage S5).

Implements:
- get_calendar_events (GREEN tier)
- create_calendar_event (YELLOW tier, guarded by CYBER_CALENDAR_WRITE)
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.integrations.google_calendar import get_calendar_client
from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import (
    CreateCalendarEventArgs,
    GetCalendarEventsArgs,
    ToolResult,
)

logger = logging.getLogger(__name__)


async def handle_get_calendar_events(args: Any) -> ToolResult:
    """Fetch calendar events."""
    client = get_calendar_client()
    days = getattr(args, "days", 1)
    max_results = getattr(args, "max_results", 10)

    ok, msg, events = client.get_events(days=days, max_results=max_results)
    if not ok:
        return ToolResult(success=False, output="", error=msg)

    if not events:
        return ToolResult(success=True, output="Belgilangan muddatda hech qanday tadbir topilmadi.")

    formatted = [
        f"- {ev.title} (Boshlanishi: {ev.start_time[:16]}, Tugashi: {ev.end_time[:16]})"
        for ev in events
    ]
    return ToolResult(
        success=True,
        output="Taqvimdagi tadbirlar:\n" + "\n".join(formatted),
    )


async def handle_create_calendar_event(args: Any) -> ToolResult:
    """Create a new calendar event (YELLOW tier)."""
    client = get_calendar_client()
    title = getattr(args, "title", "")
    start_time = getattr(args, "start_time", "")
    end_time = getattr(args, "end_time", "")
    description = getattr(args, "description", "")

    ok, msg = client.create_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
    )
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


def register_calendar_tools(registry: ToolRegistry) -> None:
    """Register Google Calendar tools."""
    registry.register(
        ToolDefinition(
            name="get_calendar_events",
            description="Google Calendar tadbirlarini ko'rish (GREEN tier).",
            tier=PolicyTier.GREEN,
            args_schema=GetCalendarEventsArgs,
            handler=handle_get_calendar_events,
        )
    )
    registry.register(
        ToolDefinition(
            name="create_calendar_event",
            description="Taqvimga yangi tadbir qo'shish (YELLOW tier, CYBER_CALENDAR_WRITE talab qiladi).",
            tier=PolicyTier.YELLOW,
            args_schema=CreateCalendarEventArgs,
            handler=handle_create_calendar_event,
        )
    )
