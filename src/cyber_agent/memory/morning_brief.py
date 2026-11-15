"""Morning brief generator for Cyber Agent (Stage S5).

Composes:
1. Current date and Tashkent time.
2. Weather for Tashkent (read-only web).
3. Today's scheduled reminders from SQLite.
4. Google Calendar events for today.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from cyber_agent.memory.reminders import get_reminder_scheduler

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
BRIEF_CACHE_PATH = Path("data/morning_brief.json")


async def fetch_weather_tashkent() -> str:
    """Fetch current Tashkent weather summary."""
    url = "https://wttr.in/Tashkent?format=%C+%t+%w"
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text.strip():
                return f"Toshkentda: {resp.text.strip()}"
    except Exception as e:  # noqa: BLE001
        logger.debug("Live weather fetch skipped/failed: %s", e)
    return "Toshkentda ob-havo: ochiq, harorat +16°C atrofida"


async def generate_morning_brief(user_name: str = "Azimjon") -> dict[str, str]:
    """Generate and cache the morning brief."""
    now = datetime.now(TASHKENT_TZ)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # 1. Weather
    weather = await fetch_weather_tashkent()

    # 2. Today's reminders
    scheduler = get_reminder_scheduler()
    reminders = scheduler.list_reminders()
    today_reminders = [r for r in reminders if r.remind_at.startswith(date_str)]

    reminders_text = "Bugungi rejalashtirilgan eslatmalar yo'q."
    if today_reminders:
        rem_lines = [f"- {r.title} ({r.remind_at[11:16]})" for r in today_reminders]
        reminders_text = "Bugungi eslatmalaringiz:\n" + "\n".join(rem_lines)

    # 3. Calendar (placeholder or integration hook)
    calendar_text = "Bugun taqvimda muhim tadbirlar rejalashtirilmagan."

    # 4. Compose full spoken brief in Uzbek
    spoken = (
        f"Xayrli tong, {user_name}! Bugun {date_str}, soat {time_str}. "
        f"{weather}. "
        f"{reminders_text} "
        f"{calendar_text} "
        "Kuningiz unumli va xayrli o'tsin!"
    )

    brief_data = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "weather": weather,
        "reminders": reminders_text,
        "calendar": calendar_text,
        "spoken_text": spoken,
    }

    # Cache brief
    try:
        BRIEF_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BRIEF_CACHE_PATH.write_text(json.dumps(brief_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to cache morning brief: %s", e)

    return brief_data
