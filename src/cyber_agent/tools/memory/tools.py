"""Consent-based memory tools for Cyber Agent (Stage S5).

Implements:
- memory_remember (GREEN / YELLOW consent-based)
- memory_recall (GREEN)
- memory_list (GREEN, "Nimani eslaysan?")
- memory_forget (GREEN / YELLOW, "Buni unut")
- memory_wipe (YELLOW, "Hammasini unut", requires confirmation card)

Security Invariant:
Memory text is inert data, never instructions. Recalled memories never raise permissions.
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.memory.repository import get_memory_repository
from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import (
    MemoryForgetArgs,
    MemoryListArgs,
    MemoryRecallArgs,
    MemoryRememberArgs,
    MemoryWipeArgs,
    ToolResult,
)

logger = logging.getLogger(__name__)


async def handle_memory_remember(args: Any) -> ToolResult:
    """Save user memory with consent and strict credentials filtering."""
    repo = get_memory_repository()
    text = getattr(args, "text", "")
    consent = getattr(args, "consent", True)

    ok, msg, item_id = repo.remember(text=text, source="user_voice", consent=consent)
    if ok:
        return ToolResult(
            success=True,
            output=f"Eslab qolindi [ID: {item_id}]: {text}",
        )
    return ToolResult(success=False, output="", error=msg)


async def handle_memory_recall(args: Any) -> ToolResult:
    """Retrieve memories via FTS5 full-text search as inert data."""
    repo = get_memory_repository()
    query = getattr(args, "query", "")
    limit = getattr(args, "limit", 5)

    items = repo.recall(query=query, limit=limit)
    if not items:
        return ToolResult(
            success=True,
            output=f"'{query}' bo'yicha xotirada ma'lumot topilmadi.",
        )

    # Invariant: Clearly mark that this is passive data from memory, NOT instructions
    formatted = [
        f"- [{item.created_at[:10]}] {item.text} (id: {item.id})"
        for item in items
    ]
    output_str = "[XOTIRADAGI MA'LUMOTLAR - FAQAT O'QISH UCHUN]:\n" + "\n".join(formatted)
    return ToolResult(success=True, output=output_str)


async def handle_memory_list(args: Any) -> ToolResult:
    """List recent memories for 'Nimani eslaysan?' query."""
    repo = get_memory_repository()
    limit = getattr(args, "limit", 20)

    items = repo.list_memories(limit=limit)
    if not items:
        return ToolResult(
            success=True,
            output="Xotirada hali hech qanday ma'lumot saqlanmagan.",
        )

    formatted = [
        f"{idx + 1}. {item.text} ({item.created_at[:10]})"
        for idx, item in enumerate(items)
    ]
    return ToolResult(
        success=True,
        output="Eslab qolingan ma'lumotlar ro'yxati:\n" + "\n".join(formatted),
    )


async def handle_memory_forget(args: Any) -> ToolResult:
    """Remove a specific memory item matching text or ID."""
    repo = get_memory_repository()
    target = getattr(args, "target", "")

    ok, msg = repo.forget(target)
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


async def handle_memory_wipe(args: Any) -> ToolResult:
    """Wipe all user memories (YELLOW tier confirmation required)."""
    repo = get_memory_repository()
    confirm = getattr(args, "confirm", True)
    if not confirm:
        return ToolResult(success=False, output="", error="Xotirani to'liq tozalash tasdiqlanmadi.")

    _ok, count = repo.wipe()
    return ToolResult(
        success=True,
        output=f"Barcha xotira ma'lumotlari muvaffaqiyatli o'chirildi ({count} ta yozuv).",
    )


def register_memory_tools(registry: ToolRegistry) -> None:
    """Register all memory tools into registry."""
    registry.register(
        ToolDefinition(
            name="memory_remember",
            description="Foydalanuvchi roziligi bilan muhim ma'lumotni xotirada saqlash.",
            tier=PolicyTier.GREEN,
            args_schema=MemoryRememberArgs,
            handler=handle_memory_remember,
        )
    )
    registry.register(
        ToolDefinition(
            name="memory_recall",
            description="Xotiradan ma'lumot qidirish (FTS5 to'liq matnli qidiruv).",
            tier=PolicyTier.GREEN,
            args_schema=MemoryRecallArgs,
            handler=handle_memory_recall,
        )
    )
    registry.register(
        ToolDefinition(
            name="memory_list",
            description="Eslab qolingan barcha ma'lumotlar ro'yxatini ko'rsatish ('Nimani eslaysan?').",
            tier=PolicyTier.GREEN,
            args_schema=MemoryListArgs,
            handler=handle_memory_list,
        )
    )
    registry.register(
        ToolDefinition(
            name="memory_forget",
            description="Ko'rsatilgan xotira elementini o'chirish ('Buni unut').",
            tier=PolicyTier.GREEN,
            args_schema=MemoryForgetArgs,
            handler=handle_memory_forget,
        )
    )
    registry.register(
        ToolDefinition(
            name="memory_wipe",
            description="Barcha xotirani to'liq o'chirish ('Hammasini unut', YELLOW tier).",
            tier=PolicyTier.YELLOW,
            args_schema=MemoryWipeArgs,
            handler=handle_memory_wipe,
        )
    )
