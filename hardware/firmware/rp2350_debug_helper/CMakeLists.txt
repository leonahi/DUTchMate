cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(dutchmate_rp2350_debug_helper)

target_sources(app PRIVATE
    src/connection_epoch.c
    src/hello.c
    src/main.c
    src/platform_io.c
    src/usb_connection.c
)
