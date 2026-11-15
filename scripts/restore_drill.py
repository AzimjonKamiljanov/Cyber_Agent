#!/usr/bin/env python3
"""Disaster Recovery Backup & Restore Drill for Cyber Agent (Stage S6).

Performs an end-to-end drill:
1. Populates a temporary test environment with databases and configurations.
2. Generates an encrypted/compressed backup archive.
3. Wipes the test data directory.
4. Restores from the archive.
5. Verifies data integrity and prints drill evidence.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.backup import create_backup, restore_backup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("restore_drill")


def run_drill() -> bool:
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_root = Path(tmp_dir_str)
        data_dir = tmp_root / "data"
        config_dir = tmp_root / "config"
        backups_dir = tmp_root / "backups"

        data_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)

        # 1. Create test SQLite database
        test_db = data_dir / "memory.sqlite3"
        with sqlite3.connect(test_db) as conn:
            conn.execute("CREATE TABLE test_data (id INT PRIMARY KEY, val TEXT);")
            conn.execute("INSERT INTO test_data VALUES (1, 'Azimjonning xotirasi');")
            conn.commit()

        # 2. Create test config file
        test_cfg = config_dir / "test_settings.toml"
        test_cfg.write_text("[test]\nenabled = true\n", encoding="utf-8")

        # 3. Create test audit file
        test_audit = data_dir / "audit.jsonl"
        test_audit.write_text('{"event": "DRILL_START", "hash": "abc"}\n', encoding="utf-8")

        logger.info("==> [1/4] Test environment populated successfully.")

        # 4. Create Backup
        archive_path = create_backup(project_root=tmp_root, output_dir=backups_dir)
        assert archive_path.exists(), "Backup archive creation failed"
        logger.info("==> [2/4] Backup created: %s (%d bytes)", archive_path.name, archive_path.stat().st_size)

        # 5. Wipe Data Directory
        test_db.unlink()
        test_audit.unlink()
        test_cfg.unlink()
        assert not test_db.exists()
        logger.info("==> [3/4] Simulated disaster: data and config directories wiped clean.")

        # 6. Restore from Backup
        restore_backup(archive_path, target_root=tmp_root)
        logger.info("==> [4/4] Restore completed. Verifying restored data integrity...")

        assert test_db.exists(), "Restored SQLite database missing!"
        assert test_cfg.exists(), "Restored config missing!"
        assert test_audit.exists(), "Restored audit log missing!"

        with sqlite3.connect(test_db) as conn:
            cur = conn.execute("SELECT val FROM test_data WHERE id = 1;")
            row = cur.fetchone()
            assert row is not None and row[0] == "Azimjonning xotirasi", "Database content mismatch!"

        assert "enabled = true" in test_cfg.read_text(encoding="utf-8")
        assert "DRILL_START" in test_audit.read_text(encoding="utf-8")

        print("=" * 65)
        print("BACKUP & RESTORE DRILL: 100% SUCCESS")
        print("All data tables, audit logs, and configurations restored intact.")
        print("=" * 65)
        return True


if __name__ == "__main__":
    success = run_drill()
    sys.exit(0 if success else 1)
