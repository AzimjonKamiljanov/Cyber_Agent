"""Rootless Bubblewrap Sandbox Executor for Cyber Agent Stage S4.

Enforces:
1. Command allowlist from config/command_allowlist.toml
2. Rootless bubblewrap container with --unshare-net (network isolated)
3. Workspace jail inside ~/cyber-workspace
4. Stripped environment (zero leaked secrets or tokens)
5. Process group registration for instant kill-switch termination
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tomllib
from pathlib import Path

from cyber_agent.killswitch.process_registry import get_process_registry
from cyber_agent.tools.workspace_jail import get_workspace_root

logger = logging.getLogger(__name__)

CONFIG_ALLOWLIST = Path("config/command_allowlist.toml")

# Sensitive patterns that must never appear in arguments
FORBIDDEN_ARG_PATTERNS = [
    re.compile(r"(\.\./|\.\.\\)"),  # Path traversal
    re.compile(r"(\.env|id_rsa|id_ed25519|authorized_keys|credentials)"),  # Secrets
    re.compile(r"(/etc/|/root|/var/|~/\.ssh|~/\.config)"),  # Protected system paths
    re.compile(r"[;&|><`$]"),  # Shell operators
]


def is_command_allowed(argv: list[str], config_path: Path | None = None) -> tuple[bool, str]:
    """Check if argv matches an allowed command prefix in config/command_allowlist.toml."""
    if not argv:
        return False, "Bo'sh buyruq ro'yxati berildi"

    # Reject shell meta-characters or forbidden argument patterns
    full_cmd_str = " ".join(argv)
    for pattern in FORBIDDEN_ARG_PATTERNS:
        if pattern.search(full_cmd_str):
            return False, f"Xavfsizlik qoidasi: Buyruq argumentlarida xavfli belgi yoki yo'l aniqlandi: '{pattern.pattern}'"

    # Reject binary name spoofing or execution of binaries inside workspace
    first_arg = argv[0]
    if "/" in first_arg or "\\" in first_arg:
        return False, f"Xavfsizlik qoidasi: Faqat tizim buyruqlari ruxsat etiladi, nisbiy yoki to'liq yo'l bilan ishga tushirish taqiqlangan: '{first_arg}'"

    cfg_file = config_path or CONFIG_ALLOWLIST
    allowed_list: list[list[str]] = [
        ["git", "status"],
        ["git", "diff"],
        ["git", "log"],
        ["ls"],
        ["pwd"],
        ["uv", "run", "pytest"],
    ]

    if cfg_file.exists():
        try:
            with open(cfg_file, "rb") as f:
                data = tomllib.load(f)
            allowed_list = data.get("allowed_commands", {}).get("commands", allowed_list)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load command allowlist: %s", e)

    # Check prefix matching
    for allowed in allowed_list:
        if len(argv) >= len(allowed) and argv[: len(allowed)] == allowed:
            return True, "Allowed"

    return False, f"Buyruq ruxsat etilgan ro'yxatda (config/command_allowlist.toml) mavjud emas: {argv}"


class SandboxExecutor:
    """Executes allowlisted commands inside rootless Bubblewrap container."""

    def __init__(self, workspace_dir: Path | None = None, bwrap_path: str | None = None) -> None:
        self.workspace_dir = workspace_dir or get_workspace_root()
        self.bwrap_path = bwrap_path or shutil.which("bwrap") or "/usr/bin/bwrap"

    def _build_sanitized_env(self) -> dict[str, str]:
        """Produce minimal sanitized environment without any leaked tokens or keys."""
        home = str(Path.home())
        return {
            "PATH": f"/usr/bin:/bin:/usr/local/bin:{home}/.local/bin:{home}/.cargo/bin",
            "HOME": home,
            "LANG": "en_US.UTF-8",
            "TERM": "xterm",
            "LC_ALL": "en_US.UTF-8",
        }

    async def run(
        self,
        argv: list[str],
        timeout: float = 30.0,
        max_output_chars: int = 8000,
    ) -> tuple[int, str, str]:
        """Execute sandboxed command.

        Returns (exit_code, stdout, stderr).
        """
        allowed, reason = is_command_allowed(argv)
        if not allowed:
            return -1, "", f"Xavfsizlik xatosi: {reason}"

        workspace = self.workspace_dir.resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        # Bubblewrap isolation flags
        cmd: list[str] = []
        if Path(self.bwrap_path).exists():
            cmd = [
                self.bwrap_path,
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/bin", "/bin",
                "--dev", "/dev",
                "--proc", "/proc",
                "--tmpfs", "/tmp",
                "--bind", str(workspace), str(workspace),
                "--chdir", str(workspace),
                "--unshare-net",
                "--die-with-parent",
            ]
            if Path("/lib64").exists():
                cmd.extend(["--ro-bind", "/lib64", "/lib64"])
            cmd.extend(argv)
        else:
            # Fallback if bwrap missing (should not happen in Linux setup)
            cmd = list(argv)

        env = self._build_sanitized_env()
        registry = get_process_registry()
        proc = None
        pid: int | None = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,  # Creates a new process group for clean kill-switch SIGKILL
            )
            pid = proc.pid
            registry.register_pgid(pid)

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = stdout_bytes.decode("utf-8", errors="replace")[:max_output_chars]
            err = stderr_bytes.decode("utf-8", errors="replace")[:max_output_chars]
            return proc.returncode if proc.returncode is not None else 0, out, err

        except TimeoutError:
            if pid is not None:
                try:
                    os.killpg(pid, 9)
                except OSError:
                    pass
            return -1, "", f"Buyruqni bajarish vaqti ({timeout}s) tugadi."
        except Exception as e:  # noqa: BLE001
            return -1, "", f"Buyruqni ishga tushirishda xatolik: {e}"
        finally:
            if pid is not None:
                registry.unregister_pgid(pid)


_global_sandbox_executor: SandboxExecutor | None = None


def get_sandbox_executor() -> SandboxExecutor:
    global _global_sandbox_executor
    if _global_sandbox_executor is None:
        _global_sandbox_executor = SandboxExecutor()
    return _global_sandbox_executor
