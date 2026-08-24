cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(dutchmate_zephyr_dut)

target_sources(app PRIVATE
    src/fixture_protocol.c
    src/main.c
)
