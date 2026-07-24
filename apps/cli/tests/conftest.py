from __future__ import annotations

import pytest

from dutchmate_cli import main
from dutchmate_cli.config import CliConfig


@pytest.fixture(autouse=True)
def default_cli_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "load_cli_config", lambda: CliConfig())
