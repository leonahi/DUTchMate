"""GPIO role configuration state tracking."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias, cast

from dutchmate_core.device_connection.commands import (
    VALID_GPIO_CONTROL_CHANNELS,
    VALID_GPIO_LEVELS,
    VALID_GPIO_MODES,
)

GpioControlChannel: TypeAlias = Literal["CTRL0", "CTRL1", "CTRL2", "CTRL3"]
GpioRoleName: TypeAlias = str
GpioControlMode: TypeAlias = Literal["open_drain", "push_pull"]
GpioLevel: TypeAlias = Literal["low", "high"]
GpioModeRequestSource: TypeAlias = Literal["config", "runtime"]
GpioModeState: TypeAlias = Literal["unconfigured", "configured", "rejected"]
ALL_CONTROL_CHANNELS: tuple[GpioControlChannel, ...] = ("CTRL0", "CTRL1", "CTRL2", "CTRL3")


class GpioConfigurationError(RuntimeError):
    """Raised when a GPIO-controlled workflow cannot run with current state."""


@dataclass(frozen=True, slots=True)
class GpioModeRejection:
    """Rejected GPIO channel mode request."""

    role: GpioRoleName
    channel: GpioControlChannel
    dut_signal: str
    mode: GpioControlMode
    active_level: GpioLevel
    source: GpioModeRequestSource
    error: str
    detail: str
    rejected_at: str
    idle_level: GpioLevel | None = None
    device_timestamp_us: int | None = None


@dataclass(frozen=True, slots=True)
class GpioControlChannelState:
    """Current Device Core state for one physical control channel."""

    channel: GpioControlChannel
    state: GpioModeState
    role: GpioRoleName | None = None
    dut_signal: str | None = None
    mode: GpioControlMode | None = None
    active_level: GpioLevel | None = None
    idle_level: GpioLevel | None = None
    source: GpioModeRequestSource | None = None
    configured_at: str | None = None
    device_timestamp_us: int | None = None
    last_rejected: GpioModeRejection | None = None


GpioRoleState: TypeAlias = GpioControlChannelState


class GpioModeRegistry:
    """Track accepted and rejected GPIO mode configuration per control channel."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or _utc_now
        self._states: dict[GpioControlChannel, GpioControlChannelState] = {
            channel: GpioControlChannelState(channel=channel, state="unconfigured")
            for channel in ALL_CONTROL_CHANNELS
        }

    def get(self, channel: str) -> GpioControlChannelState:
        """Return the current state for a physical control channel."""

        channel_name = _validate_channel(channel)
        return self._states[channel_name]

    def snapshot(self) -> dict[GpioControlChannel, GpioControlChannelState]:
        """Return current states for all physical control channels."""

        return dict(self._states)

    def find_by_role(self, role: str) -> GpioControlChannelState | None:
        """Return the configured channel state for a role, if one exists."""

        role_name = _validate_role(role)
        for state in self._states.values():
            if state.role == role_name and state.state == "configured":
                return state
        return None

    def accept_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        source: GpioModeRequestSource,
        idle_level: str | None = None,
        device_timestamp_us: int | None = None,
    ) -> GpioControlChannelState:
        """Record a firmware-accepted GPIO control channel mode."""

        role_name = _validate_role(role)
        channel_name = _validate_channel(channel)
        dut_signal_name = _validate_dut_signal(dut_signal)
        mode_name = _validate_mode(mode)
        active_level_name = _validate_level(active_level, "active_level")
        idle_level_name = _validate_optional_level(idle_level, "idle_level")
        _validate_source(source)
        self._clear_role_from_other_channels(role=role_name, channel=channel_name)

        state = GpioControlChannelState(
            channel=channel_name,
            state="configured",
            role=role_name,
            dut_signal=dut_signal_name,
            mode=mode_name,
            active_level=active_level_name,
            idle_level=idle_level_name,
            source=source,
            configured_at=_format_utc_timestamp(self._clock()),
            device_timestamp_us=device_timestamp_us,
        )
        self._states[channel_name] = state
        return state

    def reject_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        source: GpioModeRequestSource,
        error: str,
        detail: str,
        idle_level: str | None = None,
        device_timestamp_us: int | None = None,
    ) -> GpioControlChannelState:
        """Record a firmware- or host-rejected GPIO control channel mode request."""

        role_name = _validate_role(role)
        channel_name = _validate_channel(channel)
        dut_signal_name = _validate_dut_signal(dut_signal)
        mode_name = _validate_mode(mode)
        active_level_name = _validate_level(active_level, "active_level")
        idle_level_name = _validate_optional_level(idle_level, "idle_level")
        _validate_source(source)
        if not error:
            raise ValueError("GPIO mode rejection error must not be empty")
        if not detail:
            raise ValueError("GPIO mode rejection detail must not be empty")

        current = self._states[channel_name]
        rejection = GpioModeRejection(
            role=role_name,
            channel=channel_name,
            dut_signal=dut_signal_name,
            mode=mode_name,
            active_level=active_level_name,
            idle_level=idle_level_name,
            source=source,
            error=error,
            detail=detail,
            rejected_at=_format_utc_timestamp(self._clock()),
            device_timestamp_us=device_timestamp_us,
        )

        if current.state == "configured":
            state = GpioControlChannelState(
                channel=current.channel,
                state=current.state,
                role=current.role,
                dut_signal=current.dut_signal,
                mode=current.mode,
                active_level=current.active_level,
                idle_level=current.idle_level,
                source=current.source,
                configured_at=current.configured_at,
                device_timestamp_us=current.device_timestamp_us,
                last_rejected=rejection,
            )
        else:
            state = GpioControlChannelState(
                channel=channel_name,
                state="rejected",
                role=role_name,
                last_rejected=rejection,
            )

        self._states[channel_name] = state
        return state

    def require_role_configured(self, role: str) -> GpioControlChannelState:
        """Return configured channel state for a role or raise a workflow-facing error."""

        role_name = _validate_role(role)
        state = self.find_by_role(role_name)
        if state is not None:
            return state
        rejection = self._latest_rejection_for_role(role_name)
        if rejection is not None:
            raise GpioConfigurationError(rejection.detail)
        raise GpioConfigurationError(f"GPIO role '{role_name}' is not configured")

    def require_configured(self, role: str) -> GpioControlChannelState:
        """Return configured channel state for a role.

        Kept as a compatibility wrapper for existing reset/boot workflow code.
        """

        return self.require_role_configured(role)

    def _clear_role_from_other_channels(
        self,
        *,
        role: GpioRoleName,
        channel: GpioControlChannel,
    ) -> None:
        for current_channel, state in list(self._states.items()):
            if current_channel == channel or state.role != role:
                continue
            self._states[current_channel] = GpioControlChannelState(
                channel=current_channel,
                state="unconfigured",
            )

    def _latest_rejection_for_role(self, role: GpioRoleName) -> GpioModeRejection | None:
        latest: GpioModeRejection | None = None
        for state in self._states.values():
            rejection = state.last_rejected
            if rejection is None or rejection.role != role:
                continue
            latest = rejection
        return latest


def _validate_role(role: str) -> GpioRoleName:
    if not isinstance(role, str) or not role.strip():
        raise ValueError("GPIO role must be a non-empty string")
    return role.strip()


def _validate_channel(channel: str) -> GpioControlChannel:
    if channel not in VALID_GPIO_CONTROL_CHANNELS:
        raise ValueError("GPIO control channel must be 'CTRL0', 'CTRL1', 'CTRL2', or 'CTRL3'")
    return cast(GpioControlChannel, channel)


def _validate_dut_signal(dut_signal: str) -> str:
    if not isinstance(dut_signal, str) or not dut_signal.strip():
        raise ValueError("GPIO dut_signal must be a non-empty string")
    return dut_signal


def _validate_mode(mode: str) -> GpioControlMode:
    if mode not in VALID_GPIO_MODES:
        raise ValueError("GPIO mode must be 'open_drain' or 'push_pull'")
    return cast(GpioControlMode, mode)


def _validate_level(level: str, field_name: str) -> GpioLevel:
    if level not in VALID_GPIO_LEVELS:
        raise ValueError(f"GPIO {field_name} must be 'low' or 'high'")
    return cast(GpioLevel, level)


def _validate_optional_level(level: str | None, field_name: str) -> GpioLevel | None:
    if level is None:
        return None
    return _validate_level(level, field_name)


def _validate_source(source: str) -> None:
    if source not in {"config", "runtime"}:
        raise ValueError("GPIO mode source must be 'config' or 'runtime'")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
