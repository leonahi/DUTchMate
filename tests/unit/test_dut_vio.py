import pytest

from dutchmate_core.dut_vio import DutVioSample


@pytest.mark.parametrize("raw,mv", [(0, 0), (1024, 1650), (2048, 3300), (3072, 4950), (4094, 6597)])
def test_vio_sample_validates_exact_divider_conversion(raw, mv):
    from dutchmate_core.dut_vio import DutVioSample

    sample = DutVioSample("ok", raw, mv, 3300, "nominal")
    assert sample.adc_raw == raw
    assert sample.voltage_mv == mv
    with pytest.raises(ValueError):
        DutVioSample("ok", raw, mv + 1, 3300, "nominal")


@pytest.mark.parametrize(
    "values",
    [
        ("ok", True, 2, 3300, "nominal"),
        ("ok", 2048, True, 3300, "nominal"),
        ("ok", 2048, 3300, True, "nominal"),
        ("ok", -1, 0, 3300, "nominal"),
        ("ok", 4095, 6598, 3300, "nominal"),
        ("ok", 2048, 2499, 2499, "measured"),
        ("ok", 2048, 3601, 3601, "measured"),
        ("ok", 2048, 3300, 3300, "estimated"),
        ("adc_error", 0, 0, 3300, "nominal"),
        ("saturated", 4094, None, 3300, "nominal"),
        ("saturated", 4095, 6600, 3300, "nominal"),
    ],
)
def test_vio_sample_rejects_invalid_or_inconsistent_measurement(values):
    from dutchmate_core.dut_vio import DutVioSample

    with pytest.raises(ValueError):
        DutVioSample(*values)


@pytest.mark.parametrize(
    "values",
    [
        ("adc_error", None, None, 3300, "nominal"),
        ("saturated", 4095, None, 3277, "measured"),
        ("ok", 2048, 3277, 3277, "measured"),
    ],
)
def test_vio_sample_retains_error_and_reference_provenance(values):
    from dutchmate_core.dut_vio import DutVioSample

    sample = DutVioSample(*values)
    assert (
        sample.status,
        sample.adc_raw,
        sample.voltage_mv,
        sample.adc_reference_mv,
        sample.reference_source,
    ) == values


@pytest.mark.parametrize("age_ms,state", [(0, "valid"), (3000, "valid"), (3001, "stale")])
@pytest.mark.parametrize("raw", [0, 2048, 3500])
def test_status_receipt_age_and_exact_nullability(age_ms, state, raw):
    from dataclasses import asdict

    from dutchmate_core.dut_vio import DutVioObservation, project_dut_vio_status

    sample = DutVioSample("ok", raw, (raw * 6600 + 2048) // 4096, 3300, "nominal")
    observation = DutVioObservation(sample, 100, 0.0, "session", 2, 4)
    result = asdict(
        project_dut_vio_status(
            connection_state="connected",
            capable=True,
            setup_rejected=False,
            observation=observation,
            now_monotonic=age_ms / 1000,
        )
    )
    assert set(result) == {"state", "reason", "voltage_mv", "age_ms", "sample", "evidence"}
    assert result["state"] == state
    assert result["age_ms"] == age_ms
    assert result["voltage_mv"] == (sample.voltage_mv if state == "valid" else None)
    assert result["sample"] == {"type": "dut_vio", "timestamp_us": 100, **asdict(sample)}
    assert result["evidence"] == {"session_id": "session", "segment_id": 2, "evidence_seq": 4}


@pytest.mark.parametrize(
    "connection", ["disconnected", "released", "reconnecting", "reacquiring", "faulted"]
)
def test_disconnected_status_clears_all_voltage_fields(connection):
    from dutchmate_core.dut_vio import DutVioObservation, project_dut_vio_status

    observation = DutVioObservation(DutVioSample("ok", 0, 0, 3300, "measured"), 1, 0.0, "s", 0, 1)
    result = project_dut_vio_status(
        connection_state=connection,
        capable=False,
        setup_rejected=True,
        observation=observation,
        now_monotonic=100.0,
    )
    assert (result.state, result.reason) == ("unavailable", connection)
    assert result.sample is result.evidence is result.age_ms is result.voltage_mv is None


@pytest.mark.parametrize("status,raw", [("adc_error", None), ("saturated", 4095)])
def test_adc_failure_reason_persists_beyond_receipt_timeout(status, raw):
    from dutchmate_core.dut_vio import DutVioObservation, project_dut_vio_status

    observation = DutVioObservation(
        DutVioSample(status, raw, None, 3300, "nominal"), 1, 0.0, "s", 0, 1
    )
    result = project_dut_vio_status(
        connection_state="connected",
        capable=True,
        setup_rejected=False,
        observation=observation,
        now_monotonic=100.0,
    )
    assert (result.state, result.reason, result.voltage_mv) == ("unavailable", status, None)
    assert result.sample.status == status


@pytest.mark.parametrize(
    "capable,rejected,state,reason",
    [
        (False, False, "unsupported", "capability_missing"),
        (True, False, "unavailable", "awaiting_sample"),
        (True, True, "unavailable", "setup_rejected"),
    ],
)
def test_voltage_setup_status(capable, rejected, state, reason):
    from dutchmate_core.dut_vio import project_dut_vio_status

    result = project_dut_vio_status(
        connection_state="connected",
        capable=capable,
        setup_rejected=rejected,
        observation=None,
        now_monotonic=0.0,
    )
    assert (result.state, result.reason) == (state, reason)
