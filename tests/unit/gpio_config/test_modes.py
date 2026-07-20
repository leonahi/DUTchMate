from datetime import datetime, timezone

import pytest

from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioModeRegistry,
    GpioModeRejection,
    GpioRoleState,
)


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def test_roles_start_unconfigured() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    assert registry.get("reset") == GpioRoleState(role="reset", state="unconfigured")
    assert registry.get("boot") == GpioRoleState(role="boot", state="unconfigured")


def test_accept_mode_marks_role_configured() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    state = registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        device_timestamp_us=1234,
    )

    assert state == GpioRoleState(
        role="reset",
        state="configured",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        configured_at="2026-07-14T12:30:45Z",
        device_timestamp_us=1234,
    )
    assert registry.get("reset") == state


def test_accept_mode_can_record_idle_level() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    state = registry.accept_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="config",
    )

    assert state.idle_level == "low"


def test_runtime_accept_replaces_previous_config_for_same_role() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
    )

    state = registry.accept_mode(
        role="reset",
        channel="CTRL2",
        dut_signal="NRST",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
    )

    assert state.state == "configured"
    assert state.channel == "CTRL2"
    assert state.dut_signal == "NRST"
    assert state.mode == "push_pull"
    assert state.idle_level == "high"
    assert state.source == "runtime"
    assert state.last_rejected is None


def test_accept_mode_rejects_duplicate_configured_channel() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
    )

    with pytest.raises(ValueError, match="already assigned"):
        registry.accept_mode(
            role="boot",
            channel="CTRL0",
            dut_signal="BOOT0",
            mode="push_pull",
            active_level="high",
            source="config",
        )


def test_rejection_without_previous_accept_marks_role_rejected() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    state = registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        source="config",
        error="invalid_argument",
        detail="push_pull is not supported for reset",
        device_timestamp_us=200,
    )

    assert state == GpioRoleState(
        role="reset",
        state="rejected",
        last_rejected=GpioModeRejection(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="push_pull",
            active_level="low",
            source="config",
            error="invalid_argument",
            detail="push_pull is not supported for reset",
            rejected_at="2026-07-14T12:30:45Z",
            device_timestamp_us=200,
        ),
    )


def test_rejected_runtime_override_preserves_previous_accepted_mode() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        device_timestamp_us=100,
    )

    state = registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
        error="invalid_argument",
        detail="push_pull is not supported for reset",
        device_timestamp_us=200,
    )

    assert state.state == "configured"
    assert state.channel == "CTRL0"
    assert state.dut_signal == "RESET_N"
    assert state.mode == "open_drain"
    assert state.source == "config"
    assert state.configured_at == "2026-07-14T12:30:45Z"
    assert state.device_timestamp_us == 100
    assert state.last_rejected == GpioModeRejection(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
        error="invalid_argument",
        detail="push_pull is not supported for reset",
        rejected_at="2026-07-14T12:30:45Z",
        device_timestamp_us=200,
    )


def test_later_accept_clears_previous_rejection() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        source="runtime",
        error="invalid_argument",
        detail="unsupported",
    )

    state = registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert state.state == "configured"
    assert state.last_rejected is None


def test_require_configured_returns_configured_state() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    configured = registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert registry.require_configured("reset") == configured


def test_require_configured_rejects_unconfigured_role() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(GpioConfigurationError, match="not configured"):
        registry.require_configured("reset")


def test_require_configured_uses_rejection_detail_for_rejected_role() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        source="runtime",
        error="invalid_argument",
        detail="unsupported reset mode",
    )

    with pytest.raises(GpioConfigurationError, match="unsupported reset mode"):
        registry.require_configured("reset")


def test_snapshot_returns_all_role_states() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert registry.snapshot() == {
        "reset": GpioRoleState(
            role="reset",
            state="configured",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
            configured_at="2026-07-14T12:30:45Z",
        ),
        "boot": GpioRoleState(role="boot", state="unconfigured"),
    }


@pytest.mark.parametrize("role", ["power", "", "RESET"])
def test_rejects_unknown_role(role: str) -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role=role,
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )


@pytest.mark.parametrize("channel", ["GPIO0", "", "ctrl0"])
def test_rejects_unknown_channel(channel: str) -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel=channel,
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )


@pytest.mark.parametrize("dut_signal", ["", "   "])
def test_rejects_empty_dut_signal(dut_signal: str) -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel="CTRL0",
            dut_signal=dut_signal,
            mode="open_drain",
            active_level="low",
            source="runtime",
        )


@pytest.mark.parametrize("mode", ["hi_z", "", "OPEN_DRAIN"])
def test_rejects_unknown_mode(mode: str) -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode=mode,
            active_level="low",
            source="runtime",
        )


@pytest.mark.parametrize("level", ["asserted", "", "LOW"])
def test_rejects_unknown_active_level(level: str) -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level=level,
            source="runtime",
        )


def test_rejects_unknown_idle_level() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            idle_level="released",
            source="runtime",
        )


def test_rejects_unknown_source() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.accept_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="service",  # type: ignore[arg-type]
        )


def test_rejection_requires_error_and_detail() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(ValueError):
        registry.reject_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
            error="",
            detail="detail",
        )
    with pytest.raises(ValueError):
        registry.reject_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
            error="invalid_argument",
            detail="",
        )
