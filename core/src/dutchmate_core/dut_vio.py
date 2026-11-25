"""Immutable report-only DUT interface-voltage observations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Literal, cast

VioSampleState = Literal["ok", "adc_error", "saturated"]
VioReferenceSource = Literal["nominal", "measured"]


@dataclass(frozen=True, slots=True)
class DutVioSample:
    """An ADC observation with explicit reference provenance and exact scaling."""

    status: VioSampleState
    adc_raw: int | None
    voltage_mv: int | None
    adc_reference_mv: int
    reference_source: VioReferenceSource

    @classmethod
    def from_fields(cls, fields: Mapping[str, object]) -> DutVioSample:
        """Validate the shared measurement fields in a wire or evidence record."""
        try:
            return cls(
                cast(VioSampleState, fields["status"]),
                cast(int | None, fields["adc_raw"]),
                cast(int | None, fields["voltage_mv"]),
                cast(int, fields["adc_reference_mv"]),
                cast(VioReferenceSource, fields["reference_source"]),
            )
        except KeyError as exc:
            raise ValueError("DUT VIO measurement field is missing") from exc

    def __post_init__(self) -> None:
        if type(self.adc_reference_mv) is not int or not 2500 <= self.adc_reference_mv <= 3600:
            raise ValueError("ADC reference must be an integer in 2500..3600 mV")
        if self.reference_source not in ("nominal", "measured"):
            raise ValueError("ADC reference source must be nominal or measured")
        if self.status == "adc_error":
            if self.adc_raw is not None or self.voltage_mv is not None:
                raise ValueError("ADC error cannot contain a voltage or ADC code")
        elif self.status == "saturated":
            if type(self.adc_raw) is not int or self.adc_raw != 4095 or self.voltage_mv is not None:
                raise ValueError("Saturated ADC observation must have code 4095 and no voltage")
        elif self.status == "ok":
            if type(self.adc_raw) is not int or not 0 <= self.adc_raw < 4095:
                raise ValueError("Successful ADC code must be an integer in 0..4094")
            expected = (self.adc_raw * self.adc_reference_mv * 2 + 2048) // 4096
            if type(self.voltage_mv) is not int or self.voltage_mv != expected:
                raise ValueError("DUT VIO voltage does not match ADC/reference conversion")
        else:
            raise ValueError("Unknown DUT VIO observation status")


@dataclass(frozen=True, slots=True)
class DutVioObservation:
    """An admitted observation tied to durable evidence and its original receipt."""

    sample: DutVioSample
    timestamp_us: int
    received_at_monotonic: float
    session_id: str
    segment_id: int
    evidence_seq: int


@dataclass(frozen=True, slots=True)
class DutVioStatusSample(DutVioSample):
    """Portable fields of the most recent durably admitted observation."""

    timestamp_us: int
    type: Literal["dut_vio"] = "dut_vio"


@dataclass(frozen=True, slots=True)
class DutVioEvidence:
    session_id: str
    segment_id: int
    evidence_seq: int


@dataclass(frozen=True, slots=True)
class DutVioStatus:
    state: Literal["valid", "stale", "unsupported", "unavailable"] = "unavailable"
    reason: str | None = "disconnected"
    voltage_mv: int | None = None
    age_ms: int | None = None
    sample: DutVioStatusSample | None = None
    evidence: DutVioEvidence | None = None


def project_dut_vio_status(
    *,
    connection_state: str,
    capable: bool,
    setup_rejected: bool,
    observation: DutVioObservation | None,
    now_monotonic: float,
) -> DutVioStatus:
    """Project report-only state using receipt age and connection-first precedence."""
    if connection_state != "connected":
        reason = (
            connection_state
            if connection_state
            in ("disconnected", "reconnecting", "released", "reacquiring", "faulted")
            else "disconnected"
        )
        return DutVioStatus(reason=reason)
    if not capable:
        return DutVioStatus(state="unsupported", reason="capability_missing")
    if setup_rejected:
        return DutVioStatus(reason="setup_rejected")
    if observation is None:
        return DutVioStatus(reason="awaiting_sample")
    age_ms = max(0, int((now_monotonic - observation.received_at_monotonic) * 1000))
    sample = DutVioStatusSample(timestamp_us=observation.timestamp_us, **asdict(observation.sample))
    evidence = DutVioEvidence(
        observation.session_id, observation.segment_id, observation.evidence_seq
    )
    if sample.status != "ok":
        return DutVioStatus(reason=sample.status, age_ms=age_ms, sample=sample, evidence=evidence)
    if age_ms > 3000:
        return DutVioStatus(
            state="stale", reason="sample_timeout", age_ms=age_ms, sample=sample, evidence=evidence
        )
    return DutVioStatus(
        state="valid",
        reason=None,
        voltage_mv=sample.voltage_mv,
        age_ms=age_ms,
        sample=sample,
        evidence=evidence,
    )
