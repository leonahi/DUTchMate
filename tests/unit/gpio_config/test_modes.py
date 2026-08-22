from datetime import datetime, timezone

import pytest

from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRejection,
)


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def test_channels_start_unconfigured() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    assert registry.get("CTRL0") == GpioControlChannelState(
        channel="CTRL0",
        state="unconfigured",
    )
    assert registry.get("CTRL3") == GpioControlChannelState(
        channel="CTRL3",
        state="unconfigured",
    )


def test_accept_mode_marks_channel_configured_with_role_metadata() -> None:
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

    assert state == GpioControlChannelState(
        channel="CTRL0",
        state="configured",
        role="reset",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        configured_at="2026-07-14T12:30:45Z",
        device_timestamp_us=1234,
    )
    assert registry.get("CTRL0") == state
    assert registry.find_by_role("reset") == state


def test_accept_mode_can_record_custom_role_and_idle_level() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    state = registry.accept_mode(
        role="power_en",
        channel="CTRL2",
        dut_signal="REG_EN",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="config",
    )

    assert state.role == "power_en"
    assert state.idle_level == "low"
    assert registry.find_by_role("power_en") == state


def test_runtime_accept_moves_role_to_new_channel() -> None:
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

    assert registry.get("CTRL0").state == "unconfigured"
    assert state.state == "configured"
    assert state.channel == "CTRL2"
    assert state.role == "reset"
    assert state.dut_signal == "NRST"
    assert state.mode == "push_pull"
    assert state.idle_level == "high"
    assert state.source == "runtime"


def test_reconfiguring_same_channel_replaces_role_metadata() -> None:
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
        role="wake",
        channel="CTRL0",
        dut_signal="WAKE_N",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="runtime",
    )

    assert state.role == "wake"
    assert state.dut_signal == "WAKE_N"
    assert registry.find_by_role("reset") is None
    assert registry.find_by_role("wake") == state


def test_rejection_without_previous_accept_marks_channel_rejected() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    state = registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="config",
        error="invalid_argument",
        detail="push_pull is not supported for reset",
        device_timestamp_us=200,
    )

    assert state == GpioControlChannelState(
        channel="CTRL0",
        state="rejected",
        role="reset",
        last_rejected=GpioModeRejection(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="push_pull",
            active_level="low",
            idle_level="high",
            source="config",
            error="invalid_argument",
            detail="push_pull is not supported for reset",
            rejected_at="2026-07-14T12:30:45Z",
            device_timestamp_us=200,
        ),
    )


def test_rejected_runtime_override_preserves_previous_accepted_channel_state() -> None:
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
    assert state.role == "reset"
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
        idle_level="high",
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


def test_require_role_configured_returns_configured_state() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    configured = registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert registry.require_role_configured("reset") == configured


def test_require_role_configured_rejects_unconfigured_role() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)

    with pytest.raises(GpioConfigurationError, match="not configured") as exc_info:
        registry.require_role_configured("reset", operation="boot_test")

    assert exc_info.value.operation == "boot_test"
    assert exc_info.value.required_role == "reset"
    assert exc_info.value.role_state == "unconfigured"


def test_require_role_configured_uses_rejection_detail_for_rejected_role() -> None:
    registry = GpioModeRegistry(clock=fixed_clock)
    registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
        error="invalid_argument",
        detail="unsupported reset mode",
    )

    with pytest.raises(GpioConfigurationError, match="unsupported reset mode") as exc_info:
        registry.require_role_configured("reset", operation="reset")

    assert exc_info.value.operation == "reset"
    assert exc_info.value.required_role == "reset"
    assert exc_info.value.role_state == "rejected"


def test_snapshot_returns_all_channel_states() -> None:
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
        "CTRL0": GpioControlChannelState(
            channel="CTRL0",
            state="configured",
            role="reset",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
            configured_at="2026-07-14T12:30:45Z",
        ),
        "CTRL1": GpioControlChannelState(channel="CTRL1", state="unconfigured"),
        "CTRL2": GpioControlChannelState(channel="CTRL2", state="unconfigured"),
        "CTRL3": GpioControlChannelState(channel="CTRL3", state="unconfigured"),
    }


@pytest.mark.parametrize("role", ["", "   "])
def test_rejects_empty_role(role: str) -> None:
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
