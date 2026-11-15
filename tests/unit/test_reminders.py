"""Unit tests for persistent reminders scheduler in Asia/Tashkent (Stage S5)."""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from cyber_agent.memory.reminders import ReminderScheduler, parse_remind_time
from cyber_agent.tools.reminders import (
    handle_cancel_reminder,
    handle_create_reminder,
    handle_list_reminders,
)
from cyber_agent.tools.schemas import (
    CancelReminderArgs,
    CreateReminderArgs,
    ListRemindersArgs,
)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def test_parse_remind_time_relative_and_iso() -> None:
    """Test relative strings and ISO timestamp parsing."""
    now = datetime.now(TASHKENT_TZ)

    # 10 daqiqa
    dt_10m = parse_remind_time("10 daqiqa")
    assert abs((dt_10m - (now + timedelta(minutes=10))).total_seconds()) < 5

    # 2 soat
    dt_2h = parse_remind_time("2 soat")
    assert abs((dt_2h - (now + timedelta(hours=2))).total_seconds()) < 5

    # ISO string
    iso_input = "2026-11-20T14:30:00"
    dt_iso = parse_remind_time(iso_input)
    assert dt_iso.year == 2026 and dt_iso.month == 11 and dt_iso.day == 20
    assert dt_iso.hour == 14 and dt_iso.minute == 30
    assert dt_iso.tzinfo == TASHKENT_TZ


def test_reminder_scheduler_restart_persistence(tmp_path: Path) -> None:
    """Ensure reminders survive scheduler / service restarts."""
    db_file = tmp_path / "reminders_persist.sqlite3"
    sched1 = ReminderScheduler(db_path=db_file)

    # Add reminder in session 1
    ok, _, rem = sched1.add_reminder(title="Noutbukni zaryadlash", remind_at_str="30 daqiqa")
    assert ok is True
    assert rem is not None

    # Simulate restart: create new scheduler instance on same DB file
    sched2 = ReminderScheduler(db_path=db_file)
    active = sched2.list_reminders()
    assert len(active) == 1
    assert active[0].id == rem.id
    assert active[0].title == "Noutbukni zaryadlash"

    # Cancel reminder in session 2
    cancel_ok, _ = sched2.cancel_reminder(rem.id)
    assert cancel_ok is True
    assert len(sched2.list_reminders()) == 0


def test_reminder_due_delivery(tmp_path: Path) -> None:
    """Test due reminder checking and completion status."""
    db_file = tmp_path / "reminders_due.sqlite3"
    sched = ReminderScheduler(db_path=db_file)

    # Add reminder scheduled in the past
    past_iso = (datetime.now(TASHKENT_TZ) - timedelta(minutes=5)).isoformat()
    conn = sched._get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO reminders (id, title, remind_at, channel, status, created_at)
            VALUES ('due-01', ?, ?, 'desktop', 'pending', ?);
            """,
            ("O'tgan eslatma", past_iso, past_iso),
        )

    # Check due reminders
    due = sched.check_due_reminders()
    assert len(due) == 1
    assert due[0].id == "due-01"

    # Now no pending reminders left
    assert len(sched.list_reminders()) == 0


@pytest.mark.asyncio
async def test_reminder_tool_handlers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool handlers for reminders."""
    db_file = tmp_path / "reminders_tools.sqlite3"
    sched = ReminderScheduler(db_path=db_file)
    monkeypatch.setattr("cyber_agent.tools.reminders.get_reminder_scheduler", lambda: sched)

    # Create reminder
    res_create = await handle_create_reminder(
        CreateReminderArgs(title="Dars boshlanishi", remind_at="15 daqiqa")
    )
    assert res_create.success is True
    assert "Eslatma o'rnatildi" in res_create.output

    # List reminders
    res_list = await handle_list_reminders(ListRemindersArgs())
    assert res_list.success is True
    assert "Dars boshlanishi" in res_list.output

    # Cancel reminder
    res_cancel = await handle_cancel_reminder(CancelReminderArgs(reminder_id="Dars boshlanishi"))
    assert res_cancel.success is True
    assert "bekor qilindi" in res_cancel.output
