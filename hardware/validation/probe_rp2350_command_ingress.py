#!/usr/bin/env python3
"""Verify that an RP2350 Debug Helper accepts one host command."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import serial


def _read_frame(port: serial.Serial, deadline: float) -> dict[str, Any] | None:
    buffer = bytearray()
    while time.monotonic() < deadline:
        byte = port.read(1)
        if not byte:
            continue
        if byte != b"\n":
            buffer.extend(byte)
            continue
        try:
            frame = json.loads(buffer)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"invalid NDJSON frame: {buffer!r}") from error
        if not isinstance(frame, dict):
            raise RuntimeError(f"non-object NDJSON frame: {frame!r}")
        return frame
    return None


def _open_port(path: str) -> serial.Serial:
    port = serial.Serial(
        port=None,
        baudrate=115200,
        timeout=0.05,
        write_timeout=1.0,
        exclusive=True,
    )
    port.dtr = False
    port.port = path
    port.open()
    port.reset_input_buffer()
    port.dtr = True
    return port


def probe(path: str, timeout_s: float) -> None:
    observed: list[dict[str, Any]] = []
    port = _open_port(path)
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            frame = _read_frame(port, deadline)
            if frame is None:
                raise RuntimeError(f"hello timed out; observed={observed!r}")
            observed.append(frame)
            if frame.get("type") == "hello":
                break

        port.write(b'{"cmd":"bogus"}\n')
        port.flush()
        deadline = time.monotonic() + timeout_s
        while True:
            frame = _read_frame(port, deadline)
            if frame is None:
                raise RuntimeError(
                    "invalid-command response timed out; "
                    f"observed={observed!r}"
                )
            observed.append(frame)
            if frame.get("error") == "invalid_command":
                return
    finally:
        port.dtr = False
        port.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="CDC serial path, such as /dev/cu.usbmodem11201")
    parser.add_argument("--timeout-s", type=float, default=2.0)
    args = parser.parse_args()
    try:
        probe(args.port, args.timeout_s)
    except (OSError, RuntimeError, serial.SerialException) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: hello received and invalid command rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
