"""Device connection and host-device protocol handling."""

from dutchmate_core.device_connection.commands import (
    WELL_KNOWN_GPIO_ROLES,
    BootModeCommand,
    ConfigureGpioModeCommand,
    ResetCommand,
    UartSendCommand,
    boot_mode_command,
    configure_gpio_mode_command,
    reset_command,
    uart_send_command,
    uart_send_text_command,
)
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import parse_device_message
from dutchmate_core.device_connection.serial_transport import (
    SerialCommandTransport,
    SerialPort,
    open_serial_command_transport,
)
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.device_connection.transport import (
    CommandTransport,
    TransportError,
    TransportTimeoutError,
)

__all__ = [
    "BootModeCommand",
    "BufferOverflowMessage",
    "BufferStatusMessage",
    "CommandErrorMessage",
    "CommandSuccessMessage",
    "CommandTransport",
    "ConfigureGpioModeCommand",
    "HelloMessage",
    "NdjsonStreamParser",
    "ResetCommand",
    "SerialCommandTransport",
    "SerialPort",
    "UartSendCommand",
    "UartMessage",
    "TransportError",
    "TransportTimeoutError",
    "WELL_KNOWN_GPIO_ROLES",
    "boot_mode_command",
    "configure_gpio_mode_command",
    "open_serial_command_transport",
    "parse_device_message",
    "reset_command",
    "uart_send_command",
    "uart_send_text_command",
]
