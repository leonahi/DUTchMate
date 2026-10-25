"""Stage 7 requested control-line provenance and safe native USB selection."""

from dataclasses import replace

import pytest

from dutchmate_core.backends.basic import BasicBackendEventSource, open_basic_backend_connection
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.device_connection.discovery import SerialPortCandidate
from dutchmate_core.profile import DutProfileConfig, UartProfileConfig, resolve_dut_profile
from dutchmate_core.profile.config import parse_dut_profile_config


def test_requested_lines_are_preconfigured_before_open_and_do_not_advertise_gpio():
    order = []

    class Port:
        def __setattr__(self, key, value):
            order.append((key, value))
            object.__setattr__(self, key, value)

        def open(self):
            order.append(("open", self.port))
            assert self.dtr is False and self.rts is True

        def close(self):
            order.append(("close", None))

        def read(self, size=1):
            return b""

        def write(self, data):
            return len(data)

    def factory(**kwargs):
        assert kwargs["port"] is None
        return Port()

    profile = resolve_dut_profile(
        DutProfileConfig(uart=UartProfileConfig(dtr_on_open="deasserted", rts_on_open="asserted")),
        mode="basic",
        serial_port="/dev/old",
    )
    connection = open_basic_backend_connection(profile.backend_settings, serial_factory=factory)
    snapshot = BasicBackendEventSource(connection, segment_id=0).snapshot
    assert order.index(("dtr", False)) < order.index(("open", "/dev/old"))
    assert snapshot.serial_provenance["open_transition"] == "preconfigured"
    assert snapshot.serial_provenance["electrical_glitch_free"] is False
    assert snapshot.serial_provenance["dtr_requested"] == "deasserted"
    assert snapshot.serial_provenance["rts_owner"] == "application"
    assert "gpio_control" not in snapshot.capabilities
    assert "serial_line_control" not in snapshot.capabilities
    connection.close()


@pytest.mark.parametrize("cleanup_fails", [False, True])
@pytest.mark.parametrize("behavior", ["driver_default", "deasserted"])
def test_failed_open_reports_confirmed_versus_unknown_cleanup(cleanup_fails, behavior):
    from dutchmate_core.backends.contracts import BackendOpenError

    closed = []

    class Port:
        def open(self):
            raise OSError("open failed")

        def close(self):
            closed.append(True)
            if cleanup_fails:
                raise OSError("cleanup failed")

    profile = resolve_dut_profile(
        DutProfileConfig(uart=UartProfileConfig(dtr_on_open=behavior)),
        mode="basic",
        serial_port="/dev/old",
    )
    with pytest.raises(BackendOpenError) as raised:
        open_basic_backend_connection(
            profile.backend_settings, serial_factory=lambda **kwargs: Port()
        )
    assert raised.value.cleanup_confirmed is (not cleanup_fails)
    assert closed == [True]


def usb_profile():
    return resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {
                    "mode": "basic",
                    "serial_port": "/dev/old",
                    "topology": "native_usb_console",
                    "selector": {"vid": 0x1234, "pid": 0x5678, "serial_number": "unit-1"},
                },
            }
        )
    )


def candidate(path, serial="unit-1"):
    return SerialPortCandidate(
        device=path,
        description="port",
        hwid="usb",
        vid=0x1234,
        pid=0x5678,
        serial_number=serial,
    )


def test_native_selector_accepts_only_a_unique_identity_and_external_path_is_exact():
    from dutchmate_core.backends.selection import select_backend_settings

    profile = usb_profile()
    result = select_backend_settings(profile.backend_settings, candidates=[candidate("/dev/new")])
    assert result.serial_port == "/dev/new"
    with pytest.raises(ConnectionLifecycleError) as raised:
        select_backend_settings(
            profile.backend_settings, candidates=[candidate("/dev/a"), candidate("/dev/b")]
        )
    assert raised.value.error == "service_unavailable"
    assert raised.value.context["reason"] == "ambiguous_device"
    with pytest.raises(ConnectionLifecycleError):
        select_backend_settings(
            profile.backend_settings, candidates=[candidate("/dev/other", "not-unit")]
        )
    external = replace(profile.backend_settings, topology="external_uart")
    assert (
        select_backend_settings(external, candidates=[candidate("/dev/new")]).serial_port
        == "/dev/old"
    )


def test_rts_flow_control_conflict_is_rejected_before_any_open():
    with pytest.raises(ValueError, match="conflicts"):
        resolve_dut_profile(
            DutProfileConfig(uart=UartProfileConfig(rtscts=True, rts_on_open="deasserted")),
            mode="basic",
            serial_port="/dev/old",
        )


def test_basic_source_never_hides_an_unconfirmed_close_on_a_second_call():
    from dutchmate_core.backends.basic import BasicBackendConnection

    class Port:
        def close(self):
            raise OSError("unconfirmed close")

    profile = resolve_dut_profile(DutProfileConfig(), mode="basic", serial_port="/dev/old")
    source = BasicBackendEventSource(
        BasicBackendConnection(serial_port=Port(), settings=profile.backend_settings), segment_id=0
    )
    with pytest.raises(OSError):
        source.close()
    with pytest.raises(OSError):
        source.close()


@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_enhanced_failed_open_keeps_primary_error_and_cleanup_certainty(cleanup_fails):
    from test_enhanced_serial_io import FakeStreamReader, FakeStreamWriter, RecordingOpener

    from dutchmate_core.backends.enhanced_serial_io import open_async_enhanced_serial_adapter

    writer = FakeStreamWriter(None)
    if cleanup_fails:
        writer.wait_closed_failure = OSError("cleanup failed")
    with pytest.raises(RuntimeError, match="omitted serial resource") as raised:
        await open_async_enhanced_serial_adapter(
            port="/dev/old",
            segment_id=0,
            open_connection=RecordingOpener(FakeStreamReader(), writer),
        )
    assert raised.value.cleanup_confirmed is (not cleanup_fails)
    assert writer.close_count == 1


async def test_enhanced_explicit_close_retains_unconfirmed_resource_cleanup():
    from test_enhanced_serial import HELLO_FRAME, FakeAsyncSerialReader, make_adapter

    reader = FakeAsyncSerialReader()
    reader.close_failure = OSError("close unconfirmed")
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    with pytest.raises(OSError, match="unconfirmed"):
        await adapter.close()
    with pytest.raises(OSError, match="unconfirmed"):
        await adapter.close()
    assert reader.close_count == 1


async def test_enhanced_transport_inspection_failure_still_confirms_cleanup():
    from test_enhanced_serial_io import FakeStreamReader, FakeStreamWriter, RecordingOpener

    from dutchmate_core.backends.enhanced_serial_io import open_async_enhanced_serial_adapter

    class Transport:
        def get_extra_info(self, name):
            raise RuntimeError("inspection failed")

    writer = FakeStreamWriter(None)
    writer.transport = Transport()
    with pytest.raises(RuntimeError, match="inspection failed") as raised:
        await open_async_enhanced_serial_adapter(
            port="/dev/old",
            segment_id=0,
            open_connection=RecordingOpener(FakeStreamReader(), writer),
        )
    assert writer.close_count == 1
    assert raised.value.cleanup_confirmed is True
