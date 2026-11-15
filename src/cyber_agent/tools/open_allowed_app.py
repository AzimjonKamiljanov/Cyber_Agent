"""Tool: open_allowed_app (GREEN tier)."""

import asyncio
import subprocess
import tomllib
from pathlib import Path

from cyber_agent.tools.schemas import OpenAllowedAppArgs, ToolResult


def load_allowed_apps() -> dict[str, list[str]]:
    allowlist_file = Path(__file__).resolve().parent.parent.parent.parent / "config" / "apps_allowlist.toml"
    if not allowlist_file.exists():
        return {}

    try:
        data = tomllib.loads(allowlist_file.read_text(encoding="utf-8"))
        apps = data.get("apps", {})
        return {k.lower(): v.get("command", [k]) for k, v in apps.items()}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


async def handle_open_allowed_app(args: OpenAllowedAppArgs) -> ToolResult:
    allowed = load_allowed_apps()
    app_key = args.app_name.strip().lower()

    if app_key not in allowed:
        valid_list = ", ".join(allowed.keys())
        return ToolResult(
            success=False,
            output="",
            error=f"Ilova '{args.app_name}' ruxsat etilgan ilovalar ro'yxatida yo'q. Ruxsat etilganlar: {valid_list}",
        )

    cmd = allowed[app_key]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
        return ToolResult(
            success=True,
            output=f"'{args.app_name}' ilovasi muvaffaqiyatli ishga tushirildi (PID: {proc.pid}).",
        )
    except (OSError, subprocess.SubprocessError) as e:
        return ToolResult(success=False, output="", error=f"Ilovani ishga tushirishda xatolik: {e}")
