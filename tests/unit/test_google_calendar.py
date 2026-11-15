"""Unit tests for Google Calendar integration and policy guards (Stage S5)."""

import pytest

from cyber_agent.integrations.google_calendar import CalendarEvent, GoogleCalendarClient
from cyber_agent.policy.taint import SessionTaintTracker
from cyber_agent.tools.calendar_tools import (
    handle_create_calendar_event,
    handle_get_calendar_events,
)
from cyber_agent.tools.schemas import CreateCalendarEventArgs, GetCalendarEventsArgs


def test_calendar_write_guard_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure calendar event creation is blocked by default."""
    monkeypatch.delenv("CYBER_CALENDAR_WRITE", raising=False)
    client = GoogleCalendarClient()
    assert client.is_write_enabled() is False

    ok, msg = client.create_event("New meeting", "2026-11-16T10:00:00", "2026-11-16T11:00:00")
    assert ok is False
    assert "CYBER_CALENDAR_WRITE=false" in msg


def test_calendar_write_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure calendar creation succeeds when explicitly enabled."""
    monkeypatch.setenv("CYBER_CALENDAR_WRITE", "true")
    client = GoogleCalendarClient()
    client._mock_events = []
    assert client.is_write_enabled() is True

    ok, msg = client.create_event("Sprint Planning", "2026-11-16T10:00:00", "2026-11-16T11:00:00")
    assert ok is True
    assert "muvaffaqiyatli qo'shildi" in msg
    assert len(client._mock_events) == 1


@pytest.mark.asyncio
async def test_calendar_event_descriptions_taint_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify external event descriptions taint the session."""
    taint = SessionTaintTracker()
    monkeypatch.setattr("cyber_agent.integrations.google_calendar.get_taint_tracker", lambda: taint)

    client = GoogleCalendarClient()
    client._mock_events = [
        CalendarEvent(
            id="ev-101",
            title="Design Review",
            start_time="2026-11-17T14:00:00",
            end_time="2026-11-17T15:00:00",
            description="Discuss Figma layouts and architecture",
        )
    ]
    monkeypatch.setattr("cyber_agent.tools.calendar_tools.get_calendar_client", lambda: client)

    assert taint.is_tainted() is False
    res = await handle_get_calendar_events(GetCalendarEventsArgs())
    assert res.success is True
    assert "Design Review" in res.output
    # Description exists -> session tainted
    assert taint.is_tainted() is True


@pytest.mark.asyncio
async def test_calendar_create_tool_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test create calendar event tool handler."""
    monkeypatch.setenv("CYBER_CALENDAR_WRITE", "true")
    client = GoogleCalendarClient()
    client._mock_events = []
    monkeypatch.setattr("cyber_agent.tools.calendar_tools.get_calendar_client", lambda: client)

    res = await handle_create_calendar_event(
        CreateCalendarEventArgs(
            title="Qo'lda test",
            start_time="2026-11-18T10:00:00",
            end_time="2026-11-18T11:00:00",
        )
    )
    assert res.success is True
    assert "muvaffaqiyatli qo'shildi" in res.output
