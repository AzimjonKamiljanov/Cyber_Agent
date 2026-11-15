"""Kill Switch Service: out-of-band daemon listening on a Unix domain socket.

Effects of STOP:
- Kill registered subprocess groups (SIGKILL).
- Invalidate all pending confirmation tokens.
- Cancel all background task queue items.
- Block tool execution until explicit RESUME.
- Audit every killswitch invocation.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from cyber_agent.audit.logger import get_audit_logger
from cyber_agent.brain.task_queue import get_task_queue
from cyber_agent.killswitch.process_registry import get_process_registry
from cyber_agent.policy.confirmations import get_confirmation_store

logger = logging.getLogger(__name__)

DEFAULT_SOCKET_PATH = Path.home() / ".cyber" / "killswitch.sock"


def get_socket_path() -> Path:
    env_path = os.environ.get("CYBER_KILLSWITCH_SOCK")
    if env_path:
        return Path(env_path)
    return DEFAULT_SOCKET_PATH


class KillSwitchService:
    def __init__(self, sock_path: Path | None = None) -> None:
        self.sock_path = sock_path or get_socket_path()
        self.is_stopped = False
        self._server: asyncio.Server | None = None
        self.audit_logger = get_audit_logger()
        self.process_registry = get_process_registry()
        self.confirmation_store = get_confirmation_store()
        self.task_queue = get_task_queue()

    async def start(self) -> None:
        self.sock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.sock_path.exists():
            self.sock_path.unlink()

        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.sock_path),
        )
        logger.info("Kill switch daemon listening on unix socket: %s", self.sock_path)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except OSError:
                pass
        logger.info("Kill switch daemon stopped.")

    async def trigger_stop(self) -> dict[str, Any]:
        """Execute complete emergency stop sequence."""
        t0 = time.monotonic()
        self.is_stopped = True

        # 1. Kill all child process groups
        groups_killed = self.process_registry.kill_all()

        # 2. Invalidate all pending confirmation tokens
        confirmations_invalidated = self.confirmation_store.invalidate_all()

        # 3. Cancel task queue items
        tasks_cancelled = self.task_queue.cancel_all()

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        event_data = {
            "status": "STOPPED",
            "groups_killed": groups_killed,
            "confirmations_invalidated": confirmations_invalidated,
            "tasks_cancelled": tasks_cancelled,
            "elapsed_ms": elapsed_ms,
        }
        self.audit_logger.log_event("KILL_SWITCH_STOP", event_data)
        logger.warning(
            "KILL SWITCH STOP executed in %.2f ms (groups: %d, confirms: %d, tasks: %d)",
            elapsed_ms,
            groups_killed,
            confirmations_invalidated,
            tasks_cancelled,
        )
        return event_data

    async def trigger_resume(self) -> dict[str, Any]:
        """Resume agent from stopped state."""
        self.is_stopped = False
        event_data = {"status": "IDLE"}
        self.audit_logger.log_event("KILL_SWITCH_RESUME", event_data)
        logger.info("KILL SWITCH RESUMED to IDLE state.")
        return event_data

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            line_bytes = await reader.readline()
            if not line_bytes:
                return

            line = line_bytes.decode("utf-8").strip()
            parts = line.split()
            cmd = parts[0].upper() if parts else ""

            if cmd == "STOP":
                res = await self.trigger_stop()
            elif cmd == "RESUME":
                res = await self.trigger_resume()
            elif cmd == "STATUS":
                res = {
                    "is_stopped": self.is_stopped,
                    "active_groups": self.process_registry.list_pgids(),
                }
            elif cmd == "REGISTER_PGID" and len(parts) > 1:
                try:
                    pgid = int(parts[1])
                    self.process_registry.register_pgid(pgid)
                    res = {"registered": pgid}
                except ValueError:
                    res = {"error": "Invalid PGID"}
            elif cmd == "UNREGISTER_PGID" and len(parts) > 1:
                try:
                    pgid = int(parts[1])
                    self.process_registry.unregister_pgid(pgid)
                    res = {"unregistered": pgid}
                except ValueError:
                    res = {"error": "Invalid PGID"}
            else:
                res = {"error": f"Unknown command: {line}"}

            writer.write(json.dumps(res).encode("utf-8") + b"\n")
            await writer.drain()
        except Exception as e:  # noqa: BLE001
            logger.error("Error handling killswitch client: %s", e)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001, S110
                pass


_global_service: KillSwitchService | None = None


def get_killswitch_service() -> KillSwitchService:
    global _global_service
    if _global_service is None:
        _global_service = KillSwitchService()
    return _global_service


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    service = get_killswitch_service()
    await service.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
