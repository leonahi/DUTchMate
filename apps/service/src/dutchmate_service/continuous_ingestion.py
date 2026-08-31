"""Service-owned continuous draining for finite capture workflows."""

from __future__ import annotations

import math
from collections import deque
from contextlib import suppress
from dataclasses import replace
from threading import Condition, Event, RLock, Thread
from typing import Final

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
    BackendInputError,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartIntegrity,
)
from dutchmate_core.workflows.capture import CaptureEventSource, CaptureSourceHealth

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
        backend_snapshot: BackendSnapshot | None = None,
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
        self._connection_generation = 0
        self._health = CaptureSourceHealth(
            connected=True,
            integrity=None,
            backend_snapshot=backend_snapshot,
            connection_generation=self._connection_generation,
        )
        self._events: deque[BackendEvent] = deque()
        self._queue_capacity = queue_capacity
        self._event_wait_timeout_s = float(event_wait_timeout_s)
        self._workflow_active = False
        self._generation = 0
        self._terminal_error: BaseException | None = None
        self._terminal_consumed = False
        self._replacement_allowed = False
        self._ingestion_stopped = False
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._source_close_complete = Event()
        self._source_close_complete.set()
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

    def capture_source_health(self) -> CaptureSourceHealth:
        """Return one immutable health snapshot for the installed source."""

        with self._condition:
            return self._health

    def begin_workflow(self) -> None:
        """Establish a fresh cursor for one finite workflow."""

        with self._condition:
            if self._closing or self._closed:
                raise RuntimeError("continuous ingestion coordinator is closing")
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
            if self._terminal_error is not None:
                self._terminal_consumed = True
                raise self._terminal_error
            return None

    def discard_pending_events(self) -> None:
        """Retain active events because workflow activation owns cursor freshness."""

    def wait_for_idle_disconnect(self, timeout_s: float) -> bool:
        """Wait until an idle source disconnect can be claimed for replacement."""

        with self._condition:
            self._condition.wait_for(
                lambda: self._closing
                or self._closed
                or self._ingestion_stopped
                or (
                    not self._workflow_active
                    and isinstance(self._terminal_error, BackendDisconnectedError)
                    and self._replacement_allowed
                    and self._source is not None
                ),
                timeout=timeout_s,
            )
            return (
                not self._closing
                and not self._closed
                and not self._ingestion_stopped
                and not self._workflow_active
                and isinstance(self._terminal_error, BackendDisconnectedError)
                and self._replacement_allowed
                and self._source is not None
            )

    def close_current_source_for_reconnect(self, *, idle: bool = False) -> None:
        """Detach and close the consumed disconnected source."""

        with self._condition:
            if self._close_error is not None:
                raise self._close_error
            can_detach = (
                not self._closing
                and not self._closed
                and isinstance(self._terminal_error, BackendDisconnectedError)
                and self._replacement_allowed
                and self._source is not None
                and (
                    (idle and not self._workflow_active)
                    or (not idle and self._terminal_consumed)
                )
            )
            if not can_detach:
                raise RuntimeError(
                    "continuous ingestion coordinator cannot detach source for reconnect"
                )
            if idle:
                self._terminal_consumed = True
            source = self._source
            assert source is not None
            self._source = None
            self._replacement_allowed = False
            self._source_close_complete.clear()
            self._condition.notify_all()

        close_error: BaseException | None = None
        try:
            _close_source(source)
        except BaseException as exc:
            close_error = exc
        finally:
            with self._condition:
                if close_error is not None:
                    if self._close_error is None:
                        self._close_error = close_error
                    self._ingestion_stopped = True
                self._condition.notify_all()
            self._source_close_complete.set()

        if close_error is not None:
            with self._condition:
                retained_error = self._close_error
            assert retained_error is not None
            raise retained_error

        with self._condition:
            if not self._closing and not self._closed and not self._ingestion_stopped:
                self._replacement_allowed = True
            self._condition.notify_all()

    def replace_source(
        self,
        replacement: CaptureEventSource,
        *,
        backend_snapshot: BackendSnapshot | None = None,
    ) -> None:
        """Transfer one validated replacement into the stable coordinator."""

        preparation_error: BaseException | None = None
        with self._condition:
            can_accept = (
                not self._closing
                and not self._closed
                and not self._ingestion_stopped
                and self._source is None
                and self._replacement_allowed
                and self._terminal_consumed
                and isinstance(self._terminal_error, BackendDisconnectedError)
                and self._close_error is None
            )
            if can_accept:
                try:
                    replacement_segment = _source_segment(replacement)
                    connection_generation = self._connection_generation + 1
                    health = CaptureSourceHealth(
                        connected=True,
                        integrity=None,
                        backend_snapshot=backend_snapshot,
                        connection_generation=connection_generation,
                    )
                except BaseException as error:
                    preparation_error = error
                else:
                    self._connection_generation = connection_generation
                    self._source = replacement
                    self._segment = replacement_segment
                    self._health = health
                    self._terminal_error = None
                    self._terminal_consumed = False
                    self._replacement_allowed = False
                    self._condition.notify_all()
                    return

        with suppress(BaseException):
            _close_source(replacement)
        if preparation_error is not None:
            raise preparation_error
        raise RuntimeError("continuous ingestion coordinator cannot accept replacement")

    def close(self) -> None:
        """Close the source and join the single ingestion thread."""

        with self._condition:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            if self._closing:
                first_closer = False
                source = None
                wait_for_source_close = False
            else:
                first_closer = True
                self._closing = True
                self._health = replace(self._health, connected=False)
                self._workflow_active = False
                self._events.clear()
                if self._terminal_error is None:
                    self._terminal_error = BackendDisconnectedError(
                        "continuous ingestion coordinator is closed"
                    )
                    self._terminal_consumed = False
                source = self._source
                wait_for_source_close = not self._source_close_complete.is_set()
                self._condition.notify_all()

        if not first_closer:
            self._close_complete.wait()
            with self._condition:
                retained_error = self._close_error
            if retained_error is not None:
                raise retained_error
            return

        close_error: BaseException | None = None
        try:
            if wait_for_source_close:
                self._source_close_complete.wait()
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
                if self._close_error is None:
                    self._close_error = close_error
                retained_error = self._close_error
                self._ingestion_stopped = True
                self._closed = True
                self._condition.notify_all()
            self._close_complete.set()

        if retained_error is not None:
            raise retained_error

    def _ingest(self) -> None:
        while True:
            with self._condition:
                while (
                    self._source is None
                    and not self._closing
                    and not self._ingestion_stopped
                ):
                    self._condition.wait()
                if self._closing or self._ingestion_stopped:
                    return
                source = self._source
            if source is None:
                continue

            try:
                event = source.read_event()
            except (BackendDisconnectedError, BackendInputError) as exc:
                with self._condition:
                    if source is self._source and not self._closing:
                        self._health = replace(self._health, connected=False)
                        self._terminal_error = exc
                        self._terminal_consumed = False
                        self._replacement_allowed = isinstance(
                            exc, BackendDisconnectedError
                        )
                        self._condition.notify_all()
                        while (
                            source is self._source
                            and not self._closing
                            and not self._ingestion_stopped
                        ):
                            self._condition.wait()
            except Exception as exc:
                self._terminalize_unexpected(source, exc)

            source_segment = _source_segment(source)
            with self._condition:
                if source is self._source and not self._closing:
                    self._segment = source_segment
                    if event is not None:
                        self._health = _project_event_health(self._health, event)
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

    def _terminalize_unexpected(
        self,
        source: CaptureEventSource,
        error: Exception,
    ) -> None:
        with self._condition:
            if self._closing or source is not self._source:
                return
            self._health = replace(self._health, connected=False)
            self._source = None
            self._terminal_error = error
            self._terminal_consumed = False
            self._replacement_allowed = False
            self._source_close_complete.clear()
            self._condition.notify_all()

        close_error: BaseException | None = None
        try:
            _close_source(source)
        except BaseException as exc:
            close_error = exc
        finally:
            with self._condition:
                if close_error is not None and self._close_error is None:
                    self._close_error = close_error
                self._ingestion_stopped = True
                self._condition.notify_all()
            self._source_close_complete.set()


def _source_segment(source: CaptureEventSource) -> SegmentContext | None:
    segment = getattr(source, "segment", None)
    return segment if isinstance(segment, SegmentContext) else None


def _project_event_health(
    health: CaptureSourceHealth,
    event: BackendEvent,
) -> CaptureSourceHealth:
    integrity = health.integrity
    previous_dropped = (
        integrity.dropped_bytes
        if integrity is not None and integrity.dropped_bytes is not None
        else 0
    )
    if isinstance(event, BufferOverflowEvent):
        return replace(
            health,
            integrity=UartIntegrity(
                "loss_reported",
                "debug_helper_rx_buffer",
                previous_dropped + event.dropped_bytes,
            ),
        )
    if isinstance(event, BufferStatusEvent):
        reported_loss = event.dropped_bytes_total > 0 or event.overflow_events > 0
        prior_loss = integrity is not None and integrity.loss_status == "loss_reported"
        return replace(
            health,
            integrity=UartIntegrity(
                "loss_reported" if prior_loss or reported_loss else "none_reported",
                "debug_helper_rx_buffer",
                max(previous_dropped, event.dropped_bytes_total),
            ),
        )
    return health


def _close_source(source: CaptureEventSource) -> None:
    close = getattr(source, "close", None)
    if callable(close):
        close()
