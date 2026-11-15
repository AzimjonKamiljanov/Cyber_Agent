"""Tool: search_workspace (GREEN tier)."""

from cyber_agent.tools.schemas import SearchWorkspaceArgs, ToolResult
from cyber_agent.tools.workspace_jail import get_workspace_root


async def handle_search_workspace(args: SearchWorkspaceArgs) -> ToolResult:
    root = get_workspace_root()
    matches: list[str] = []
    q_lower = args.query.lower()

    for item in root.rglob("*"):
        if len(matches) >= args.max_results:
            break
        # Match filename
        if q_lower in item.name.lower():
            rel_path = item.relative_to(root)
            matches.append(f"[Fayl nomi]: {rel_path}")
            continue

        # Match content inside text files (< 1MB)
        if item.is_file() and item.stat().st_size < 1024 * 1024:
            try:
                text = item.read_text(encoding="utf-8", errors="ignore")
                if q_lower in text.lower():
                    rel_path = item.relative_to(root)
                    matches.append(f"[Matn ichida]: {rel_path}")
            except OSError:
                pass

    if not matches:
        return ToolResult(success=True, output=f"'{args.query}' bo'yicha hech qanday fayl topilmadi.")

    out = f"Workspace ichida '{args.query}' bo'yicha {len(matches)} ta natija:\n" + "\n".join(matches)
    return ToolResult(success=True, output=out)
