import json

import pytest
from session_store_support import enhanced_snapshot

from dutchmate_core.backends import DutVioEvent
from dutchmate_core.dut_vio import DutVioSample
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.models import SessionPersistenceError, SessionQueryError
from dutchmate_core.session_store.store import SessionStore


def create(store):
    snapshot = enhanced_snapshot()
    profile = resolve_dut_profile(
        DutProfileConfig(), mode="enhanced", serial_port=snapshot.info.port
    )
    return store.create_v2_session(profile=profile, backend_snapshot=snapshot)


def observation(segment=0):
    return DutVioEvent(segment, 123, DutVioSample("ok", 2048, 3300, 3300, "nominal"), 2.5)


def test_vio_is_portable_durable_hardware_evidence_and_tail_data(tmp_path):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    cursor = store.read_evidence_page(
        cursor=None, tail_session_id=handle.session_id, limit=100
    ).next_cursor
    result = store.append_v2_dut_vio(handle, event=observation())
    record = json.loads(handle.paths.hardware_events.read_text())
    assert record["type"] == "dut_vio"
    assert record["adc_raw"] == 2048
    assert record["voltage_mv"] == 3300
    assert record["timestamp_us"] == 123
    assert "received_at_monotonic" not in record
    assert result.evidence_seq == record["evidence_seq"]
    page = store.read_evidence_page(cursor=cursor, tail_session_id=handle.session_id, limit=100)
    voltage = next(x for x in page.records if x["type"] == "dut_vio")
    assert voltage["voltage_mv"] == 3300
    assert voltage["adc_reference_mv"] == 3300
    assert store.get_session_detail(handle.session_id).summary.first_error is None


def test_vio_wrong_segment_is_rejected_without_writing(tmp_path):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    before = handle.paths.metadata.read_bytes()
    with pytest.raises(ValueError, match="segment"):
        store.append_v2_dut_vio(handle, event=observation(1))
    assert handle.paths.hardware_events.read_bytes() == b""
    assert handle.paths.metadata.read_bytes() == before


def test_vio_failed_append_rolls_back_whole_record(tmp_path, monkeypatch):
    import dutchmate_core.session_store.persistence as persistence

    store = SessionStore(root=tmp_path)
    handle = create(store)
    append = persistence.append_serialized

    def fail(path, data):
        append(path, data)
        if path == handle.paths.hardware_events:
            raise SessionPersistenceError(operation="append", path=path, detail="voltage failure")

    monkeypatch.setattr(persistence, "append_serialized", fail)
    with pytest.raises(SessionPersistenceError):
        store.append_v2_dut_vio(handle, event=observation())
    assert handle.paths.hardware_events.read_bytes() == b""


def test_vio_rollover_maps_record_into_successor_segment(tmp_path, monkeypatch):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    original = store._v2_unit_fits

    def fits(metadata, *, unit_bytes):
        if metadata["session_id"] == handle.session_id:
            return False
        return original(metadata, unit_bytes=unit_bytes)

    monkeypatch.setattr(store, "_v2_unit_fits", fits)
    result = store.append_v2_dut_vio(handle, event=observation())
    assert result.rolled_over
    assert result.handle.session_id != handle.session_id
    record = json.loads(result.handle.paths.hardware_events.read_text())
    assert record["segment_id"] == 0
    assert record["voltage_mv"] == 3300
    assert record["evidence_seq"] == result.evidence_seq


@pytest.mark.parametrize(
    "changes", [{"voltage_mv": 3301}, {"reference_source": []}, {"status": {}}]
)
def test_reader_rejects_corrupt_known_voltage_record(tmp_path, changes):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    store.append_v2_dut_vio(handle, event=observation())
    record = json.loads(handle.paths.hardware_events.read_text())
    record.update(changes)
    handle.paths.hardware_events.write_text(json.dumps(record) + "\n")
    with pytest.raises(SessionQueryError):
        store.get_session_detail(handle.session_id)


def test_vio_record_survives_stale_session_recovery(tmp_path):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    store.append_v2_dut_vio(handle, event=observation())
    before = handle.paths.hardware_events.read_bytes()
    restarted = SessionStore(root=tmp_path)
    restarted.recover_stale_sessions()
    assert restarted.get_session_detail(handle.session_id).summary.state == "abandoned"
    assert handle.paths.hardware_events.read_bytes() == before


def test_vio_record_never_partially_persists_when_successor_creation_fails(tmp_path, monkeypatch):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    original = store._v2_unit_fits

    def fits(metadata, *, unit_bytes):
        return metadata["session_id"] != handle.session_id and original(
            metadata, unit_bytes=unit_bytes
        )

    def cannot_create(**kwargs):
        raise SessionPersistenceError(
            operation="create", path=tmp_path, detail="disk quota exhausted"
        )

    monkeypatch.setattr(store, "_v2_unit_fits", fits)
    monkeypatch.setattr(store, "_create_v2_session_locked", cannot_create)
    with pytest.raises(SessionPersistenceError):
        store.append_v2_dut_vio(handle, event=observation())
    assert all(path.read_bytes() == b"" for path in tmp_path.glob("*/hardware_events.jsonl"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp_us", None),
        ("timestamp_us", False),
        ("timestamp_us", -1),
        ("segment_id", None),
        ("segment_id", True),
        ("segment_id", -1),
        ("segment_id", 42),
    ],
)
def test_tail_rejects_invalid_voltage_provenance(tmp_path, field, value):
    store = SessionStore(root=tmp_path)
    handle = create(store)
    cursor = store.read_evidence_page(
        cursor=None, tail_session_id=handle.session_id, limit=100
    ).next_cursor
    store.append_v2_dut_vio(handle, event=observation())
    record = json.loads(handle.paths.hardware_events.read_text())
    if value is None:
        del record[field]
    else:
        record[field] = value
    handle.paths.hardware_events.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError, match="DUT VIO"):
        store.read_evidence_page(cursor=cursor, tail_session_id=handle.session_id, limit=100)
