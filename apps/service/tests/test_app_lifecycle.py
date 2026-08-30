import threading
from pathlib import Path
from threading import Condition, Event

import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, disconnected_status

from dutchmate_core.backends import BackendEvent
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.gpio_config.config import HardwareGpioConfig, parse_hardware_gpio_config
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_service import app as app_module
from dutchmate_service.continuous_ingestion import ContinuousIngestionCoordinator


class ClosableFakeRuntime(FakeRuntime):
    def __init__(self, *, close_error: Exception | None = None) -> None:
        super().__init__(disconnected_status())
        self.close_count = 0
        self._close_error = close_error

    def close(self) -> None:
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


class BlockingCaptureSource:
    def __init__(self) -> None:
        self.read_started = Event()
        self.close_count = 0
        self._condition = Condition()
        self._closed = False

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            self.read_started.set()
            while not self._closed:
                self._condition.wait()
            return None

    def close(self) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self.close_count += 1
            self._condition.notify_all()


class NoopDeviceControl:
    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> None:
        del channel, mode, active_level, idle_level

    def pulse_control(self, *, channel: str, pulse_ms: int) -> None:
        del channel, pulse_ms

    def set_control_state(self, *, channel: str, state: ControlState) -> None:
        del channel, state


def test_app_lifespan_closes_internally_constructed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch an application shutdown that leaks the runtime it constructed."""

    runtime = ClosableFakeRuntime()
    monkeypatch.setattr(app_module, "build_startup_runtime", lambda **_kwargs: runtime)

    with TestClient(app_module.create_app()) as client:
        assert client.get("/status").status_code == 200
        assert runtime.close_count == 0

    assert runtime.close_count == 1


def test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catch app-owned shutdown returning with a source or ingestion thread alive."""

    source = BlockingCaptureSource()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
    )
    monkeypatch.setattr(app_module, "build_startup_runtime", lambda **_kwargs: runtime)

    with TestClient(app_module.create_app()) as client:
        assert source.read_started.wait(timeout=1)
        assert client.get("/status").status_code == 200
        assert any(
            thread.name == "dutchmate-continuous-ingestion"
            for thread in threading.enumerate()
        )

    assert source.close_count == 1
    assert all(
        thread.name != "dutchmate-continuous-ingestion"
        for thread in threading.enumerate()
    )


def test_app_lifespan_keeps_injected_runtime_caller_owned() -> None:
    """Catch application shutdown closing a runtime supplied by its caller."""

    runtime = ClosableFakeRuntime()

    with TestClient(app_module.create_app(runtime)) as client:
        assert client.get("/status").status_code == 200

    assert runtime.close_count == 0


def test_internal_runtime_cleanup_preserves_hardware_configuration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch startup cleanup that leaks its runtime or masks its primary failure."""

    primary_error = RuntimeError("hardware configuration failed")
    runtime = ClosableFakeRuntime(close_error=RuntimeError("runtime close failed"))
    monkeypatch.setattr(app_module, "build_startup_runtime", lambda **_kwargs: runtime)

    def fail_hardware_config(
        _runtime: object,
        _config: HardwareGpioConfig,
    ) -> bool:
        raise primary_error

    monkeypatch.setattr(app_module, "apply_startup_hardware_config", fail_hardware_config)

    with pytest.raises(RuntimeError) as raised:
        app_module.create_app(hardware_config=_hardware_config())

    assert raised.value is primary_error
    assert runtime.close_count == 1


def _hardware_config() -> HardwareGpioConfig:
    return parse_hardware_gpio_config(
        {
            "hardware": {
                "control": {
                    "reset": {
                        "channel": "CTRL0",
                        "dut_signal": "RESET_N",
                        "mode": "open_drain",
                        "active_level": "low",
                    }
                }
            }
        }
    )
