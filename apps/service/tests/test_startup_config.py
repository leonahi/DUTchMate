from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, disconnected_status

from dutchmate_core.backends.basic import BasicBackendConnection
from dutchmate_core.backends.enhanced import EnhancedDeviceControl, normalize_enhanced_hello
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.serial_transport import SerialCommandTransport
from dutchmate_core.gpio_config.config import parse_hardware_gpio_config
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionRecoveryResult, SessionStore
from dutchmate_service import startup
from dutchmate_service.app import create_app
from dutchmate_service.startup import (
    apply_startup_hardware_config,
    build_startup_runtime,
    load_startup_hardware_config,
    read_startup_hello,
)


class FakeTransport:
    def __init__(self, responses: list[DeviceMessage]) -> None:
        self._responses = responses
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> DeviceMessage:
        self.requests.append(command)
        if not self._responses:
            raise AssertionError("fake transport has no queued response")
        return self._responses.pop(0)


class FakeSerial:
    def __init__(self, reads: list[bytes]) -> None:
        self._reads = reads

    def write(self, data: bytes) -> int:
        return len(data)

    def read(self, size: int = 1) -> bytes:
        raise AssertionError("Basic startup must not read or wait for hello")

    def flush(self) -> None:
        pass

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        if not self._reads:
            return b""
        return self._reads.pop(0)

    def close(self) -> None:
        pass


def backend_settings(
    mode: str,
    *,
    serial_port: str | None,
    baudrate: int,
    tx_enabled: bool = False,
) -> BackendSettings:
    return BackendSettings(
        mode=mode,  # type: ignore[arg-type]
        serial_port=serial_port,
        reconnect_timeout_s=5.0,
        baudrate=baudrate,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=tx_enabled,
    )


def test_load_startup_hardware_config_returns_empty_config_when_missing(tmp_path: Path) -> None:
    config = load_startup_hardware_config(tmp_path / "missing.toml")

    assert config.controls == {}


def test_apply_startup_hardware_config_skips_disconnected_runtime() -> None:
    runtime = FakeRuntime(disconnected_status())
    config = parse_hardware_gpio_config(
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

    applied = apply_startup_hardware_config(runtime, config)

    assert applied is False
    assert runtime.hardware_configs == []


def test_read_startup_hello_returns_initial_hello() -> None:
    transport = SerialCommandTransport(
        FakeSerial(
            [
                b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
                b'"capabilities":["gpio_control"]}\n'
            ]
        )
    )

    hello = read_startup_hello(transport)

    assert hello == _hello()


def test_read_startup_hello_rejects_non_hello_message() -> None:
    transport = SerialCommandTransport(
        FakeSerial([b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n'])
    )

    with pytest.raises(
        RuntimeError,
        match="Expected Debug Helper hello message, got UartMessage",
    ):
        read_startup_hello(transport)


def test_build_startup_runtime_without_serial_port_is_disconnected(tmp_path: Path) -> None:
    runtime = build_startup_runtime(session_root=tmp_path)

    status = runtime.status()
    assert status.connected is False
    assert status.port is None
    assert runtime.session_store.root == tmp_path


def test_build_startup_runtime_passes_session_evidence_budget_to_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: list[tuple[Path | str, int]] = []

    def tracking_session_store(
        *,
        root: Path | str,
        evidence_budget_bytes: int,
    ) -> SessionStore:
        observed.append((root, evidence_budget_bytes))
        return SessionStore(root=root, evidence_budget_bytes=evidence_budget_bytes)

    monkeypatch.setattr(startup, "SessionStore", tracking_session_store)

    startup.build_startup_runtime(
        session_root=tmp_path,
        session_evidence_budget_bytes=10 * 1024 * 1024,
    )

    assert observed == [(tmp_path, 10 * 1024 * 1024)]


def test_build_startup_runtime_preserves_disconnected_enhanced_selection(
    tmp_path: Path,
) -> None:
    runtime = build_startup_runtime(
        session_root=tmp_path,
        backend_settings=backend_settings(
            "enhanced",
            serial_port=None,
            baudrate=460800,
        ),
    )

    status = runtime.status()
    assert status.connected is False
    assert status.backend_mode == "enhanced"
    assert status.port is None


def test_build_startup_runtime_with_serial_port_records_hello(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_open_serial_command_transport(
        *,
        port: str,
        baudrate: int,
    ) -> SerialCommandTransport:
        assert port == "/dev/ttyACM0"
        assert baudrate == 460800
        return SerialCommandTransport(
            FakeSerial(
                [
                    b'{"type":"hello","v":1,"firmware":"0.1.0",'
                    b'"device":"dutchmate-rp2040","capabilities":["gpio_control"]}\n'
                ]
            )
        )

    monkeypatch.setattr(
        "dutchmate_service.startup.open_serial_command_transport",
        fake_open_serial_command_transport,
    )

    runtime = build_startup_runtime(
        session_root=tmp_path,
        backend_settings=backend_settings(
            "enhanced",
            serial_port="/dev/ttyACM0",
            baudrate=460800,
        ),
    )

    status = runtime.status()
    assert status.connected is True
    assert status.port == "/dev/ttyACM0"
    assert status.firmware == "0.1.0"
    assert status.device == "dutchmate-rp2040"
    assert status.backend_mode == "enhanced"


def test_build_startup_runtime_opens_basic_without_hello(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = backend_settings(
        "basic",
        serial_port="/dev/ttyUSB0",
        baudrate=115200,
        tx_enabled=True,
    )
    serial = FakeSerial([])

    def fake_open_basic_backend_connection(
        received_settings: BackendSettings,
    ) -> BasicBackendConnection:
        assert received_settings == settings
        return BasicBackendConnection(serial_port=serial, settings=settings)

    monkeypatch.setattr(
        "dutchmate_service.startup.open_basic_backend_connection",
        fake_open_basic_backend_connection,
    )

    runtime = build_startup_runtime(session_root=tmp_path, backend_settings=settings)

    status = runtime.status()
    assert status.connected is True
    assert status.backend_mode == "basic"
    assert status.port == "/dev/ttyUSB0"
    assert status.device is None
    assert status.firmware is None
    assert status.backend_capabilities == ("uart_receive", "uart_send")
    assert status.capabilities == ("uart_receive", "uart_send")
    assert status.capability_policy is not None
    assert status.capability_policy.uart_send.tx_policy_enabled is True
    assert status.timestamp_provenance is not None
    assert status.timestamp_provenance.segment_id == 0
    assert status.timestamp_provenance.timestamp.source == "host"
    assert status.timestamp_provenance.timestamp.observation_point == "host_serial_read"
    assert status.integrity is not None
    assert status.integrity.loss_status == "not_observable"
    assert status.integrity.observation_scope is None

    config = parse_hardware_gpio_config(
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
    assert apply_startup_hardware_config(runtime, config) is False
    assert runtime.gpio_registry.get("CTRL0").state == "unconfigured"


def test_build_startup_runtime_recovers_sessions_before_opening_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = backend_settings(
        "basic",
        serial_port="/dev/ttyUSB0",
        baudrate=115200,
    )
    order: list[str] = []

    def fake_recover(store: SessionStore) -> SessionRecoveryResult:
        order.append("recover")
        return SessionRecoveryResult()

    def fake_open(received_settings: BackendSettings) -> BasicBackendConnection:
        assert received_settings == settings
        assert order == ["recover"]
        order.append("open")
        return BasicBackendConnection(serial_port=FakeSerial([]), settings=settings)

    monkeypatch.setattr(SessionStore, "recover_stale_sessions", fake_recover)
    monkeypatch.setattr(
        "dutchmate_service.startup.open_basic_backend_connection",
        fake_open,
    )

    build_startup_runtime(session_root=tmp_path, backend_settings=settings)

    assert order == ["recover", "open"]


def test_create_app_applies_startup_hardware_config_when_runtime_is_connected(
    tmp_path: Path,
) -> None:
    transport = FakeTransport([CommandSuccessMessage(timestamp_us=123)])
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(normalize_enhanced_hello(_hello(), port="/dev/ttyACM0"))
    config = parse_hardware_gpio_config(
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

    app = create_app(runtime, hardware_config=config)
    response = TestClient(app).get("/status")

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n'
    ]
    assert response.status_code == 200
    payload = response.json()
    assert payload["control_channels"]["CTRL0"]["state"] == "configured"
    assert payload["control_channels"]["CTRL0"]["role"] == "reset"
    assert payload["control_channels"]["CTRL0"]["source"] == "config"
    assert payload["control_channels"]["CTRL0"]["device_timestamp_us"] == 123


def test_rejected_startup_hardware_config_is_visible_in_status(tmp_path: Path) -> None:
    transport = FakeTransport(
        [CommandErrorMessage(error="hardware_fault", detail="CTRL0 cannot drive RESET_N")]
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(normalize_enhanced_hello(_hello(), port="/dev/ttyACM0"))
    config = parse_hardware_gpio_config(
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

    app = create_app(runtime, hardware_config=config)
    response = TestClient(app).get("/status")

    assert response.status_code == 200
    channel = response.json()["control_channels"]["CTRL0"]
    assert channel["state"] == "rejected"
    assert channel["role"] == "reset"
    assert channel["last_rejected"]["error"] == "hardware_fault"
    assert channel["last_rejected"]["detail"] == "CTRL0 cannot drive RESET_N"


def _hello() -> HelloMessage:
    return HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("gpio_control",),
    )
