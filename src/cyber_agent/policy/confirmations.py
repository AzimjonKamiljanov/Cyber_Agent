"""SQLite-backed confirmation store with single-use tokens, 60s TTL, and args binding."""

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from cyber_agent.config import get_settings

DEFAULT_EXPIRY_SECONDS = 60.0


def compute_args_hash(args: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of normalized tool arguments."""
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConfirmationStore:
    """Manages one-time confirmation tokens bound to actions and argument hashes."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            settings = get_settings()
            db_dir = settings.cyber_data_dir / "policy"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "confirmations.sqlite3"
        else:
            self.db_path = db_path
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS confirmations (
                    action_id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    args_hash TEXT NOT NULL,
                    args_json TEXT NOT NULL DEFAULT '{}',
                    token_hash TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            # Ensure column args_json exists if upgrading from earlier version
            try:
                conn.execute("ALTER TABLE confirmations ADD COLUMN args_json TEXT NOT NULL DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def create_confirmation(
        self,
        tool_name: str,
        args: dict[str, Any],
        expiry_seconds: float = DEFAULT_EXPIRY_SECONDS,
    ) -> tuple[str, str]:
        """Create a pending confirmation and return (action_id, plaintext_token)."""
        action_id = f"act_{secrets.token_hex(8)}"
        raw_token = secrets.token_hex(16)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        args_hash = compute_args_hash(args)
        args_json = json.dumps(args, sort_keys=True)

        now = time.time()
        expires_at = now + expiry_seconds

        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO confirmations (action_id, tool_name, args_hash, args_json, token_hash, created_at, expires_at, consumed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (action_id, tool_name, args_hash, args_json, token_hash, now, expires_at),
            )
            conn.commit()

        return action_id, raw_token

    def get_confirmation(self, action_id: str) -> dict[str, Any] | None:
        """Fetch confirmation record by action_id."""
        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                "SELECT action_id, tool_name, args_json, consumed, expires_at FROM confirmations WHERE action_id = ?",
                (action_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "action_id": row["action_id"],
                "tool_name": row["tool_name"],
                "args": json.loads(row["args_json"]),
                "consumed": bool(row["consumed"]),
                "expires_at": float(row["expires_at"]),
            }

    def invalidate_confirmation(self, action_id: str) -> bool:
        """Invalidate a specific pending confirmation."""
        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE confirmations SET consumed = 1 WHERE action_id = ? AND consumed = 0",
                (action_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def validate_and_consume(
        self,
        action_id: str,
        token: str,
        args: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate token and arguments, and mark confirmation as consumed (single-use)."""
        now = time.time()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expected_args_hash = compute_args_hash(args)

        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM confirmations WHERE action_id = ?",
                (action_id,),
            )
            row = cur.fetchone()

            if not row:
                return False, "Action ID not found"

            if row["consumed"] != 0:
                return False, "Confirmation token already consumed (single-use)"

            if now > row["expires_at"]:
                return False, "Confirmation token expired (60s limit)"

            if row["token_hash"] != token_hash:
                return False, "Invalid confirmation token"

            if row["args_hash"] != expected_args_hash:
                return False, "Action arguments mismatch (tampering detected)"

            # Atomically mark as consumed
            conn.execute(
                "UPDATE confirmations SET consumed = 1 WHERE action_id = ?",
                (action_id,),
            )
            conn.commit()

        return True, "Confirmation validated and consumed successfully"

    def invalidate_all(self) -> int:
        """Invalidate all unconsumed confirmations (called by kill switch)."""
        with self._lock, self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE confirmations SET consumed = 1 WHERE consumed = 0"
            )
            count = cur.rowcount
            conn.commit()
            return count


_global_confirm_store: ConfirmationStore | None = None


def get_confirmation_store() -> ConfirmationStore:
    global _global_confirm_store
    if _global_confirm_store is None:
        _global_confirm_store = ConfirmationStore()
    return _global_confirm_store
