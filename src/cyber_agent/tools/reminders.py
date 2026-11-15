"""Reminder management tools for Cyber Agent (Stage S5).

Implements:
- create_reminder (GREEN / YELLOW)
- list_reminders (GREEN)
- cancel_reminder (GREEN / YELLOW)
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.memory.reminders import get_reminder_scheduler
from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import (
    CancelReminderArgs,
    CreateReminderArgs,
    ListRemindersArgs,
    ToolResult,
)

logger = logging.getLogger(__name__)


async def handle_create_reminder(args: Any) -> ToolResult:
    """Create a persistent reminder."""
    scheduler = get_reminder_scheduler()
    title = getattr(args, "title", "")
    remind_at = getattr(args, "remind_at", "")
    channel = getattr(args, "channel", "all")

    ok, msg, _item = scheduler.add_reminder(title=title, remind_at_str=remind_at, channel=channel)
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


async def handle_list_reminders(args: Any) -> ToolResult:
    """List pending reminders."""
    scheduler = get_reminder_scheduler()
    include_completed = getattr(args, "include_completed", False)

    items = scheduler.list_reminders(include_completed=include_completed)
    if not items:
        return ToolResult(success=True, output="Faol eslatmalar mavjud emas.")

    formatted = [
        f"- [ID: {item.id}] '{item.title}' — Vaqti: {item.remind_at[:19]} ({item.status})"
        for item in items
    ]
    return ToolResult(
        success=True,
        output="Mavjud eslatmalar:\n" + "\n".join(formatted),
    )


async def handle_cancel_reminder(args: Any) -> ToolResult:
    """Cancel an existing reminder."""
    scheduler = get_reminder_scheduler()
    rem_id = getattr(args, "reminder_id", "")

    ok, msg = scheduler.cancel_reminder(rem_id)
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


def register_reminder_tools(registry: ToolRegistry) -> None:
    """Register reminder tools into the tool registry."""
    registry.register(
        ToolDefinition(
            name="create_reminder",
            description="Toshkent vaqti bilan kelajakdagi aniq daqiqa yoki soatga eslatma o'rnatish.",
            tier=PolicyTier.GREEN,
            args_schema=CreateReminderArgs,
            handler=handle_create_reminder,
        )
    )
    registry.register(
        ToolDefinition(
            name="list_reminders",
            description="Faol va rejalashtirilgan eslatmalar ro'yxatini ko'rsatish.",
            tier=PolicyTier.GREEN,
            args_schema=ListRemindersArgs,
            handler=handle_list_reminders,
        )
    )
    registry.register(
        ToolDefinition(
            name="cancel_reminder",
            description="Eslatmani ID raqami yoki nomi bo'yicha bekor qilish.",
            tier=PolicyTier.GREEN,
            args_schema=CancelReminderArgs,
            handler=handle_cancel_reminder,
        )
    )
