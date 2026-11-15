"""Memory repository managing CRUD and FTS5 search on SQLite."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cyber_agent.memory.database import get_db_connection, init_database
from cyber_agent.memory.filters import check_for_secrets

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    id: str
    text: str
    source: str
    consent: bool
    created_at: str
    updated_at: str
    expires_at: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "consent": self.consent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }


class MemoryRepository:
    """Provides storage, full-text retrieval, and deletion of user memory items."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path
        init_database(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def remember(
        self,
        text: str,
        source: str = "voice",
        consent: bool = True,
        expires_at: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Store a new memory item with consent and secret filtering."""
        clean_text = text.strip()
        if not clean_text:
            return False, "Saqlash uchun bo'sh matn berildi.", None

        # Invariant: Never store passwords, credentials, or bank secrets
        has_secret, secret_reason = check_for_secrets(clean_text)
        if has_secret:
            logger.warning("Memory storage REFUSED due to sensitive credentials detected.")
            return False, secret_reason, None

        item_id = str(uuid.uuid4())
        now_iso = datetime.now(UTC).isoformat()

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO memory_items (id, text, source, consent, created_at, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (item_id, clean_text, source, consent, now_iso, now_iso, expires_at),
                )
            logger.info("Saved memory item %s (length: %d chars)", item_id, len(clean_text))
            return True, f"'{clean_text}' muvaffaqiyatli eslab qolindi.", item_id
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to insert memory item: %s", e)
            return False, f"Xotirada saqlashda xatolik yuz berdi: {e}", None

    def recall(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Search memory using FTS5 full-text search with LIKE fallback."""
        clean_query = query.strip()
        if not clean_query:
            return []

        conn = self._get_connection()
        results: list[MemoryItem] = []

        # 1. Try FTS5 MATCH query
        try:
            # Escape double quotes for FTS5 syntax
            safe_fts = clean_query.replace('"', '""')
            cursor = conn.execute(
                """
                SELECT m.id, m.text, m.source, m.consent, m.created_at, m.updated_at, m.expires_at
                FROM memory_items m
                JOIN memory_items_fts fts ON m.id = fts.id
                WHERE memory_items_fts MATCH ?
                ORDER BY rank
                LIMIT ?;
                """,
                (f'"{safe_fts}"', limit),
            )
            for row in cursor.fetchall():
                results.append(MemoryItem(**dict(row)))
        except sqlite3.OperationalError:
            # If FTS expression fails on unusual syntax, fallback to LIKE
            results = []

        # 2. Fallback to LIKE if FTS yielded no matches
        if not results:
            cursor = conn.execute(
                """
                SELECT id, text, source, consent, created_at, updated_at, expires_at
                FROM memory_items
                WHERE text LIKE ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (f"%{clean_query}%", limit),
            )
            for row in cursor.fetchall():
                results.append(MemoryItem(**dict(row)))

        return results

    def list_memories(self, limit: int = 20) -> list[MemoryItem]:
        """List recent memories ordered chronologically."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT id, text, source, consent, created_at, updated_at, expires_at
            FROM memory_items
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (limit,),
        )
        return [MemoryItem(**dict(row)) for row in cursor.fetchall()]

    def forget(self, identifier_or_substring: str) -> tuple[bool, str]:
        """Delete specific memory by ID or exact text match."""
        target = identifier_or_substring.strip()
        if not target:
            return False, "O'chirish uchun ma'lumot ko'rsatilmadi."

        conn = self._get_connection()
        with conn:
            # First try exact ID
            cursor = conn.execute("DELETE FROM memory_items WHERE id = ?;", (target,))
            deleted = cursor.rowcount

            # If not deleted by ID, try exact text or substring match
            if deleted == 0:
                cursor = conn.execute("DELETE FROM memory_items WHERE text LIKE ?;", (f"%{target}%",))
                deleted = cursor.rowcount

        if deleted > 0:
            logger.info("Deleted %d memory item(s) matching '%s'", deleted, target)
            return True, f"{deleted} ta xotira elementi muvaffaqiyatli o'chirildi."
        return False, f"'{target}' bo'yicha o'chirish uchun hech qanday xotira topilmadi."

    def wipe(self) -> tuple[bool, int]:
        """Wipe all user memory entries and rebuild FTS index."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM memory_items;")
            deleted = cursor.rowcount
            conn.execute("DELETE FROM memory_items_fts;")

        logger.warning("WIPED entire user memory (%d items deleted)", deleted)
        return True, deleted


_global_memory_repo: MemoryRepository | None = None


def get_memory_repository() -> MemoryRepository:
    global _global_memory_repo
    if _global_memory_repo is None:
        _global_memory_repo = MemoryRepository()
    return _global_memory_repo
