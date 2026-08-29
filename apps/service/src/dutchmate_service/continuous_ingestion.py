"""Service-owned continuous draining for finite capture workflows."""

from __future__ import annotations

import math
from collections import deque
from contextlib import suppress
from threading import Condition, Event, RLock, Thread
from typing import Final

from dutchmate_core.backends import BackendEvent, SegmentContext
from dutchmate_core.workflows.capture import CaptureEventSource

DEFAULT_INGESTION_QUEUE_CAPACITY: Final = 256
DEFAULT_INGESTION_EVENT_WAIT_TIMEOUT_S: Final = 0.1


class ContinuousIngestionCoordinator:
    """Continuously drain one source and expose an active-workflow FIFO."""

    def __init__(
        self,
        source: CaptureEventSource,
        *,
        queue_capacity: int = DEFAULT_INGESTION_QUEUE_CAPACITY,
        event_wait_timeout_s: float = DEFAULT_INGESTION_EVENT_WAIT_TIMEOUT_S,
    ) -> None:
        if (
            isinstance(queue_capacity, bool)
            or not isinstance(queue_capacity, int)
            or queue_capacity <= 0
        ):
            raise ValueError("continuous ingestion queue capacity must be a positive integer")
        if (
            isinstance(event_wait_timeout_s, bool)
            or not isinstance(event_wait_timeout_s, (int, float))
            or not math.isfinite(event_wait_timeout_s)
            or event_wait_timeout_s <= 0
        ):
            raise ValueError(
                "continuous ingestion event wait timeout must be positive and finite"
            )

        self._condition = Condition(RLock())
        self._source: CaptureEventSource | None = source
        self._segment = _source_segment(source)
        self._events: deque[BackendEvent] = deque()
        self._queue_capacity = queue_capacity
        self._event_wait_timeout_s = float(event_wait_timeout_s)
        self._workflow_active = False
        self._generation = 0
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._close_error: BaseException | None = None
        self._thread = Thread(
            target=self._ingest,
            name="dutchmate-continuous-ingestion",
            daemon=False,
        )
        try:
            self._thread.start()
        except BaseException:
            with suppress(BaseException):
                _close_source(source)
            raise

    @property
    def segment(self) -> SegmentContext | None:
        """Return the latest timestamp provenance published by the source."""

        with self._condition:
            return self._segment

    def begin_workflow(self) -> None:
        """Establish a fresh cursor for one finite workflow."""

        with self._condition:
            if self._workflow_active:
                raise RuntimeError("continuous ingestion workflow is already active")
            self._generation += 1
            self._events.clear()
            self._workflow_active = True
            self._condition.notify_all()

    def end_workflow(self) -> None:
        """Return to idle draining and discard unread workflow events."""

        with self._condition:
            self._workflow_active = False
            self._events.clear()
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        """Return the next active-workflow event or an inactivity timeout."""

        with self._condition:
            if not self._workflow_active:
                raise RuntimeError("continuous ingestion workflow is not active")
            if not self._events:
                self._condition.wait(timeout=self._event_wait_timeout_s)
            if self._events:
                event = self._events.popleft()
                self._condition.notify_all()
                return event
            return None

    def discard_pending_events(self) -> None:
        """Retain active events because workflow activation owns cursor freshness."""

    def close(self) -> None:
        """Close the source and join the single ingestion thread."""

        with self._condition:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            self._closing = True
            self._workflow_active = False
            self._events.clear()
            source = self._source
            self._condition.notify_all()

        close_error: BaseException | None = None
        try:
            if source is not None:
                _close_source(source)
        except BaseException as exc:
            close_error = exc
        finally:
            try:
                self._thread.join()
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
            with self._condition:
                self._source = None
                self._close_error = close_error
                self._closed = True
                self._condition.notify_all()
            self._close_complete.set()

        if close_error is not None:
            raise close_error

    def _ingest(self) -> None:
        while True:
            with self._condition:
                if self._closing:
                    return
                source = self._source
            if source is None:
                return

            try:
                event = source.read_event()
            except BaseException:
                with self._condition:
                    if self._closing or source is not self._source:
                        continue
                return

            source_segment = _source_segment(source)
            with self._condition:
                if source is self._source:
                    self._segment = source_segment
                if self._closing:
                    return
                if source is not self._source or event is None or not self._workflow_active:
                    continue

                event_generation = self._generation
                while len(self._events) >= self._queue_capacity:
                    self._condition.wait()
                    if (
                        self._closing
                        or source is not self._source
                        or not self._workflow_active
                        or event_generation != self._generation
                    ):
                        break
                else:
                    self._events.append(event)
                    self._condition.notify_all()


def _source_segment(source: CaptureEventSource) -> SegmentContext | None:
    segment = getattr(source, "segment", None)
    return segment if isinstance(segment, SegmentContext) else None


def _close_source(source: CaptureEventSource) -> None:
    close = getattr(source, "close", None)
    if callable(close):
        close()
