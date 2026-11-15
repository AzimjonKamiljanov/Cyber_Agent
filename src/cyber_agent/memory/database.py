"""SQLite database connection and schema initialization for Second Brain (Stage S5)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/memory.sqlite3")


def get_db_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Create and configure a SQLite connection with WAL mode and foreign keys."""
    target_path = db_path or DEFAULT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_database(db_path: Path | None = None) -> None:
    """Initialize all MASTER_PLAN §11 tables and FTS5 full-text search index."""
    conn = get_db_connection(db_path)
    with conn:
        # 1. memory_items table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                consent BOOLEAN NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT
            );
            """
        )

        # 2. memory_items FTS5 index
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5(
                id UNINDEXED,
                text,
                tokenize='unicode61'
            );
            """
        )

        # Triggers to keep FTS index synchronized with memory_items
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memory_items_ai AFTER INSERT ON memory_items BEGIN
                INSERT INTO memory_items_fts(id, text) VALUES (new.id, new.text);
            END;
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memory_items_ad AFTER DELETE ON memory_items BEGIN
                DELETE FROM memory_items_fts WHERE id = old.id;
            END;
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memory_items_au AFTER UPDATE ON memory_items BEGIN
                DELETE FROM memory_items_fts WHERE id = old.id;
                INSERT INTO memory_items_fts(id, text) VALUES (new.id, new.text);
            END;
            """
        )

        # 3. reminders table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                channel TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        # 4. tasks table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # 5. tool_runs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_runs (
                id TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                args_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        # 6. confirmations table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS confirmations (
                id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed BOOLEAN NOT NULL DEFAULT 0
            );
            """
        )

        # 7. user_settings table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # 8. consent_records table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consent_records (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                granted BOOLEAN NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )
    logger.info("Database schema and FTS5 tables initialized successfully.")
