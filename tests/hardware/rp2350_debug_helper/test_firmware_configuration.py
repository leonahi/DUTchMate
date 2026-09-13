import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[3]
FIRMWARE_ROOT = REPOSITORY_ROOT / "hardware/firmware/rp2350_debug_helper"


def _decimal_define(path: Path, name: str) -> int:
    match = re.search(
        rf"^#define\s+{re.escape(name)}\s+(\d+)U$",
        path.read_text(),
        flags=re.MULTILINE,
    )
    assert match is not None, f"missing decimal define {name} in {path}"
    return int(match.group(1))


def test_cdc_tx_fifo_holds_one_maximum_evidence_frame() -> None:
    overlay = (
        FIRMWARE_ROOT / "boards/rpi_pico2_rp2350a_m33.overlay"
    ).read_text()
    fifo_match = re.search(r"tx-fifo-size\s*=\s*<(\d+)>;", overlay)
    assert fifo_match is not None, "missing CDC tx-fifo-size"

    frame_capacity = _decimal_define(
        FIRMWARE_ROOT / "src/uart_event.h",
        "DMH_UART_EVENT_FRAME_CAPACITY",
    )

    assert int(fifo_match.group(1)) >= frame_capacity
