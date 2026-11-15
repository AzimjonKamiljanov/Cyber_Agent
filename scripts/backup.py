"""Backup & Restore Utility for Cyber Agent.

Creates timestamped tarballs of data/ and config/ directories.
Security invariant: strictly excludes .env, secrets, tokens, and unix sockets.
Protects against archive path traversal during restoration.
"""

import argparse
import logging
import tarfile
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_NAMES = {
    ".env",
    ".env.example",
    "token.json",
    "credentials.json",
}

EXCLUDED_SUFFIXES = {
    ".sock",
    ".key",
    ".pem",
}


def should_exclude(path: Path) -> bool:
    name_lower = path.name.lower()
    if name_lower in EXCLUDED_NAMES or name_lower.startswith(".env"):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return bool("secret" in name_lower or "token" in name_lower)


def create_backup(
    project_root: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    root = project_root or PROJECT_ROOT
    dest_dir = output_dir or (root / "data" / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive_path = dest_dir / f"cyber_backup_{timestamp}.tar.gz"

    dirs_to_backup = [root / "data", root / "config"]

    with tarfile.open(archive_path, "w:gz") as tar:
        for d in dirs_to_backup:
            if not d.exists():
                continue
            for item in d.rglob("*"):
                # Exclude backup files themselves to avoid recursion
                if dest_dir in item.parents or item == dest_dir:
                    continue
                if should_exclude(item):
                    continue
                if item.is_file():
                    arcname = item.relative_to(root)
                    tar.add(item, arcname=str(arcname))

    logger.info("Backup archive created: %s", archive_path)
    return archive_path


def restore_backup(
    archive_path: Path,
    target_root: Path | None = None,
) -> bool:
    root = target_root or PROJECT_ROOT
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            # Security: Prevent Zip Slip / tar path traversal
            resolved_target = (root / member.name).resolve()
            try:
                resolved_target.relative_to(root.resolve())
            except ValueError as e:
                raise ValueError(f"Malicious archive member '{member.name}' escapes restore target") from e

            # Extract safely
            tar.extract(member, path=root, filter="data")

    logger.info("Restored backup '%s' to '%s'", archive_path, root)
    return True


def list_backups(output_dir: Path | None = None) -> list[Path]:
    dest_dir = output_dir or (PROJECT_ROOT / "data" / "backups")
    if not dest_dir.exists():
        return []
    return sorted(dest_dir.glob("cyber_backup_*.tar.gz"), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber Agent Backup & Restore Utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup", action="store_true", help="Create a new backup tarball")
    group.add_argument("--restore", type=Path, help="Path to backup tarball to restore")
    group.add_argument("--list", action="store_true", help="List existing backups")

    parser.add_argument("--target", type=Path, default=None, help="Target restore directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.backup:
        out = create_backup()
        print(f"Created: {out}")
    elif args.restore:
        restore_backup(args.restore, target_root=args.target)
        print(f"Restored: {args.restore}")
    elif args.list:
        backups = list_backups()
        if not backups:
            print("No backups found.")
        for b in backups:
            print(f"- {b.name} ({b.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
