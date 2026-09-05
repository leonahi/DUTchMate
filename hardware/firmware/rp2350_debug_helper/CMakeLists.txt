cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(dutchmate_rp2350_debug_helper)

target_sources(app PRIVATE
    src/command_decode.c
    src/command_executor.c
    src/command_response.c
    src/connection_epoch.c
    src/control_state.c
    src/hello.c
    src/main.c
    src/ndjson_framer.c
    src/platform_io.c
    src/telemetry.c
    src/uart_event.c
    src/uart_rx.c
    src/uart_rx_ring.c
    src/uart_tx.c
    src/uart_tx_state.c
    src/usb_connection.c
)
