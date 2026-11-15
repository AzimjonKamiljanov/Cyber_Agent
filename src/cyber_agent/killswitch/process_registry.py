"""Process Group registry for subprocess tracking and kill switch termination."""

import logging
import os
import signal
import threading

logger = logging.getLogger(__name__)


class ProcessRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pgids: set[int] = set()

    def register_pgid(self, pgid: int) -> None:
        with self._lock:
            self._pgids.add(pgid)
        logger.debug("Registered process group: %d", pgid)

    def unregister_pgid(self, pgid: int) -> None:
        with self._lock:
            self._pgids.discard(pgid)
        logger.debug("Unregistered process group: %d", pgid)

    def list_pgids(self) -> list[int]:
        with self._lock:
            return list(self._pgids)

    def kill_all(self) -> int:
        """Send SIGKILL to all tracked process groups."""
        with self._lock:
            targets = list(self._pgids)
            self._pgids.clear()

        killed = 0
        for pgid in targets:
            try:
                os.killpg(pgid, signal.SIGKILL)
                killed += 1
                logger.info("Sent SIGKILL to process group %d", pgid)
            except ProcessLookupError:
                # Already terminated
                pass
            except PermissionError as e:
                logger.error("Permission error killing process group %d: %s", pgid, e)
            except OSError as e:
                logger.warning("OSError killing process group %d: %s", pgid, e)

        return killed


_default_registry = ProcessRegistry()


def get_process_registry() -> ProcessRegistry:
    return _default_registry
