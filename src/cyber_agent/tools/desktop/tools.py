"""Desktop tools implementation for Cyber Agent Stage S4.

Implements:
- window_list (GREEN)
- window_focus (GREEN)
- read_ui_tree (GREEN)
- gui_click (YELLOW)
- gui_type (YELLOW)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.desktop.backend import get_desktop_driver
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import (
    GUIClickArgs,
    GUITypeArgs,
    ReadUITreeArgs,
    ToolResult,
    WindowFocusArgs,
    WindowListArgs,
)

logger = logging.getLogger(__name__)


async def handle_window_list(args: Any) -> ToolResult:
    driver = get_desktop_driver()
    windows = driver.list_windows()
    res = []
    for w in windows:
        if w.is_sensitive and not getattr(args, "include_sensitive", False):
            res.append({"id": w.id, "title": "[MAXFIY OYNA]", "monitor": w.monitor, "is_sensitive": True})
        else:
            res.append({"id": w.id, "title": w.title, "app": w.app_class, "monitor": w.monitor, "is_sensitive": w.is_sensitive})
    return ToolResult(
        success=True,
        output=json.dumps(res, ensure_ascii=False, indent=2),
    )


async def handle_window_focus(args: Any) -> ToolResult:
    driver = get_desktop_driver()
    target = getattr(args, "target", "")
    ok = driver.focus_window(target)
    if ok:
        return ToolResult(success=True, output=f"'{target}' oynasiga muvaffaqiyatli fokus o'rnatildi.")
    return ToolResult(success=False, output="", error=f"'{target}' nomli oyna topilmadi.")


async def handle_read_ui_tree(args: Any) -> ToolResult:
    driver = get_desktop_driver()
    target = getattr(args, "window_title", None)
    depth = getattr(args, "max_depth", 3)
    tree = driver.read_ui_tree(window_title=target, max_depth=depth)
    return ToolResult(
        success=True,
        output=json.dumps(tree, ensure_ascii=False, indent=2),
    )


async def handle_gui_click(args: Any) -> ToolResult:
    driver = get_desktop_driver()
    x = getattr(args, "x", 0)
    y = getattr(args, "y", 0)
    monitor = getattr(args, "monitor", "primary")
    target_win = getattr(args, "target_window", "")

    if target_win and driver.is_sensitive_window(target_win):
        return ToolResult(
            success=False,
            output="",
            error=f"Xavfsizlik qoidasi: '{target_win}' maxfiy oynalar ro'yxatida bo'lgani sababli bosish rad etildi.",
        )

    ok = driver.click(x=x, y=y, monitor=monitor, target_window=target_win)
    if ok:
        return ToolResult(success=True, output=f"{monitor.capitalize()} monitorda ({x}, {y}) koordinatasida bosildi.")
    return ToolResult(success=False, output="", error="Bosish amalga oshirilmadi (koordinatalar xato yoki oyna bloklangan).")


async def handle_gui_type(args: Any) -> ToolResult:
    driver = get_desktop_driver()
    text = getattr(args, "text", "")
    target_win = getattr(args, "target_window", "")
    role = getattr(args, "target_element_role", "")
    name = getattr(args, "target_element_name", "")

    # Invariant 1: Strictly refuse password fields
    if driver.is_password_field(role, name):
        return ToolResult(
            success=False,
            output="",
            error="Xavfsizlik qoidasi: Parol yoki maxfiy maydonlarga avtomatik yozish qat'iyan taqiqlangan.",
        )

    # Invariant 2: Strictly refuse sensitive windows
    if target_win and driver.is_sensitive_window(target_win):
        return ToolResult(
            success=False,
            output="",
            error=f"Xavfsizlik qoidasi: '{target_win}' maxfiy oynasida matn kiritish taqiqlangan.",
        )

    ok = driver.type_text(text, target_window=target_win, target_element_role=role, target_element_name=name)
    if ok:
        return ToolResult(success=True, output=f"'{target_win}' oynasiga matn muvaffaqiyatli kiritildi.")
    return ToolResult(success=False, output="", error="Matn kiritish rad etildi.")


def register_desktop_tools(registry: ToolRegistry) -> None:
    """Register desktop inspection and actuation tools."""
    registry.register(
        ToolDefinition(
            name="window_list",
            description="Ochiq ishchi stoli oynalari ro'yxatini va ularning monitorini ko'rish.",
            tier=PolicyTier.GREEN,
            args_schema=WindowListArgs,
            handler=handle_window_list,
        )
    )
    registry.register(
        ToolDefinition(
            name="window_focus",
            description="Ko'rsatilgan dastur yoki oyna sarlavhasiga fokus o'rnatish.",
            tier=PolicyTier.GREEN,
            args_schema=WindowFocusArgs,
            handler=handle_window_focus,
        )
    )
    registry.register(
        ToolDefinition(
            name="read_ui_tree",
            description="Faol oyna yoki dasturning semantik AT-SPI foydalanuvchi interfeysi (UI) daraxtini o'qish.",
            tier=PolicyTier.GREEN,
            args_schema=ReadUITreeArgs,
            handler=handle_read_ui_tree,
        )
    )
    registry.register(
        ToolDefinition(
            name="gui_click",
            description="Ko'rsatilgan monitor va koordinatada sichqoncha bosishini bajarish (YELLOW tier, tasdiqlash talab qilinadi).",
            tier=PolicyTier.YELLOW,
            args_schema=GUIClickArgs,
            handler=handle_gui_click,
        )
    )
    registry.register(
        ToolDefinition(
            name="gui_type",
            description="Nishon oynadagi maydonga matn yozish. Parol maydonlariga kiritish taqiqlangan (YELLOW tier).",
            tier=PolicyTier.YELLOW,
            args_schema=GUITypeArgs,
            handler=handle_gui_type,
        )
    )
