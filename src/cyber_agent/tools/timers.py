"""Tools: create_timer and list_timers (GREEN tier)."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from cyber_agent.tools.schemas import CreateTimerArgs, ListTimersArgs, ToolResult

# In-memory timer registry
_active_timers: list[dict[str, Any]] = []


async def _timer_worker(timer_id: int, duration_sec: int, label: str) -> None:
    await asyncio.sleep(duration_sec)
    for t in _active_timers:
        if t["id"] == timer_id:
            t["status"] = "Tugadi"
            break


async def handle_create_timer(args: CreateTimerArgs) -> ToolResult:
    timer_id = len(_active_timers) + 1
    label = args.label or f"Taymer #{timer_id}"
    created_at = datetime.now(UTC).strftime("%H:%M:%S")

    timer_entry = {
        "id": timer_id,
        "label": label,
        "seconds": args.seconds,
        "created_at": created_at,
        "status": "Faol",
        "expires_at": time.time() + args.seconds,
    }
    _active_timers.append(timer_entry)

    # Launch background sleep
    asyncio.create_task(_timer_worker(timer_id, args.seconds, label))

    minutes = args.seconds // 60
    secs = args.seconds % 60
    duration_str = f"{minutes} daqiqa " if minutes else ""
    duration_str += f"{secs} soniya"

    return ToolResult(
        success=True,
        output=f"'{label}' uchun {duration_str}lik taymer o'rnatildi (ID: #{timer_id}).",
    )


async def handle_list_timers(args: ListTimersArgs) -> ToolResult:
    if not _active_timers:
        return ToolResult(success=True, output="Hozirda faol taymerlar yo'q.")

    lines = ["Mavjud taymerlar:"]
    now = time.time()
    for t in _active_timers:
        remaining = max(0, int(t["expires_at"] - now))
        status = t["status"] if remaining == 0 else f"{remaining} soniya qoldi"
        lines.append(f"• [#{t['id']}] {t['label']}: {status}")

    return ToolResult(success=True, output="\n".join(lines))
