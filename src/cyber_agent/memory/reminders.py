"""Persistent Reminders Scheduler in Asia/Tashkent timezone (Stage S5).

Handles:
- Storage and restart persistence in SQLite `reminders` table.
- Asia/Tashkent timezone conversion.
- Dual delivery: desktop notification via notify-send + PWA event dispatch.
- Cancellation and listing.
"""

from __future__ import annotations

import logging
import re
import shutil
import sqlite3
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from cyber_agent.memory.database import get_db_connection, init_database

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


@dataclass
class ReminderItem:
    id: str
    title: str
    remind_at: str
    channel: str
    status: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "remind_at": self.remind_at,
            "channel": self.channel,
            "status": self.status,
            "created_at": self.created_at,
        }


def parse_remind_time(input_str: str) -> datetime:
    """Parse relative ("10 daqiqa", "1 soat") or ISO-8601 datetime in Asia/Tashkent."""
    now = datetime.now(TASHKENT_TZ)
    text = input_str.strip().lower()

    # Relative minutes
    m_min = re.search(r"(\d+)\s*(?:daqiqa|min|daq)", text)
    if m_min:
        return now + timedelta(minutes=int(m_min.group(1)))

    # Relative hours
    m_hour = re.search(r"(\d+)\s*(?:soat|hour|soatdan)", text)
    if m_hour:
        return now + timedelta(hours=int(m_hour.group(1)))

    # Relative days
    m_day = re.search(r"(\d+)\s*(?:kun|day)", text)
    if m_day:
        return now + timedelta(days=int(m_day.group(1)))

    # ISO or standard datetime
    try:
        dt = datetime.fromisoformat(input_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=TASHKENT_TZ)
        return dt.astimezone(TASHKENT_TZ)
    except ValueError:
        pass

    # Fallback default: 15 minutes from now
    return now + timedelta(minutes=15)


class ReminderScheduler:
    """Manages persistent reminders and asynchronous delivery."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path
        init_database(self.db_path)
        self._notify_bin = shutil.which("notify-send") or "/usr/bin/notify-send"

    def _get_connection(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def add_reminder(
        self,
        title: str,
        remind_at_str: str,
        channel: str = "all",
    ) -> tuple[bool, str, ReminderItem | None]:
        """Schedule a persistent reminder."""
        clean_title = title.strip()
        if not clean_title:
            return False, "Eslatma sarlavhasi bo'sh bo'lishi mumkin emas.", None

        target_dt = parse_remind_time(remind_at_str)
        target_iso = target_dt.isoformat()
        now_iso = datetime.now(TASHKENT_TZ).isoformat()
        rem_id = str(uuid.uuid4())[:8]

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO reminders (id, title, remind_at, channel, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?);
                    """,
                    (rem_id, clean_title, target_iso, channel, now_iso),
                )
            item = ReminderItem(
                id=rem_id,
                title=clean_title,
                remind_at=target_iso,
                channel=channel,
                status="pending",
                created_at=now_iso,
            )
            time_display = target_dt.strftime("%Y-%m-%d %H:%M:%S")
            return (
                True,
                f"Eslatma o'rnatildi [ID: {rem_id}]: '{clean_title}' ({time_display})",
                item,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to insert reminder: %s", e)
            return False, f"Eslatma yaratishda xatolik: {e}", None

    def list_reminders(self, include_completed: bool = False) -> list[ReminderItem]:
        """List active/pending reminders."""
        conn = self._get_connection()
        query = "SELECT id, title, remind_at, channel, status, created_at FROM reminders"
        if not include_completed:
            query += " WHERE status = 'pending'"
        query += " ORDER BY remind_at ASC;"

        cursor = conn.execute(query)
        return [ReminderItem(**dict(row)) for row in cursor.fetchall()]

    def cancel_reminder(self, reminder_id: str) -> tuple[bool, str]:
        """Cancel an existing reminder by ID or title substring."""
        target = reminder_id.strip()
        conn = self._get_connection()
        with conn:
            cursor = conn.execute(
                "UPDATE reminders SET status = 'cancelled' WHERE id = ? AND status = 'pending';",
                (target,),
            )
            if cursor.rowcount == 0:
                cursor = conn.execute(
                    "UPDATE reminders SET status = 'cancelled' WHERE title LIKE ? AND status = 'pending';",
                    (f"%{target}%",),
                )

        if cursor.rowcount > 0:
            return True, f"'{target}' eslatmasi muvaffaqiyatli bekor qilindi."
        return False, f"'{target}' nomli faol eslatma topilmadi."

    def deliver_reminder(self, reminder: ReminderItem) -> bool:
        """Trigger notification delivery on desktop and update status."""
        logger.info("Delivering reminder %s: '%s'", reminder.id, reminder.title)

        # 1. Desktop notification via notify-send
        if Path(self._notify_bin).exists() and reminder.channel in ("all", "desktop"):
            try:
                subprocess.run(
                    [
                        self._notify_bin,
                        "-u", "normal",
                        "-a", "Cyber Agent",
                        "🔔 Cyber Agent Eslatma",
                        reminder.title,
                    ],
                    timeout=3.0,
                    check=False,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Desktop notification failed: %s", e)

        # 2. Mark reminder as completed
        conn = self._get_connection()
        with conn:
            conn.execute(
                "UPDATE reminders SET status = 'completed' WHERE id = ?;",
                (reminder.id,),
            )
        return True

    def check_due_reminders(self) -> list[ReminderItem]:
        """Check and return all reminders that are due for delivery."""
        now_iso = datetime.now(TASHKENT_TZ).isoformat()
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT id, title, remind_at, channel, status, created_at
            FROM reminders
            WHERE status = 'pending' AND remind_at <= ?
            ORDER BY remind_at ASC;
            """,
            (now_iso,),
        )
        due_items = [ReminderItem(**dict(row)) for row in cursor.fetchall()]
        for item in due_items:
            self.deliver_reminder(item)
        return due_items


_global_reminder_scheduler: ReminderScheduler | None = None


def get_reminder_scheduler() -> ReminderScheduler:
    global _global_reminder_scheduler
    if _global_reminder_scheduler is None:
        _global_reminder_scheduler = ReminderScheduler()
    return _global_reminder_scheduler
