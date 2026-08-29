import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, disconnected_status

from dutchmate_core.gpio_config.config import HardwareGpioConfig, parse_hardware_gpio_config
from dutchmate_service import app as app_module


class ClosableFakeRuntime(FakeRuntime):
    def __init__(self, *, close_error: Exception | None = None) -> None:
        super().__init__(disconnected_status())
        self.close_count = 0
        self._close_error = close_error

    def close(self) -> None:
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


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
