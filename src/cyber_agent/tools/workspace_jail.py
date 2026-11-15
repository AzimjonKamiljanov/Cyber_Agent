"""Workspace filesystem jail utilities for Cyber Agent.

Guarantees all file operations strictly remain within ~/cyber-workspace
and rejects symlink or hardlink path traversal attacks.
"""

from pathlib import Path

from cyber_agent.config import get_settings


def get_workspace_root() -> Path:
    settings = get_settings()
    root: Path = settings.cyber_workspace_dir.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_jail_path(relative_or_subpath: str | Path, must_exist: bool = False) -> Path:
    """Resolve and validate a path inside ~/cyber-workspace.

    Raises PermissionError if path attempts to escape the workspace root.
    """
    root = get_workspace_root()
    raw = Path(relative_or_subpath)

    # If an absolute path was passed, check if it resides within root
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (root / raw).resolve()

    # Invariant: Must be strictly inside root
    try:
        resolved.relative_to(root)
    except ValueError as e:
        raise PermissionError(f"Path escape blocked: '{relative_or_subpath}' escapes workspace jail.") from e

    # Check symlinks target
    if resolved.is_symlink():
        target = resolved.resolve()
        try:
            target.relative_to(root)
        except ValueError as e:
            raise PermissionError(f"Symlink escape blocked: '{relative_or_subpath}' points outside workspace.") from e

    # Prohibited files regardless of location
    name_lower = resolved.name.lower()
    if name_lower.startswith(".env") or name_lower in {"id_rsa", "id_ed25519", "authorized_keys"}:
        raise PermissionError(f"Access to sensitive file '{resolved.name}' is strictly blocked.")

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"File not found inside workspace: {relative_or_subpath}")

    return resolved
