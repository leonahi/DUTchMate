from fastapi.testclient import TestClient

from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.gpio_config.modes import GpioControlChannelState, GpioModeRegistry
from dutchmate_core.runtime import DeviceCoreRuntimeError, DeviceCoreStatus
from dutchmate_service.app import create_app


class FakeRuntime:
    def __init__(self, status: DeviceCoreStatus) -> None:
        self._status = status
        self.gpio_mode_requests: list[dict[str, object]] = []

    def status(self) -> DeviceCoreStatus:
        return self._status

    def configure_gpio_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        idle_level: str | None = None,
    ) -> GpioControlChannelState:
        self.gpio_mode_requests.append(
            {
                "role": role,
                "channel": channel,
                "dut_signal": dut_signal,
                "mode": mode,
                "active_level": active_level,
                "idle_level": idle_level,
            }
        )
        return GpioControlChannelState(
            channel="CTRL0",
            state="configured",
            role=role,
            dut_signal=dut_signal,
            mode="open_drain",
            active_level="low",
            source="runtime",
            device_timestamp_us=182334400,
        )


def test_status_returns_disconnected_runtime_state() -> None:
    registry = GpioModeRegistry()
    app = create_app(
        FakeRuntime(
            DeviceCoreStatus(
                connected=False,
                port="/dev/ttyACM0",
                firmware=None,
                device=None,
                capabilities=(),
                active_session_id=None,
                control_channels=registry.snapshot(),
            )
        )
    )

    response = TestClient(app).get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "port": "/dev/ttyACM0",
        "firmware": None,
        "device": None,
        "capabilities": [],
        "active_session_id": None,
        "control_channels": {
            "CTRL0": {
                "channel": "CTRL0",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL1": {
                "channel": "CTRL1",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL2": {
                "channel": "CTRL2",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL3": {
                "channel": "CTRL3",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
        },
    }


def test_status_returns_connected_gpio_mapping_state() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        device_timestamp_us=123,
    )
    hello = HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control"),
    )
    app = create_app(
        FakeRuntime(
            DeviceCoreStatus(
                connected=True,
                port="/dev/ttyACM0",
                firmware=hello.firmware,
                device=hello.device,
                capabilities=hello.capabilities,
                active_session_id="20260724T100000Z-abc12345",
                control_channels=registry.snapshot(),
            )
        )
    )

    response = TestClient(app).get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["firmware"] == "0.1.0"
    assert payload["device"] == "dutchmate-rp2040"
    assert payload["capabilities"] == ["uart_capture", "gpio_control"]
    assert payload["active_session_id"] == "20260724T100000Z-abc12345"
    assert payload["control_channels"]["CTRL0"]["state"] == "configured"
    assert payload["control_channels"]["CTRL0"]["role"] == "reset"
    assert payload["control_channels"]["CTRL0"]["dut_signal"] == "RESET_N"
    assert payload["control_channels"]["CTRL0"]["mode"] == "open_drain"
    assert payload["control_channels"]["CTRL0"]["source"] == "config"
    assert payload["control_channels"]["CTRL0"]["device_timestamp_us"] == 123


def test_configure_gpio_mode_calls_runtime_and_returns_accepted_mode() -> None:
    registry = GpioModeRegistry()
    runtime = FakeRuntime(
        DeviceCoreStatus(
            connected=True,
            port="/dev/ttyACM0",
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=("gpio_control",),
            active_session_id=None,
            control_channels=registry.snapshot(),
        )
    )
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 200
    assert runtime.gpio_mode_requests == [
        {
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
            "idle_level": None,
        }
    ]
    assert response.json() == {
        "ok": True,
        "channel": "CTRL0",
        "role": "reset",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
        "idle_level": None,
        "source": "runtime",
        "timestamp_us": 182334400,
    }


def test_configure_gpio_mode_passes_idle_level_for_push_pull_mapping() -> None:
    registry = GpioModeRegistry()
    runtime = FakeRuntime(
        DeviceCoreStatus(
            connected=True,
            port="/dev/ttyACM0",
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=("gpio_control",),
            active_session_id=None,
            control_channels=registry.snapshot(),
        )
    )
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL2",
            "role": "power_en",
            "dut_signal": "REG_EN",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        },
    )

    assert response.status_code == 200
    assert runtime.gpio_mode_requests == [
        {
            "channel": "CTRL2",
            "role": "power_en",
            "dut_signal": "REG_EN",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        }
    ]


def test_configure_gpio_mode_runtime_error_uses_service_error_contract() -> None:
    class DisconnectedRuntime(FakeRuntime):
        def configure_gpio_mode(
            self,
            *,
            role: str,
            channel: str,
            dut_signal: str,
            mode: str,
            active_level: str,
            idle_level: str | None = None,
        ) -> GpioControlChannelState:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    registry = GpioModeRegistry()
    runtime = DisconnectedRuntime(
        DeviceCoreStatus(
            connected=False,
            port="/dev/ttyACM0",
            firmware=None,
            device=None,
            capabilities=(),
            active_session_id=None,
            control_channels=registry.snapshot(),
        )
    )
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Debug Helper is not connected",
    }


def test_configure_gpio_mode_validation_error_uses_service_error_contract() -> None:
    registry = GpioModeRegistry()
    app = create_app(
        FakeRuntime(
            DeviceCoreStatus(
                connected=True,
                port="/dev/ttyACM0",
                firmware="0.1.0",
                device="dutchmate-rp2040",
                capabilities=("gpio_control",),
                active_session_id=None,
                control_channels=registry.snapshot(),
            )
        )
    )

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "GPIO0",
            "role": " ",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
    }
