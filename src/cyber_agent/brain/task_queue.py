"""In-memory async task queue for long-running non-blocking jobs."""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cyber_agent.audit.logger import get_audit_logger

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskItem:
    task_id: str
    description: str
    coro_fn: Callable[[], Coroutine[Any, Any, Any]]
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    on_complete: Callable[["TaskItem"], Awaitable[None]] | None = None
    asyncio_task: asyncio.Task[Any] | None = None


class TaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[TaskItem] = asyncio.Queue()
        self._tasks: dict[str, TaskItem] = {}
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False
        self.audit_logger = get_audit_logger()

    def start(self) -> None:
        if self._running and self._worker_task and not self._worker_task.done():
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._worker_loop())
        except RuntimeError:
            # Event loop not yet running; worker will be spawned on first enqueue
            pass

    async def stop(self) -> None:
        self._running = False
        self.cancel_all()
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def enqueue_task(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, Any]],
        description: str,
        on_complete: Callable[[TaskItem], Awaitable[None]] | None = None,
    ) -> str:
        self.start()
        task_id = str(uuid.uuid4())
        item = TaskItem(
            task_id=task_id,
            description=description,
            coro_fn=coro_fn,
            on_complete=on_complete,
        )
        self._tasks[task_id] = item
        await self._queue.put(item)
        self.audit_logger.log_event("TASK_ENQUEUED", {"task_id": task_id, "description": description})
        return task_id

    def cancel_all(self) -> int:
        cancelled_count = 0
        for task in self._tasks.values():
            if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(UTC).isoformat()
                if task.asyncio_task and not task.asyncio_task.done():
                    task.asyncio_task.cancel()
                cancelled_count += 1
        self.audit_logger.log_event("TASK_QUEUE_CANCELLED_ALL", {"cancelled_count": cancelled_count})
        return cancelled_count

    def get_task(self, task_id: str) -> TaskItem | None:
        return self._tasks.get(task_id)

    def list_active(self) -> list[TaskItem]:
        return [t for t in self._tasks.values() if t.status in {TaskStatus.PENDING, TaskStatus.RUNNING}]

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                item = await self._queue.get()
            except asyncio.CancelledError:
                break

            if item.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            item.status = TaskStatus.RUNNING
            self.audit_logger.log_event("TASK_STARTED", {"task_id": item.task_id, "description": item.description})

            current_task: asyncio.Task[Any] = asyncio.create_task(item.coro_fn())
            item.asyncio_task = current_task

            try:
                result = await current_task
                item.result = result
                item.status = TaskStatus.COMPLETED
                item.completed_at = datetime.now(UTC).isoformat()
                self.audit_logger.log_event("TASK_COMPLETED", {"task_id": item.task_id, "description": item.description})
            except asyncio.CancelledError:
                item.status = TaskStatus.CANCELLED
                item.completed_at = datetime.now(UTC).isoformat()
                self.audit_logger.log_event("TASK_CANCELLED", {"task_id": item.task_id})
            except Exception as e:  # noqa: BLE001
                item.status = TaskStatus.FAILED
                item.error = str(e)
                item.completed_at = datetime.now(UTC).isoformat()
                self.audit_logger.log_event("TASK_FAILED", {"task_id": item.task_id, "error": str(e)})
            finally:
                self._queue.task_done()

            if item.on_complete:
                try:
                    await item.on_complete(item)
                except Exception as e:  # noqa: BLE001
                    logger.error("Error in on_complete callback for task %s: %s", item.task_id, e)


_default_task_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    global _default_task_queue
    if _default_task_queue is None:
        _default_task_queue = TaskQueue()
        _default_task_queue.start()
    return _default_task_queue
