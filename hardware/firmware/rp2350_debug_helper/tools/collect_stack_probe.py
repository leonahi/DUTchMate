"""Read a frozen post-epoch Zephyr stack report over the normal USB CDC port."""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import serial  # type: ignore[import-untyped]

STACK_FRAGMENT = re.compile(
    r"^stack-(?P<index>\d+)of(?P<count>\d+)-"
    r"(?P<name>[A-Za-z0-9_.]+)-(?P<used>\d+)-(?P<size>\d+)$"
)


def read_hello(port_name: str) -> dict[str, object]:
    port = serial.Serial(port=None, baudrate=115200, timeout=3)
    port.dtr = False
    port.port = port_name
    try:
        port.open()
        port.reset_input_buffer()
        port.dtr = True
        frame = port.readline()
    finally:
        port.dtr = False
        port.close()
    if not frame:
        raise RuntimeError("no hello received within 3 seconds")
    hello = cast(dict[str, object], json.loads(frame))
    if hello.get("type") != "hello" or hello.get("device") != "dutchmate-rp2350":
        raise RuntimeError(f"unexpected first frame: {hello!r}")
    return hello


def collect(port_name: str) -> list[dict[str, int | str]]:
    measurements: list[dict[str, int | str]] = []
    expected_count: int | None = None
    while True:
        hello = read_hello(port_name)
        firmware = hello.get("firmware", "")
        if not isinstance(firmware, str):
            raise RuntimeError("hello firmware identifier is not a string")
        if firmware == "stack-error":
            raise RuntimeError("stack report is empty or exceeded firmware capacity")
        match = STACK_FRAGMENT.fullmatch(firmware)
        if match is None:
            raise RuntimeError(f"expected frozen stack report, got {firmware!r}")
        index = int(match["index"])
        count = int(match["count"])
        if count < 1 or count > 16 or index != len(measurements) + 1:
            raise RuntimeError(f"out-of-order stack fragment: {firmware!r}")
        if expected_count is None:
            expected_count = count
        elif count != expected_count:
            raise RuntimeError("stack fragment count changed during collection")
        used = int(match["used"])
        size = int(match["size"])
        if used > size:
            raise RuntimeError(f"invalid stack usage exceeds size: {firmware!r}")
        measurements.append(
            {"name": match["name"], "used_bytes": used,
             "size_bytes": size, "free_bytes": size - used}
        )
        if index == count:
            time.sleep(0.15)
            return measurements
        time.sleep(0.15)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="Pico 2 CDC port, e.g. /dev/cu.usbmodem11201")
    parser.add_argument("--uf2", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    image = args.uf2.read_bytes()
    measurements = collect(args.port)
    result = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "port": args.port,
        "uf2_sha256": hashlib.sha256(image).hexdigest(),
        "stacks": measurements,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
