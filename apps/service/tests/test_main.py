from __future__ import annotations

from pathlib import Path
from typing import Any

from dutchmate_service import main


def test_service_main_passes_config_to_app_and_host_port_to_uvicorn(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    session_roots: list[object] = []
    hardware_configs: list[object] = []
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"
""",
        encoding="utf-8",
    )

    def fake_create_app(*, session_root: object, hardware_config: object) -> object:
        session_roots.append(session_root)
        hardware_configs.append(hardware_config)
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
            "--config",
            str(config_path),
        ]
    )

    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 2041
    assert [str(path) for path in session_roots] == [".dutchmate/custom-sessions"]
    assert len(hardware_configs) == 1
    assert hardware_configs[0].require_control("reset").channel == "CTRL0"
