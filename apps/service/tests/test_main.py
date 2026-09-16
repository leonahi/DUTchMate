from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dutchmate_core.backends.settings import BackendSettings
from dutchmate_service import main


def test_service_main_rejects_non_positive_session_max_size() -> None:
    with pytest.raises(SystemExit) as error:
        main.main(["--session-max-size-mb", "0"])

    assert error.value.code == 2


def test_service_main_rejects_non_positive_session_max_count() -> None:
    with pytest.raises(SystemExit) as error:
        main.main(["--session-max-count", "0"])

    assert error.value.code == 2


def test_service_main_passes_config_to_app_and_host_port_to_uvicorn(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    session_roots: list[object] = []
    session_budgets: list[int] = []
    session_counts: list[int | None] = []
    hardware_configs: list[object] = []
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[backend]
mode = "enhanced"

[hardware]
dut_io_voltage = 3.3

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"
""",
        encoding="utf-8",
    )

    def fake_create_app(
        *,
        session_root: object,
        session_evidence_budget_bytes: int,
        session_max_count: int | None,
        hardware_config: object,
        backend_settings: BackendSettings,
    ) -> object:
        session_roots.append(session_root)
        session_budgets.append(session_evidence_budget_bytes)
        session_counts.append(session_max_count)
        hardware_configs.append(hardware_config)
        assert backend_settings.mode == "enhanced"
        assert backend_settings.serial_port == "/dev/ttyACM0"
        assert backend_settings.baudrate == 460800
        return object()

    def fake_run(app: object, *, host: str, port: int) -> None:
        calls.append({"app": app, "host": host, "port": port})

    monkeypatch.setattr(main, "create_app", fake_create_app)
    monkeypatch.setattr(main.uvicorn, "run", fake_run)

    main.main(
        [
            "--host",
            "127.0.0.1",
            "--port",
            "2041",
            "--session-root",
            ".dutchmate/custom-sessions",
            "--session-max-size-mb",
            "10",
            "--session-max-count",
            "25",
            "--config",
            str(config_path),
            "--serial-port",
            "/dev/ttyACM0",
        ]
    )

    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 2041
    assert [str(path) for path in session_roots] == [".dutchmate/custom-sessions"]
    assert session_budgets == [10 * 1024 * 1024]
    assert session_counts == [25]
    assert len(hardware_configs) == 1
    assert hardware_configs[0].dut_io_voltage == 3.3
    assert hardware_configs[0].require_control("reset").channel == "CTRL0"
