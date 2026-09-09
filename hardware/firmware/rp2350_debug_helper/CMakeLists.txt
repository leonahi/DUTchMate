cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

set(DUTCHMATE_MINIMUM_ZEPHYR_VERSION "4.4.2")
set(DUTCHMATE_ZEPHYR_VERSION
    "${KERNEL_VERSION_MAJOR}.${KERNEL_VERSION_MINOR}.${KERNEL_PATCHLEVEL}"
)
if("${DUTCHMATE_ZEPHYR_VERSION}" VERSION_LESS
   "${DUTCHMATE_MINIMUM_ZEPHYR_VERSION}")
    message(FATAL_ERROR
        "DUTchMate RP2350 Debug Helper requires Zephyr "
        "${DUTCHMATE_MINIMUM_ZEPHYR_VERSION} or newer because earlier "
        "PL011 drivers do not acknowledge UART error interrupts "
        "(GHSA-36rp-2hcp-f5hv)."
    )
endif()

project(dutchmate_rp2350_debug_helper)

target_sources(app PRIVATE
    src/cdc_tx.c
    src/cdc_tx_state.c
    src/command_decode.c
    src/command_executor.c
    src/command_ingress.c
    src/command_runtime.c
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
