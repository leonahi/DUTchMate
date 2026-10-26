"""Keep service tests away from developer and live HIL state by default."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_service_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve relative config/session/PID/log paths inside per-test state."""
    monkeypatch.chdir(tmp_path)
