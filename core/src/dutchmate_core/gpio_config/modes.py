"""GPIO role configuration state tracking."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias, cast

from dutchmate_core.device_connection.commands import (
    VALID_GPIO_CONTROL_CHANNELS,
    VALID_GPIO_LEVELS,
    VALID_GPIO_MODES,
    VALID_GPIO_ROLES,
)

GpioControlChannel: TypeAlias = Literal["CTRL0", "CTRL1", "CTRL2", "CTRL3"]
GpioRoleName: TypeAlias = Literal["reset", "boot"]
GpioControlMode: TypeAlias = Literal["open_drain", "push_pull"]
GpioLevel: TypeAlias = Literal["low", "high"]
GpioModeRequestSource: TypeAlias = Literal["config", "runtime"]
GpioModeState: TypeAlias = Literal["unconfigured", "configured", "rejected"]


class GpioConfigurationError(RuntimeError):
    """Raised when a GPIO-controlled workflow cannot run with current state."""


@dataclass(frozen=True, slots=True)
class GpioModeRejection:
    """Rejected GPIO role mode request."""

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
class GpioRoleState:
    """Current Device Core state for one configured GPIO role."""

    role: GpioRoleName
    state: GpioModeState
    channel: GpioControlChannel | None = None
    dut_signal: str | None = None
    mode: GpioControlMode | None = None
    active_level: GpioLevel | None = None
    idle_level: GpioLevel | None = None
    source: GpioModeRequestSource | None = None
    configured_at: str | None = None
    device_timestamp_us: int | None = None
    last_rejected: GpioModeRejection | None = None


class GpioModeRegistry:
    """Track accepted and rejected GPIO mode configuration per role."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or _utc_now
        self._states: dict[GpioRoleName, GpioRoleState] = {
            "reset": GpioRoleState(role="reset", state="unconfigured"),
            "boot": GpioRoleState(role="boot", state="unconfigured"),
        }

    def get(self, role: str) -> GpioRoleState:
        """Return the current state for a role."""

        role_name = _validate_role(role)
        return self._states[role_name]

    def snapshot(self) -> dict[GpioRoleName, GpioRoleState]:
        """Return current states for all controllable roles."""

        return dict(self._states)

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
    ) -> GpioRoleState:
        """Record a firmware-accepted GPIO role mode."""

        role_name = _validate_role(role)
        channel_name = _validate_channel(channel)
        dut_signal_name = _validate_dut_signal(dut_signal)
        mode_name = _validate_mode(mode)
        active_level_name = _validate_level(active_level, "active_level")
        idle_level_name = _validate_optional_level(idle_level, "idle_level")
        _validate_source(source)
        self._ensure_channel_available(channel=channel_name, role=role_name)

        state = GpioRoleState(
            role=role_name,
            state="configured",
            channel=channel_name,
            dut_signal=dut_signal_name,
            mode=mode_name,
            active_level=active_level_name,
            idle_level=idle_level_name,
            source=source,
            configured_at=_format_utc_timestamp(self._clock()),
            device_timestamp_us=device_timestamp_us,
        )
        self._states[role_name] = state
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
    ) -> GpioRoleState:
        """Record a firmware- or host-rejected GPIO role mode request."""

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

        current = self._states[role_name]
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
            state = GpioRoleState(
                role=current.role,
                state=current.state,
                channel=current.channel,
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
            state = GpioRoleState(
                role=role_name,
                state="rejected",
                last_rejected=rejection,
            )

        self._states[role_name] = state
        return state

    def require_configured(self, role: str) -> GpioRoleState:
        """Return configured role state or raise a workflow-facing error."""

        state = self.get(role)
        if state.state == "configured":
            return state
        if state.last_rejected is not None:
            raise GpioConfigurationError(state.last_rejected.detail)
        raise GpioConfigurationError(f"GPIO role '{role}' is not configured")

    def _ensure_channel_available(
        self,
        *,
        channel: GpioControlChannel,
        role: GpioRoleName,
    ) -> None:
        for current_role, state in self._states.items():
            if current_role == role or state.state != "configured":
                continue
            if state.channel == channel:
                raise ValueError(
                    f"GPIO channel '{channel}' is already assigned to role '{current_role}'"
                )


def _validate_role(role: str) -> GpioRoleName:
    if role not in VALID_GPIO_ROLES:
        raise ValueError("GPIO role must be 'reset' or 'boot'")
    return cast(GpioRoleName, role)


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
