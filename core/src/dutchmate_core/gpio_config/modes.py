"""GPIO role configuration state tracking."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from dutchmate_core.validation import (
    ALL_CONTROL_CHANNELS,
    validate_gpio_channel,
    validate_gpio_configuration,
    validate_gpio_role,
    validate_gpio_source,
)
from dutchmate_core.validation import (
    GpioControlChannel as GpioControlChannel,
)
from dutchmate_core.validation import (
    GpioControlMode as GpioControlMode,
)
from dutchmate_core.validation import (
    GpioLevel as GpioLevel,
)
from dutchmate_core.validation import (
    GpioModeRequestSource as GpioModeRequestSource,
)
from dutchmate_core.validation import (
    GpioRoleName as GpioRoleName,
)

GpioModeState: TypeAlias = Literal["unconfigured", "configured", "rejected"]
GpioRoleRequirementState: TypeAlias = Literal["unconfigured", "rejected"]


class GpioConfigurationError(RuntimeError):
    """Raised when a GPIO-controlled workflow cannot run with current state."""

    def __init__(
        self,
        detail: str,
        *,
        operation: str | None = None,
        required_role: GpioRoleName | None = None,
        role_state: GpioRoleRequirementState | None = None,
    ) -> None:
        super().__init__(detail)
        self.operation = operation
        self.required_role = required_role
        self.role_state = role_state


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

        channel_name = validate_gpio_channel(channel)
        return self._states[channel_name]

    def snapshot(self) -> dict[GpioControlChannel, GpioControlChannelState]:
        """Return current states for all physical control channels."""

        return dict(self._states)

    def find_by_role(self, role: str) -> GpioControlChannelState | None:
        """Return the configured channel state for a role, if one exists."""

        role_name = validate_gpio_role(role)
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

        request = validate_gpio_configuration(
            role=role,
            channel=channel,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        source_name = validate_gpio_source(source)
        self._clear_role_from_other_channels(role=request.role, channel=request.channel)

        state = GpioControlChannelState(
            channel=request.channel,
            state="configured",
            role=request.role,
            dut_signal=request.dut_signal,
            mode=request.mode,
            active_level=request.active_level,
            idle_level=request.idle_level,
            source=source_name,
            configured_at=_format_utc_timestamp(self._clock()),
            device_timestamp_us=device_timestamp_us,
        )
        self._states[request.channel] = state
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

        request = validate_gpio_configuration(
            role=role,
            channel=channel,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        source_name = validate_gpio_source(source)
        if not error:
            raise ValueError("GPIO mode rejection error must not be empty")
        if not detail:
            raise ValueError("GPIO mode rejection detail must not be empty")

        current = self._states[request.channel]
        rejection = GpioModeRejection(
            role=request.role,
            channel=request.channel,
            dut_signal=request.dut_signal,
            mode=request.mode,
            active_level=request.active_level,
            idle_level=request.idle_level,
            source=source_name,
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
                channel=request.channel,
                state="rejected",
                role=request.role,
                last_rejected=rejection,
            )

        self._states[request.channel] = state
        return state

    def require_role_configured(
        self,
        role: str,
        *,
        operation: str | None = None,
    ) -> GpioControlChannelState:
        """Return configured channel state for a role or raise a workflow-facing error."""

        role_name = validate_gpio_role(role)
        state = self.find_by_role(role_name)
        if state is not None:
            return state
        rejection = self._latest_rejection_for_role(role_name)
        if rejection is not None:
            raise GpioConfigurationError(
                rejection.detail,
                operation=operation,
                required_role=role_name,
                role_state="rejected",
            )
        raise GpioConfigurationError(
            f"GPIO role '{role_name}' is not configured",
            operation=operation,
            required_role=role_name,
            role_state="unconfigured",
        )

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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
