"""Tool: write_workspace_file (YELLOW tier).

Writes a new file inside ~/cyber-workspace.
Does not overwrite existing files without explicit user confirmation.
"""

from cyber_agent.tools.schemas import ToolResult, WriteWorkspaceFileArgs
from cyber_agent.tools.workspace_jail import resolve_jail_path


async def handle_write_workspace_file(args: WriteWorkspaceFileArgs) -> ToolResult:
    try:
        target_path = resolve_jail_path(args.filename)
    except PermissionError as e:
        return ToolResult(success=False, output="", error=str(e))

    if target_path.exists():
        return ToolResult(
            success=False,
            output="",
            error=f"Fayl '{args.filename}' allaqachon mavjud. Ustidan yozish taqiqlangan.",
        )

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(args.content, encoding="utf-8")
        return ToolResult(
            success=True,
            output=f"Fayl '{args.filename}' muvaffaqiyatli yaratildi ({len(args.content)} belgi).",
        )
    except OSError as e:
        return ToolResult(success=False, output="", error=f"Fayl yozishda xatolik: {e}")
