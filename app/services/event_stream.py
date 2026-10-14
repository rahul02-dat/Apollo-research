"""Real-time event streaming and pub/sub service for Apollo research runs."""

from datetime import datetime, timezone
import json
import logging
import queue
import threading
from typing import Any, Generator

logger = logging.getLogger(__name__)


class RunEvent:
    def __init__(self, run_id: str, event_type: str, message: str, data: dict[str, Any] | None = None) -> None:
        self.run_id = run_id
        self.event_type = event_type
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
        }

    def to_sse(self) -> str:
        return f"data: {json.dumps(self.to_dict())}\n\n"


class EventBroadcaster:
    """Thread-safe event pub/sub for real-time SSE streaming."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[queue.Queue[RunEvent | None]]] = {}
        self._history: dict[str, list[RunEvent]] = {}
        self._lock = threading.Lock()

    def publish(self, run_id: str, event_type: str, message: str, data: dict[str, Any] | None = None) -> RunEvent:
        event = RunEvent(run_id=run_id, event_type=event_type, message=message, data=data)
        with self._lock:
            if run_id not in self._history:
                self._history[run_id] = []
            self._history[run_id].append(event)

            listeners = self._listeners.get(run_id, [])
            for q in listeners:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass

        logger.info("[Event] Run %s: %s - %s", run_id, event_type, message)
        return event

    def subscribe(self, run_id: str) -> Generator[str, None, None]:
        q: queue.Queue[RunEvent | None] = queue.Queue(maxsize=100)

        with self._lock:
            if run_id not in self._listeners:
                self._listeners[run_id] = []
            self._listeners[run_id].append(q)

            # Replay existing history first
            for past_event in self._history.get(run_id, []):
                q.put_nowait(past_event)

        try:
            while True:
                try:
                    event = q.get(timeout=25.0)
                    if event is None:
                        break
                    yield event.to_sse()
                    if event.event_type in ["RUN_COMPLETED", "RUN_FAILED"]:
                        break
                except queue.Empty:
                    # Keep-alive heartbeat comment
                    yield ": keep-alive\n\n"
        finally:
            with self._lock:
                if run_id in self._listeners and q in self._listeners[run_id]:
                    self._listeners[run_id].remove(q)

    async def subscribe_async(self, run_id: str, heartbeat_seconds: float = 15.0) -> Any:
        import asyncio

        q: queue.Queue[RunEvent | None] = queue.Queue(maxsize=100)

        with self._lock:
            if run_id not in self._listeners:
                self._listeners[run_id] = []
            self._listeners[run_id].append(q)

            # Replay existing history first
            for past_event in self._history.get(run_id, []):
                q.put_nowait(past_event)

        idle_cycles = 0
        cycle_delay = 0.1
        heartbeat_cycles = int(heartbeat_seconds / cycle_delay)

        try:
            while True:
                try:
                    event = q.get_nowait()
                    idle_cycles = 0
                    if event is None:
                        break
                    yield event.to_sse()
                    if event.event_type in ["RUN_COMPLETED", "RUN_FAILED", "RUN_REJECTED"]:
                        break
                except queue.Empty:
                    await asyncio.sleep(cycle_delay)
                    idle_cycles += 1
                    if idle_cycles >= heartbeat_cycles:
                        yield ": keep-alive\n\n"
                        idle_cycles = 0
        finally:
            with self._lock:
                if run_id in self._listeners and q in self._listeners[run_id]:
                    self._listeners[run_id].remove(q)


    def close(self, run_id: str) -> None:
        with self._lock:
            listeners = self._listeners.get(run_id, [])
            for q in listeners:
                try:
                    q.put_nowait(None)
                except queue.Full:
                    pass


# Global broadcaster instance
event_broadcaster = EventBroadcaster()
