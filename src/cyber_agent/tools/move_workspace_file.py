"""Tool: move_workspace_file (YELLOW tier).

Moves or renames files strictly within ~/cyber-workspace.
"""

from cyber_agent.tools.schemas import MoveWorkspaceFileArgs, ToolResult
from cyber_agent.tools.workspace_jail import resolve_jail_path


async def handle_move_workspace_file(args: MoveWorkspaceFileArgs) -> ToolResult:
    try:
        src_path = resolve_jail_path(args.source, must_exist=True)
        dest_path = resolve_jail_path(args.destination)
    except (PermissionError, FileNotFoundError) as e:
        return ToolResult(success=False, output="", error=str(e))

    if dest_path.exists():
        return ToolResult(
            success=False,
            output="",
            error=f"Manzil fayli '{args.destination}' allaqachon mavjud.",
        )

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.rename(dest_path)
        return ToolResult(
            success=True,
            output=f"'{args.source}' fayli muvaffaqiyatli '{args.destination}' ga ko'chirildi.",
        )
    except OSError as e:
        return ToolResult(success=False, output="", error=f"Faylni ko'chirishda xatolik: {e}")
