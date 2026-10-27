"""Real asyncio/pyserial-asyncio streams backed only by a test-owned pipe."""

import asyncio
import json
import os

import serial
import serial_asyncio


class PipeSerial:
    """Substitute the OS serial resource, retaining the installed transport logic."""

    def __init__(self, *, origin_us=1000, close_mode="closed"):
        self.origin_us = origin_us
        self.close_mode = close_mode
        self.fd, self.write_fd = os.pipe()
        self.is_open = True
        self.close_calls = 0
        self.read_error = serial.SerialException("read failed: [Errno 6] Device not configured")
        self.close_error = OSError("physical serial close failed")
        self.callback_errors = []
        self.commands = []
        self.configured = set()

    def fileno(self):
        return self.fd

    def read(self, size):
        raise self.read_error

    def flush(self):
        pass

    def write(self, data):
        command = json.loads(data)
        self.commands.append(command)
        if command["cmd"] == "configure_gpio_mode":
            self.configured.add(command["channel"])
        elif command["channel"] not in self.configured:
            response = {"ok": False, "error": "not_configured", "detail": "new epoch"}
            self.loop.call_soon_threadsafe(
                self.protocol.data_received, json.dumps(response).encode() + b"\n"
            )
            return len(data)
        response = {"ok": True, "timestamp_us": self.origin_us + len(self.commands)}
        self.loop.call_soon_threadsafe(
            self.protocol.data_received, json.dumps(response).encode() + b"\n"
        )
        return len(data)

    def close(self):
        self.close_calls += 1
        if self.close_mode == "failed":
            raise self.close_error
        if self.close_mode == "incomplete":
            return
        self.dispose()
        if self.close_mode == "unknown":
            self.is_open = None

    def dispose(self):
        """Release test-owned descriptors even when simulating broken cleanup."""
        for name in ("fd", "write_fd"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)
        self.is_open = False

    def disconnect(self):
        self.loop.call_soon_threadsafe(self.transport._read_ready)

    async def open_connection(self, **kwargs):
        self.loop = asyncio.get_running_loop()
        self.loop.set_exception_handler(lambda loop, context: self.callback_errors.append(context))
        reader = asyncio.StreamReader(limit=kwargs["limit"])
        self.protocol = asyncio.StreamReaderProtocol(reader)
        self.transport = serial_asyncio.SerialTransport(self.loop, self.protocol, self)
        writer = asyncio.StreamWriter(self.transport, self.protocol, reader, self.loop)
        await asyncio.sleep(0)  # Attach protocol and the pipe reader before hello.
        self.protocol.data_received(
            json.dumps(
                {
                    "type": "hello",
                    "v": 1,
                    "firmware": "development",
                    "device": "dutchmate-rp2350",
                    "capabilities": [
                        "uart_receive",
                        "uart_send",
                        "gpio_control",
                        "device_timestamp",
                        "overflow_telemetry",
                    ],
                }
            ).encode()
            + b"\n"
            + json.dumps(
                {
                    "type": "buffer_status",
                    "timestamp_us": self.origin_us,
                    "uart_rx_size_bytes": 32768,
                    "uart_rx_used_bytes": 0,
                    "uart_rx_high_water_bytes": 0,
                    "dropped_bytes_total": 0,
                    "overflow_events": 0,
                }
            ).encode()
            + b"\n"
        )
        return reader, writer
