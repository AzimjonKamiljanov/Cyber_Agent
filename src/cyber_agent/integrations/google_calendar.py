"""Google Calendar integration for Cyber Agent (Stage S5).

Security Invariants:
1. READ-ONLY by default (https://www.googleapis.com/auth/calendar.readonly).
2. Refresh token stored securely with 0600 permissions, never committed to git.
3. Event descriptions are untrusted external data (taints session).
4. Calendar event creation disabled by default (CYBER_CALENDAR_WRITE=false).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from cyber_agent.policy.taint import get_taint_tracker

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
TOKEN_PATH = Path("data/calendar_token.json")
CREDENTIALS_PATH = Path.home() / ".config" / "cyber-agent" / "calendar_credentials.json"

SCOPES_READONLY = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES_WRITE = ["https://www.googleapis.com/auth/calendar.events"]


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str
    end_time: str
    description: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
        }


class GoogleCalendarClient:
    """Manages read-only and guarded-write access to Google Calendar API."""

    def __init__(self, token_path: Path | None = None) -> None:
        self.token_path = token_path or TOKEN_PATH
        # Mock events for offline/sandbox testing
        self._mock_events: list[CalendarEvent] | None = None

    def is_write_enabled(self) -> bool:
        """Check if CYBER_CALENDAR_WRITE toggle is enabled."""
        val = os.environ.get("CYBER_CALENDAR_WRITE", "false").lower()
        return val in ("true", "1", "yes")

    def get_events(self, days: int = 1, max_results: int = 10) -> tuple[bool, str, list[CalendarEvent]]:
        """Fetch upcoming calendar events.

        Security: Any non-empty event description marks session as TAINTED.
        """
        # Testing / Mock mode
        if self._mock_events is not None:
            events = self._mock_events[:max_results]
            for ev in events:
                if ev.description:
                    get_taint_tracker().mark_tainted(source=f"calendar_event:{ev.id}")
            return True, "Mock events retrieved", events

        # Live Google API mode
        if not self.token_path.exists():
            return False, "Google Calendar hisobi ulanmagan. Iltimos docs/setup-google.md bo'yicha ulaning.", []

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES_READONLY)  # type: ignore[no-untyped-call]
            service = build("calendar", "v3", credentials=creds)

            now_iso = datetime.now(TASHKENT_TZ).isoformat()
            time_max = (datetime.now(TASHKENT_TZ) + timedelta(days=days)).isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now_iso,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])
            parsed_events: list[CalendarEvent] = []

            for item in items:
                start = item.get("start", {}).get("dateTime", item.get("start", {}).get("date", ""))
                end = item.get("end", {}).get("dateTime", item.get("end", {}).get("date", ""))
                summary = item.get("summary", "Nomsiz tadbir")
                desc = item.get("description", "")

                # Invariant: External calendar descriptions taint the session
                if desc:
                    get_taint_tracker().mark_tainted(source=f"calendar_event:{item.get('id')}")

                parsed_events.append(
                    CalendarEvent(
                        id=item.get("id", ""),
                        title=summary,
                        start_time=start,
                        end_time=end,
                        description=desc,
                    )
                )

            return True, f"{len(parsed_events)} ta tadbir olindi", parsed_events

        except Exception as e:  # noqa: BLE001
            logger.error("Failed to fetch Google Calendar events: %s", e)
            return False, f"Taqvim ma'lumotlarini olishda xatolik: {e}", []

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> tuple[bool, str]:
        """Create a new calendar event.

        Strictly guarded behind CYBER_CALENDAR_WRITE=true.
        """
        if not self.is_write_enabled():
            return (
                False,
                ("Xavfsizlik qoidasi: Taqvimga yozish o'chirilgan (CYBER_CALENDAR_WRITE=false). "
                "Faqat o'qish rejimi faol."),
            )

        if self._mock_events is not None:
            new_ev = CalendarEvent(
                id=f"evt-{len(self._mock_events) + 1}",
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
            )
            self._mock_events.append(new_ev)
            return True, f"'{title}' tadbiri taqvimga muvaffaqiyatli qo'shildi (Mock)."

        # Live API write execution
        return False, "Google Calendar API tokeni yozish ruxsatiga ega emas yoki sozlanmagan."


_global_calendar_client: GoogleCalendarClient | None = None


def get_calendar_client() -> GoogleCalendarClient:
    global _global_calendar_client
    if _global_calendar_client is None:
        _global_calendar_client = GoogleCalendarClient()
    return _global_calendar_client
