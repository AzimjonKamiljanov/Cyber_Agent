"""Append-only, SHA-256 hash-chained JSONL audit logger with rotation."""

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cyber_agent.audit.redaction import redact_data
from cyber_agent.config import get_settings

GENESIS_HASH = "0" * 64
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class AuditLogger:
    """Hash-chained append-only audit logger."""

    def __init__(self, log_path: Path | None = None) -> None:
        if log_path is None:
            settings = get_settings()
            log_dir = settings.cyber_data_dir / "audit"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = log_dir / "audit.jsonl"
        else:
            self.log_file = log_path
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._last_hash = self._read_tail_hash()

    def _read_tail_hash(self) -> str:
        """Read the hash of the last entry in the existing log file, or return genesis hash."""
        if not self.log_file.exists() or self.log_file.stat().st_size == 0:
            return GENESIS_HASH

        last_line = ""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        last_line = line_str
            if last_line:
                data = json.loads(last_line)
                return str(data.get("hash", GENESIS_HASH))
        except (OSError, json.JSONDecodeError):
            pass
        return GENESIS_HASH

    def _rotate_if_needed(self) -> None:
        if self.log_file.exists() and self.log_file.stat().st_size >= MAX_LOG_SIZE_BYTES:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            rotated = self.log_file.with_name(f"audit_{timestamp}.jsonl")
            self.log_file.rename(rotated)
            # Reset hash chain on rotation
            self._last_hash = GENESIS_HASH

    def log_event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Record a structured event into the audit log."""
        with self._lock:
            self._rotate_if_needed()

            timestamp = datetime.now(UTC).isoformat()
            safe_data = redact_data(data)

            payload = {
                "timestamp": timestamp,
                "event_type": event_type,
                "data": safe_data,
                "prev_hash": self._last_hash,
            }

            canonical_repr = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            curr_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

            payload["hash"] = curr_hash

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, separators=(",", ":")) + "\n")

            self._last_hash = curr_hash
            return payload


def verify_chain(log_file: Path) -> tuple[bool, str]:
    """Verify cryptographic integrity of an audit log file."""
    if not log_file.exists():
        return True, "File does not exist (empty log is valid)"

    prev_hash = GENESIS_HASH
    line_num = 0

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, f"Invalid JSON on line {line_num}"

            recorded_prev = entry.get("prev_hash")
            recorded_curr = entry.get("hash")

            if recorded_prev != prev_hash:
                return False, f"Broken chain link on line {line_num}: prev_hash mismatch"

            recomputed_payload = {
                "timestamp": entry.get("timestamp"),
                "event_type": entry.get("event_type"),
                "data": entry.get("data"),
                "prev_hash": recorded_prev,
            }
            canonical_repr = json.dumps(recomputed_payload, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

            if expected_hash != recorded_curr:
                return False, f"Tampered hash on line {line_num}"

            prev_hash = recorded_curr

    return True, f"Verified {line_num} entries successfully"


_default_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger
