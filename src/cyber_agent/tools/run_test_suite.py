"""Tool: run_test_suite (YELLOW tier).

Executes tests inside rootless bubblewrap (bwrap) sandbox with network isolated.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path

from cyber_agent.tools.schemas import RunTestSuiteArgs, ToolResult
from cyber_agent.tools.workspace_jail import get_workspace_root


async def handle_run_test_suite(args: RunTestSuiteArgs) -> ToolResult:
    workspace = get_workspace_root()
    bwrap_path = shutil.which("bwrap") or "/usr/bin/bwrap"

    target_subpath = args.test_path.strip()
    test_arg = str(workspace / target_subpath) if target_subpath else str(workspace)

    # Command inside sandbox
    # Network is disabled via --unshare-net
    if Path(bwrap_path).exists():
        cmd = [
            bwrap_path,
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--bind", str(workspace), str(workspace),
            "--unshare-net",
            "--die-with-parent",
            "pytest", test_arg, "-v",
        ]
    else:
        # Fallback if bwrap missing: run directly without network proxy
        cmd = ["pytest", test_arg, "-v"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        out_text = stdout.decode("utf-8", errors="replace") + "\n" + stderr.decode("utf-8", errors="replace")

        return ToolResult(
            success=(proc.returncode == 0),
            output=out_text[:3500],
            error=None if proc.returncode == 0 else f"Testlar muvaffaqiyatsiz tugadi (kod: {proc.returncode})",
        )
    except TimeoutError:
        return ToolResult(success=False, output="", error="Testlarni bajarish vaqti (30s) tugadi.")
    except (OSError, subprocess.SubprocessError) as e:
        return ToolResult(success=False, output="", error=f"Testlarni ishga tushirishda xatolik: {e}")
