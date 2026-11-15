"""Session taint tracking for Cyber Agent.

Untrusted external content (web pages, PDFs, emails, tool outputs)
marks the session as tainted, elevating confirmation checks.
"""

import threading


class SessionTaintTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tainted = False
        self._sources: list[str] = []

    def mark_tainted(self, source: str) -> None:
        """Mark session context as tainted by an untrusted source."""
        with self._lock:
            self._tainted = True
            if source not in self._sources:
                self._sources.append(source)

    def is_tainted(self) -> bool:
        with self._lock:
            return self._tainted

    def get_taint_sources(self) -> list[str]:
        with self._lock:
            return list(self._sources)

    def reset(self) -> None:
        with self._lock:
            self._tainted = False
            self._sources.clear()


_global_taint_tracker: SessionTaintTracker | None = None


def get_taint_tracker() -> SessionTaintTracker:
    global _global_taint_tracker
    if _global_taint_tracker is None:
        _global_taint_tracker = SessionTaintTracker()
    return _global_taint_tracker
