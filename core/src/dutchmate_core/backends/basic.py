"""Basic generic USB-to-UART connection, receive, and send adapter."""

from __future__ import annotations

import asyncio
import importlib
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Final, Protocol, cast

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendCapabilityError,
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    BackendWriteError,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
    apply_capability_policy,
    integrity_for_backend,
)
from dutchmate_core.backends.settings import BackendSettings

DEFAULT_SERIAL_TIMEOUT_S: Final = 1.0
DEFAULT_EVENT_READ_TIMEOUT_S: Final = 0.1
DEFAULT_READ_SIZE: Final = 4096


class BasicSerialPort(Protocol):
    """Small raw pyserial surface owned by the Basic backend."""

    def read(self, size: int = 1) -> bytes:
        """Read up to ``size`` raw UART bytes."""

    def write(self, data: bytes) -> int:
        """Write raw UART bytes."""

    def close(self) -> None:
        """Close the serial port."""


BasicSerialFactory = Callable[..., BasicSerialPort]


class BasicBackendConnection:
    """An opened Basic serial port and its immutable backend identity."""

    def __init__(
        self,
        *,
        serial_port: BasicSerialPort,
        settings: BackendSettings,
    ) -> None:
        if settings.mode != "basic" or settings.serial_port is None:
            raise ValueError("Basic connection requires resolved Basic backend settings")
        capabilities: frozenset[BackendCapability] = frozenset(
            {"uart_receive", "uart_send"}
        )
        self._serial_port = serial_port
        self._write_lock = Lock()
        self._capability_policy = BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(
                tx_policy_enabled=settings.tx_enabled,
            )
        )
        self._info = BackendInfo(
            mode="basic",
            port=settings.serial_port,
            device=None,
            firmware=None,
            capabilities=capabilities,
        )

    @property
    def info(self) -> BackendInfo:
        """Return Basic identity without a DUTchMate hello."""

        return self._info

    @property
    def serial_port(self) -> BasicSerialPort:
        """Return the owned raw serial port for the receive adapter."""

        return self._serial_port

    @property
    def capability_policy(self) -> BackendCapabilityPolicy:
        """Return the configured software capability policy."""

        return self._capability_policy

    @property
    def capabilities(self) -> frozenset[BackendCapability]:
        """Return capabilities remaining after host policy is applied."""

        return apply_capability_policy(self._info.capabilities, self._capability_policy)

    def send_uart(self, data: bytes) -> int:
        """Write a complete UART payload, retrying ordered short writes."""

        if "uart_send" not in self.capabilities:
            raise BackendCapabilityError("Basic backend UART send is disabled")
        if not isinstance(data, bytes):
            raise TypeError("Basic UART payload must be bytes")
        if not data:
            raise ValueError("Basic UART payload must not be empty")

        accepted = 0
        with self._write_lock:
            while accepted < len(data):
                try:
                    written = self._serial_port.write(data[accepted:])
                except Exception as exc:
                    raise BackendWriteError(
                        "Basic UART write failed",
                        bytes_accepted=accepted,
                    ) from exc
                remaining = len(data) - accepted
                if (
                    isinstance(written, bool)
                    or not isinstance(written, int)
                    or written <= 0
                    or written > remaining
                ):
                    raise BackendWriteError(
                        "Basic UART write made invalid progress",
                        bytes_accepted=accepted,
                    )
                accepted += written
        return accepted

    def close(self) -> None:
        """Close the underlying serial port."""

        self._serial_port.close()


@dataclass(frozen=True, slots=True)
class _ReaderFailure:
    error: BackendDisconnectedError | BackendInputError


@dataclass(frozen=True, slots=True)
class _SourceClosed:
    pass


_ReaderOutcome = BackendEvent | _ReaderFailure | _SourceClosed


class BasicBackendEventSource:
    """Normalize raw Basic serial chunks through one FIFO reader thread."""

    def __init__(
        self,
        connection: BasicBackendConnection,
        *,
        segment_id: int,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        read_size: int = DEFAULT_READ_SIZE,
        read_timeout_s: float = DEFAULT_EVENT_READ_TIMEOUT_S,
    ) -> None:
        if not isinstance(segment_id, int) or isinstance(segment_id, bool) or segment_id < 0:
            raise ValueError("Basic segment ID must be a non-negative integer")
        if not isinstance(read_size, int) or isinstance(read_size, bool) or read_size <= 0:
            raise ValueError("Basic serial read size must be a positive integer")
        _validate_timeout(read_timeout_s, field="Basic event read timeout")

        source_origin_ns = monotonic_ns()
        if not isinstance(source_origin_ns, int) or isinstance(source_origin_ns, bool):
            raise ValueError("Basic monotonic clock must return integer nanoseconds")
        source_origin_us = source_origin_ns // 1_000
        if source_origin_us < 0:
            raise ValueError("Basic monotonic source origin must be non-negative")

        self._connection = connection
        self._segment = SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=source_origin_us,
                observation_point="host_serial_read",
                event_granularity="serial_read_chunk",
            ),
        )
        self._monotonic_ns = monotonic_ns
        self._read_size = read_size
        self._read_timeout_s = read_timeout_s
        self._outcomes: Queue[_ReaderOutcome] = Queue()
        self._stop = Event()
        self._start_lock = Lock()
        self._reader: Thread | None = None
        self._terminal_error: BackendDisconnectedError | BackendInputError | None = None

    @property
    def info(self) -> BackendInfo:
        """Return immutable Basic backend identity and capabilities."""

        return self._connection.info

    @property
    def segment_id(self) -> int:
        """Return the session-local segment ID assigned to this source."""

        return self._segment.segment_id

    @property
    def segment(self) -> SegmentContext:
        """Return host-monotonic provenance established at source creation."""

        return self._segment

    @property
    def snapshot(self) -> BackendSnapshot:
        """Return the complete Basic identity/policy/provenance snapshot."""

        return BackendSnapshot(
            info=self._connection.info,
            capabilities=self._connection.capabilities,
            capability_policy=self._connection.capability_policy,
            segment=self._segment,
            integrity=integrity_for_backend("basic"),
        )

    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
        """Return the next FIFO event, or ``None`` for an ordinary timeout."""

        if timeout_s is not None:
            _validate_timeout(timeout_s, field="Basic receive timeout", allow_zero=True)
        return await asyncio.to_thread(self._next_event, timeout_s)

    def read_event(self) -> BackendEvent | None:
        """Blocking compatibility adapter used by the current capture runner."""

        return self._next_event(self._read_timeout_s)

    def discard_pending_events(self) -> None:
        """Advance a workflow ingestion cursor past already-normalized UART events."""

        retained: list[_ReaderOutcome] = []
        while True:
            try:
                outcome = self._outcomes.get_nowait()
            except Empty:
                break
            if not isinstance(outcome, UartReceiveEvent):
                retained.append(outcome)
        for outcome in retained:
            self._outcomes.put(outcome)

    def close(self) -> None:
        """Stop the reader and close the Basic serial connection."""

        if self._stop.is_set():
            return
        self._stop.set()
        try:
            self._connection.close()
        finally:
            reader = self._reader
            if reader is not None:
                reader.join(timeout=DEFAULT_SERIAL_TIMEOUT_S + 0.1)
            self._outcomes.put(_SourceClosed())

    def _ensure_reader_started(self) -> None:
        if self._reader is not None:
            return
        with self._start_lock:
            if self._reader is not None:
                return
            if self._stop.is_set():
                self._terminal_error = BackendDisconnectedError(
                    "Basic backend event source is closed"
                )
                return
            reader = Thread(
                target=self._read_serial,
                name="dutchmate-basic-serial-reader",
                daemon=True,
            )
            self._reader = reader
            reader.start()

    def _read_serial(self) -> None:
        while not self._stop.is_set():
            try:
                data = self._connection.serial_port.read(self._read_size)
            except Exception as exc:
                if not self._stop.is_set():
                    error = BackendDisconnectedError("Basic serial read failed")
                    error.__cause__ = exc
                    self._outcomes.put(_ReaderFailure(error))
                return

            if not isinstance(data, bytes):
                self._outcomes.put(
                    _ReaderFailure(
                        BackendInputError("Basic serial read returned non-bytes input")
                    )
                )
                return
            if not data:
                continue
            try:
                observed_ns = self._monotonic_ns()
                if not isinstance(observed_ns, int) or isinstance(observed_ns, bool):
                    raise TypeError("monotonic clock did not return an integer")
                observed_us = observed_ns // 1_000
            except Exception as exc:
                input_error = BackendInputError("Basic monotonic clock sampling failed")
                input_error.__cause__ = exc
                self._outcomes.put(_ReaderFailure(input_error))
                return
            timestamp_us = observed_us - self._segment.timestamp.source_origin_us
            if timestamp_us < 0:
                self._outcomes.put(
                    _ReaderFailure(
                        BackendInputError(
                            "Basic monotonic timestamp precedes its segment origin"
                        )
                    )
                )
                return
            self._outcomes.put(
                UartReceiveEvent(
                    segment_id=self.segment_id,
                    timestamp_us=timestamp_us,
                    channel=0,
                    data=data,
                )
            )

    def _next_event(self, timeout_s: float | None) -> BackendEvent | None:
        if self._terminal_error is not None:
            raise self._terminal_error
        self._ensure_reader_started()
        if self._terminal_error is not None:
            raise self._terminal_error
        try:
            if timeout_s is None:
                outcome = self._outcomes.get()
            else:
                outcome = self._outcomes.get(timeout=timeout_s)
        except Empty:
            return None

        if isinstance(outcome, _ReaderFailure):
            self._terminal_error = outcome.error
            raise outcome.error
        if isinstance(outcome, _SourceClosed):
            self._terminal_error = BackendDisconnectedError(
                "Basic backend event source is closed"
            )
            raise self._terminal_error
        return outcome


def _validate_timeout(
    value: float,
    *,
    field: str,
    allow_zero: bool = False,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    normalized = float(value)
    minimum_valid = normalized >= 0 if allow_zero else normalized > 0
    if not math.isfinite(normalized) or not minimum_valid:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field} must be a finite {qualifier} number")


def open_basic_backend_connection(
    settings: BackendSettings,
    *,
    timeout_s: float = DEFAULT_SERIAL_TIMEOUT_S,
    serial_factory: BasicSerialFactory | None = None,
) -> BasicBackendConnection:
    """Open a Basic backend as raw 8-N-1 serial without reading a hello."""

    if settings.mode != "basic" or settings.serial_port is None:
        raise ValueError("Basic connection requires resolved Basic backend settings")
    factory = serial_factory or _pyserial_factory()
    serial_port = factory(
        port=settings.serial_port,
        baudrate=settings.baudrate,
        bytesize=settings.data_bits,
        parity="N",
        stopbits=settings.stop_bits,
        timeout=timeout_s,
        write_timeout=timeout_s,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )
    return BasicBackendConnection(serial_port=serial_port, settings=settings)


def _pyserial_factory() -> BasicSerialFactory:
    serial_module = importlib.import_module("serial")
    return cast(BasicSerialFactory, serial_module.Serial)
