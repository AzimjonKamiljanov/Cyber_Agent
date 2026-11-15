"""Tool: run_allowed_command (YELLOW tier).

Executes allowlisted commands inside rootless bubblewrap sandbox.
Requires user confirmation card showing the exact argv arguments.
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.sandbox.executor import get_sandbox_executor, is_command_allowed
from cyber_agent.tools.schemas import ToolResult

logger = logging.getLogger(__name__)


async def handle_run_allowed_command(args: Any) -> ToolResult:
    """Execute allowlisted command inside bubblewrap."""
    argv: list[str] = getattr(args, "argv", [])
    if not argv:
        return ToolResult(success=False, output="", error="Hech qanday buyruq berilmadi.")

    # Preliminary validation check
    allowed, reason = is_command_allowed(argv)
    if not allowed:
        return ToolResult(
            success=False,
            output="",
            error=f"Buyruq rad etildi: {reason}",
        )

    executor = get_sandbox_executor()
    code, stdout, stderr = await executor.run(argv)

    full_output = stdout
    if stderr:
        full_output += ("\n" if full_output else "") + stderr

    if code == 0:
        return ToolResult(
            success=True,
            output=full_output.strip() or f"Buyruq muvaffaqiyatli bajarildi (kod: {code})",
        )

    return ToolResult(
        success=False,
        output=full_output.strip(),
        error=f"Buyruq xatolik bilan tugadi (kod: {code})",
    )
