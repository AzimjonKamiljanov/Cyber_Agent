"""Unit tests for Morning Brief generation (Stage S5)."""

from pathlib import Path

import pytest

from cyber_agent.memory.morning_brief import fetch_weather_tashkent, generate_morning_brief
from cyber_agent.memory.reminders import ReminderScheduler
from cyber_agent.tools.morning_brief import handle_get_morning_brief
from cyber_agent.tools.schemas import GetMorningBriefArgs


@pytest.mark.asyncio
async def test_weather_fetch_fallback() -> None:
    """Ensure weather fetch returns a coherent string even if offline."""
    weather = await fetch_weather_tashkent()
    assert isinstance(weather, str)
    assert "Toshkentda" in weather


@pytest.mark.asyncio
async def test_morning_brief_composition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify morning brief contains greeting, weather, and reminders."""
    db_file = tmp_path / "mb_reminders.sqlite3"
    sched = ReminderScheduler(db_path=db_file)
    sched.add_reminder("Muhim suhbat", "10 daqiqa")
    monkeypatch.setattr("cyber_agent.memory.morning_brief.get_reminder_scheduler", lambda: sched)

    brief = await generate_morning_brief(user_name="Azimjon")
    assert "Xayrli tong, Azimjon!" in brief["spoken_text"]
    assert "Toshkentda" in brief["spoken_text"]
    assert "Muhim suhbat" in brief["spoken_text"]

    # Tool handler
    res = await handle_get_morning_brief(GetMorningBriefArgs())
    assert res.success is True
    assert "Xayrli tong" in res.output
