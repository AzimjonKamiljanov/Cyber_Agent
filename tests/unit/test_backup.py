"""Unit tests for backup & restore utility."""

import tarfile
from pathlib import Path

from scripts.backup import create_backup, restore_backup, should_exclude


def test_should_exclude_rules() -> None:
    assert should_exclude(Path(".env")) is True
    assert should_exclude(Path(".env.local")) is True
    assert should_exclude(Path("credentials.json")) is True
    assert should_exclude(Path("server.sock")) is True
    assert should_exclude(Path("private.key")) is True
    assert should_exclude(Path("token.json")) is True
    assert should_exclude(Path("data.json")) is False
    assert should_exclude(Path("config.toml")) is False


def test_backup_and_restore_cycle(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    data_dir = project_root / "data"
    config_dir = project_root / "config"
    backups_dir = project_root / "backups"

    data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    # Normal files
    (data_dir / "audit.jsonl").write_text('{"event": "test"}\n', encoding="utf-8")
    (config_dir / "settings.toml").write_text('[app]\nname = "cyber"\n', encoding="utf-8")

    # Sensitive files that MUST be excluded
    (project_root / ".env").write_text("SECRET_KEY=12345\n", encoding="utf-8")
    (data_dir / ".env.local").write_text("SECRET=abc\n", encoding="utf-8")
    (data_dir / "test.sock").write_text("", encoding="utf-8")

    # 1. Create backup
    archive = create_backup(project_root=project_root, output_dir=backups_dir)
    assert archive.exists()
    assert archive.stat().st_size > 0

    # 2. Inspect tar members
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "data/audit.jsonl" in names
        assert "config/settings.toml" in names
        # Invariant: NEVER include secrets or sockets
        for n in names:
            assert ".env" not in n
            assert not n.endswith(".sock")
            assert not n.endswith(".key")

    # 3. Restore to a clean target directory
    restore_target = tmp_path / "restored"
    restore_target.mkdir()

    success = restore_backup(archive, target_root=restore_target)
    assert success is True
    assert (restore_target / "data" / "audit.jsonl").exists()
    assert (restore_target / "config" / "settings.toml").exists()
    assert (restore_target / "data" / "audit.jsonl").read_text() == '{"event": "test"}\n'
