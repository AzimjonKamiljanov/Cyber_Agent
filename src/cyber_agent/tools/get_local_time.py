"""Tool: get_local_time (GREEN tier)."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cyber_agent.tools.schemas import GetLocalTimeArgs, ToolResult


async def handle_get_local_time(args: GetLocalTimeArgs) -> ToolResult:
    try:
        tz = ZoneInfo(args.timezone)
    except (KeyError, ValueError, ZoneInfoNotFoundError):
        tz = ZoneInfo("Asia/Tashkent")

    now = datetime.now(tz)
    weekday_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"][now.weekday()]
    formatted = now.strftime(f"%Y-%m-%d, %H:%M:%S ({weekday_uz})")
    return ToolResult(
        success=True,
        output=f"Hozirgi vaqt ({args.timezone}): {formatted}",
    )
