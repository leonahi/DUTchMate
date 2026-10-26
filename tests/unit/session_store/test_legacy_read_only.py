"""Legacy evidence must survive startup and public lifecycle calls unchanged."""

from pathlib import Path

import pytest
from legacy_session_fixtures import LegacySessionFixtureBuilder
from session_store_support import enhanced_snapshot

from dutchmate_core.session_store.store import SessionStore


def legacy_session(root: Path):
    return LegacySessionFixtureBuilder(root=root).create_session(
        command="capture --seconds 1",
        workflow="capture",
        duration_s=1,
        reconnect_timeout_s=5,
        backend_snapshot=enhanced_snapshot(),
    )


def snapshot(root: Path):
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}


def test_startup_does_not_recover_or_change_schema_v1(tmp_path):
    handle = legacy_session(tmp_path)
    assert (
        SessionStore(root=tmp_path).get_session_detail(handle.session_id).summary.state == "active"
    )
    # Even obsolete crash bookkeeping is compatibility evidence, not recovery work.
    (handle.paths.root / ".evidence-transaction.json").write_text('{"schema_version":99}')
    before = snapshot(handle.paths.root)
    result = SessionStore(root=tmp_path).recover_stale_sessions()
    assert result.recovered_session_ids == ()
    assert snapshot(handle.paths.root) == before
    assert SessionStore(root=tmp_path).load_metadata(handle.session_id)["state"] == "active"


@pytest.mark.parametrize("method", ["complete_session", "abandon_session"])
def test_public_lifecycle_rejects_legacy_writes_without_mutation(tmp_path, method):
    handle = legacy_session(tmp_path)
    before = snapshot(handle.paths.root)
    with pytest.raises(ValueError, match="schema-v2"):
        getattr(SessionStore(root=tmp_path), method)(handle)
    assert snapshot(handle.paths.root) == before
