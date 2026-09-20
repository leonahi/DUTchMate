# Graph Report - DUTchMate  (2026-09-20)

## Corpus Check
- 351 files · ~274,964 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4932 nodes · 13076 edges · 236 communities (217 shown, 19 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2386 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a99b0835`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_backend_reconnect.py
- format_status
- dutchmate_cli/config.py
- client.py
- dutchmate_cli/main.py
- ContinuousIngestionCoordinator
- workflows/capture.py
- main
- settings.py
- fixed_clock
- FakeDeviceControl
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- SessionStore
- runtime.py
- transport.py
- cdc_tx_state_harness.c
- parse_device_message
- SessionSummary
- log_replay.py
- .capture_source_health
- service_error_from_exception
- SerialPortCandidate
- comparison.py
- Phase 1B Revision A Prototype Validation Record
- DeviceCoreStatus
- SessionPersistenceError
- parse_hardware_gpio_config
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- command_executor_harness.c
- evidence.py
- test_basic.py
- UartReceiveEvent
- GpioModeRegistry
- DeviceCoreRuntime
- EnhancedAsyncHost
- CaptureSourceHealth
- parser.py
- store.py
- dutchmate_cli/__init__.py
- FakeAsyncFrameWriter
- command_decode.c
- enhanced.py
- uart_rx_ring.c
- Service-Owned Continuous Ingestion Design
- format_uart_send
- errors.schema.json
- helpers.py
- test_app_lifecycle.py
- logs.py
- Continuous Connection And Integrity Monitoring Design
- SessionComparison
- test_device_core_uart_send.py
- test_retrieval.py
- fixed_clock
- Incremental Re-Extraction
- sessions.py
- models.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- BasicBackendConnection
- Enhanced Asynchronous Serial Adapter Design
- dutchmate_mcp_server/main.py
- CommandSuccessMessage
- test_capture_reconnect.py
- InputValidationError
- test_baseline.py
- enhanced_serial_io.py
- test_retention.py
- CaptureWorkflow
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- FakeAsyncSerialReader
- ._next_timestamp
- zephyr_dut/src/main.c
- dutchmate_usb_connection_run
- build_session_evidence
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- gpio_config/config.py
- format_baseline_mutation
- BackendInfo
- GPIO Configuration Semantics
- Enhanced Asynchronous Serial I/O Design
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- BlockingCloseSource
- make_adapter
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- Coordinated Background Reconnect Design
- ReplaceableDeviceControl
- Software Architecture
- EnhancedCaptureFixtureRecorder
- .run
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- DtrControlledSerial
- dutchmate-core
- DeviceCoreClient
- FakeDeviceControl
- test_device_core_lifecycle.py
- Graph Exports
- dutchmate_mcp_server/__init__.py
- device_connection/__init__.py
- gpio_config/__init__.py
- log_processing/__init__.py
- session_store/__init__.py
- uart_capture/__init__.py
- workflows/__init__.py
- dutchmate-workspace
- SerialFrameSink
- FakeEnhancedAsyncHost
- Enhanced Async Service Integration Design
- BackendDisconnectedError
- uart_tx.c
- File Responsibility Map
- File Responsibility Map
- BlockingCloseStreamWriter
- test_protocol_integration.py
- format_wait_pattern
- EvidenceQuotaExceeded
- File Map
- File Responsibility Map
- test_log_replay.py
- telemetry.c
- _UnavailableDeviceControl
- test_gpio.py
- BasicSerialPort
- command_runtime.c
- File Responsibility Map
- BasicBackendEventSource
- UartIntegrity
- FakeStreamTransport
- test_recovery.py
- test_enhanced_serial.py
- test_transactions.py
- _run
- test_device_message_examples.py
- SegmentContext
- BackendSnapshot
- _run
- File Responsibility Map
- test_host_command_encoder.py
- _run
- RP2350 Debug Helper Firmware Design
- CaptureSessionStorage
- .close
- dmh_uart_event_encode
- Q: commit and tell me what is next development step in phase-1
- Q: Before that what does Zephyr DUT exactly do and what is its use?
- Q: What does DMF stands for
- Q: I am ready to flash the pico.
- Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host.
- Q: commit and go to next step
- Q: move to next step
- Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy
- Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries
- Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests.
- Q: Where is the shared Enhanced host-command encoding and dispatch boundary?
- Q: How should Enhanced serial command short writes complete or report partial acceptance?
- Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?
- Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?
- Q: What is the next Phase 1 development step after pushing main?
- Q: What remains in Phase 1 before proceeding with the Enhanced async service integration design?
- Q: How should the service-owned continuous ingestion coordinator fit the current backend, runtime, session, and reconnect boundaries?
- Q: Create a detailed implementation plan for the approved service-owned continuous ingestion coordinator design
- Q: Create implementation plan for approved continuous connection monitoring design
- Q: done, what is the next steps to finish phase 1
- .__init__
- connection_epoch.c
- _run_hello
- load_startup_hardware_config
- .discard_pending_events
- backend_reconnect.py
- decoder_harness
- executor_harness
- ingress_harness
- _run_states
- framer_harness
- ring_harness
- Q: What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?
- DUTchMate RP2350 Debug Helper Firmware
- test_control_state_machine
- test_uart_tx_state_machine
- test_receive_event_accepts_zero_timeout
- TerminationBarrierAdapter
- dmh_output_drain_batch
- test_device_core_wait.py
- service_client.py
- Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?
- test_cdc_tx_state_machine
- create_server
- .__init__
- server.py
- collect_stack_probe.py
- CaptureRecorder
- dmh_hello_encode
- mcp
- Q: Which RP2350 firmware boundaries need hardware-independent automated coverage and reproducible build instructions?
- Q: what is next
- Q: ok we can do this, tell me what to do
- Q: I have the schematic and layout file for Eagle CAD, where you want me to add. I have the fully assembled board with me that I use it with Pico 2.
- Q: Review the supplied Eagle schematic only against Revision A Pico 2/RP2350A requirements and safe-state contracts
- Q: ok lets move to next step than
- Q: Trace Enhanced RP2350 UART receive events from async serial parsing through continuous ingestion to active session persistence, especially per-event processing, locking, flushing, and filesystem writes that could limit throughput
- test_output_drain_batch_policy
- test_uart_rx_adapter_error_policy
- _decimal_define
- dutchmate_debug_agent/__init__.py
- test_reader_failure_is_repeatable_disconnect
- _request_after_entering
- _BoundedNewest
- test_service_client.py
- test_close_wakes_idle_disconnect_waiter
- run_load_profile.py
- Phase 1B Enhanced Workflow HIL Evidence
- TransportTimeoutError
- .begin_workflow
- .end_workflow
- Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 274 edges
2. `DeviceCoreRuntime` - 140 edges
3. `UartReceiveEvent` - 116 edges
4. `SegmentContext` - 99 edges
5. `create_app()` - 90 edges
6. `ContinuousIngestionCoordinator` - 82 edges
7. `SessionHandle` - 79 edges
8. `FakeRuntime` - 73 edges
9. `BackendSnapshot` - 71 edges
10. `parse_device_message()` - 70 edges

## Surprising Connections (you probably didn't know these)
- `dut_uart_callback()` --calls--> `uart_err_check()`  [INFERRED]
  hardware/firmware/rp2350_debug_helper/src/uart_rx.c → tests/hardware/rp2350_debug_helper/uart_rx_adapter_harness.c
- `Ring Buffer Validation Gate` --semantically_similar_to--> `Ring Buffer Acceptance Checklist`  [INFERRED] [semantically similar]
  docs/ring_buffer_sizing_plan.md → hardware/validation/phase1_ring_buffer.md
- `Safe High-Impedance Behavior` --semantically_similar_to--> `Hardware Safe Startup State`  [INFERRED] [semantically similar]
  docs/gpio_configuration_semantics.md → hardware/schematics/revision_a.md
- `_summary_from_metadata()` --calls--> `_first_error()`  [INFERRED]
  core/src/dutchmate_core/session_store/metadata.py → apps/cli/src/dutchmate_cli/capture.py
- `CliConfig` --uses--> `BackendConfig`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DUTchMate Backend Pipeline** — readme_basic_backend, readme_enhanced_backend, readme_shared_host_processing_and_session_pipeline [EXTRACTED 1.00]
- **Graphify Operational Pipeline** — _codex_skills_graphify_skill_extraction_pipeline, _codex_skills_graphify_references_update_incremental_re_extraction, _codex_skills_graphify_skill_graph_health_check [EXTRACTED 1.00]
- **Bounded Evidence Integrity Contract** — docs_debug_agent_context_contract_bounded_hardware_evidence, docs_reconnect_session_semantics_incremental_evidence_writes, docs_software_architecture_session_store, docs_ring_buffer_sizing_plan_buffer_integrity_reporting, docs_mcp_integration_plan_bounded_tool_results [INFERRED 0.85]
- **Backend-Independent Evidence Pipeline** — docs_project_context_normalized_evidence_boundary, docs_phase1_implementation_spec_backend_independent_pipeline, docs_software_architecture_normalized_event_boundary, docs_software_architecture_backends_contracts [INFERRED 0.95]
- **Phase 1 Hardware Acceptance Gate** — docs_development_status_hardware_acceptance, docs_phase1_implementation_spec_phase1_done_criteria, docs_ring_buffer_sizing_plan_validation_gate, hardware_schematics_revision_a_prototype_validation, hardware_validation_phase1_ring_buffer_acceptance_checklist [INFERRED 0.95]

## Communities (236 total, 19 thin omitted)

### Community 0 - "test_backend_reconnect.py"
Cohesion: 0.11
Nodes (25): BackendReconnectCoordinator, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt., ClosableSource, FakeSourceOwner, _release_stuck_attempt(), _snapshot() (+17 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "dutchmate_cli/config.py"
Cohesion: 0.10
Nodes (38): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+30 more)

### Community 3 - "client.py"
Cohesion: 0.06
Nodes (67): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+59 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (54): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, _display(), format_boot_mode_result(), format_reset_result() (+46 more)

### Community 5 - "ContinuousIngestionCoordinator"
Cohesion: 0.12
Nodes (52): ContinuousIngestionCoordinator, Continuously drain one source and expose an active-workflow FIFO., buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, MonkeyPatch, parametrize (+44 more)

### Community 6 - "workflows/capture.py"
Cohesion: 0.06
Nodes (58): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+50 more)

### Community 7 - "main"
Cohesion: 0.08
Nodes (50): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+42 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (48): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError, _baudrate() (+40 more)

### Community 9 - "fixed_clock"
Cohesion: 0.14
Nodes (49): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., test_normalizes_buffer_telemetry(), enhanced_snapshot(), evidence_bytes(), fixed_clock() (+41 more)

### Community 10 - "FakeDeviceControl"
Cohesion: 0.17
Nodes (36): AdvancingMonotonicClock, enhanced_info(), FakeCaptureSource, FakeDeviceControl, FakeMonotonicClock, BackendCapability, DeviceMessage, _fixed_session_time() (+28 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (51): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest, BootTestRequest, CaptureRequest (+43 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.10
Nodes (28): UART bytes captured by the Debug Helper., UartMessage, _frame_body(), NdjsonStreamParser, DeviceMessage, NDJSON stream parsing for serial byte chunks., Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline. (+20 more)

### Community 13 - "metadata.py"
Cohesion: 0.08
Nodes (43): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _append_resumed_backend_segment(), _backend_segment_json(), _bounded_error(), _capability_policy_json(), _contiguous_native_segments() (+35 more)

### Community 14 - "create_app"
Cohesion: 0.10
Nodes (50): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, parametrize, test_boot_test_active_uses_conflict_error_contract(), test_boot_test_disconnected_uses_service_unavailable_contract() (+42 more)

### Community 15 - "SessionStore"
Cohesion: 0.04
Nodes (46): Sessions abandoned at startup plus non-fatal compatibility diagnostics., Reference to a created debug session., SessionHandle, SessionRecoveryResult, CommandedBootMode, SessionDetail, SessionWorkflow, Create filesystem-backed debug sessions. (+38 more)

### Community 16 - "runtime.py"
Cohesion: 0.05
Nodes (62): Service-facing Device Core runtime composition., Capture new UART evidence until one literal completes or time expires., _validate_native_lifecycle_inputs(), GpioIdentifierValidationError, _is_unicode_whitespace(), prepare_uart_send_payload(), GpioModeRequestSource, ValueError (+54 more)

### Community 17 - "transport.py"
Cohesion: 0.11
Nodes (29): _classify_serial_write_error(), Exception, TransportWriteErrorCode, Exact serial-frame writes shared by Enhanced transport adapters., Write and flush one complete frame with exact accepted-byte errors., write_serial_frame(), RuntimeError, TransportWriteErrorCode (+21 more)

### Community 18 - "cdc_tx_state_harness.c"
Cohesion: 0.34
Nodes (17): dmh_cdc_tx_cancel(), dmh_cdc_tx_driver_fault(), dmh_cdc_tx_init(), dmh_cdc_tx_on_writable(), dmh_cdc_tx_poll(), dmh_cdc_tx_start(), finish(), expect_result() (+9 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (63): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+55 more)

### Community 20 - "SessionSummary"
Cohesion: 0.11
Nodes (19): capture_summary_payload(), Serialize a completed capture session summary., test_capture_summary_serializes_bounded_first_error_evidence(), test_capture_summary_serializes_quota_truncation_context(), DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName (+11 more)

### Community 21 - "log_replay.py"
Cohesion: 0.12
Nodes (50): SessionDetail, _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path (+42 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.09
Nodes (42): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+34 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.09
Nodes (38): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+30 more)

### Community 25 - "comparison.py"
Cohesion: 0.11
Nodes (30): Return bounded recent UART replay for one selected session., Return recent UART evidence without requiring a backend connection., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary(), _line_excerpt() (+22 more)

### Community 26 - "Phase 1B Revision A Prototype Validation Record"
Cohesion: 0.05
Nodes (42): 2026-09-15 Source Mapping And Configured Rejection Audit, Active Enhanced UART Idle Path At 1.8 V, Active-Low Control `/OE` Follow-Up, CDC Command-Ingress Diagnosis And Corrected Image, Control High Impedance During Debugger Reset, Corrected paired-probe TX cycle: receive-pin disturbances captured, Corrected-probe baseline timeout, Correction Of Capture-Timing Interpretations (+34 more)

### Community 27 - "DeviceCoreStatus"
Cohesion: 0.05
Nodes (31): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Apply startup hardware control mappings., Runtime surface needed by the current service API., Return the current Device Core status., Configure a control channel GPIO mode. (+23 more)

### Community 28 - "SessionPersistenceError"
Cohesion: 0.13
Nodes (36): Raised when durable session evidence cannot be read or written., SessionPersistenceError, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file() (+28 more)

### Community 29 - "parse_hardware_gpio_config"
Cohesion: 0.18
Nodes (21): parse_hardware_gpio_config(), Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level(), test_parse_valid_hardware_control_mapping(), test_rejects_duplicate_channel_assignments() (+13 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.07
Nodes (38): AsyncEnhancedDeviceControl, AsyncEnhancedUartSender, EnhancedNdjsonEventStream, ControlState, Translate complete UART payloads through an async Enhanced transport., Parse Enhanced NDJSON chunks and expose only normalized evidence events., Return an incomplete Enhanced NDJSON frame buffered by the parser., Translate semantic control operations through an async Enhanced transport. (+30 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.14
Nodes (22): FakeStreamReader, FakeStreamWriter, Exception, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if the Enhanced UART setting reaches the host CDC line coding., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error. (+14 more)

### Community 33 - "command_executor_harness.c"
Cohesion: 0.06
Nodes (98): dmh_command_executor_cancel_epoch(), dmh_command_executor_poll(), dmh_command_executor_reject(), dmh_command_executor_response(), dmh_command_executor_response_sent(), dmh_command_executor_submit(), map_control_result(), response_encoded() (+90 more)

### Community 34 - "evidence.py"
Cohesion: 0.12
Nodes (23): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), _match_coordinate() (+15 more)

### Community 35 - "test_basic.py"
Cohesion: 0.12
Nodes (23): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., Return the configured software capability policy., FakeRawSerial, Exception, parametrize (+15 more)

### Community 36 - "UartReceiveEvent"
Cohesion: 0.09
Nodes (44): test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, Finalize and discard trailing derived state for one connection segment., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission., Return bytes awaiting a line terminator for one segment and channel. (+36 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.08
Nodes (46): _format_utc_timestamp(), GpioControlChannelState, GpioModeRegistry, GpioModeRejection, datetime, GpioControlChannel, GpioModeRequestSource, GpioRoleName (+38 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.11
Nodes (21): DeviceCoreRuntime, Compose Phase 1 core services behind one service-facing object., Close the currently owned backend source exactly once., Return one bounded page without requiring a backend connection., GPIO role configuration state used by this runtime., Record normalized identity for the selected connected backend., Mark the Debug Helper connection as disconnected., Return the current service-facing status snapshot. (+13 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.05
Nodes (43): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, BackendEvent (+35 more)

### Community 40 - "CaptureSourceHealth"
Cohesion: 0.22
Nodes (20): CaptureSourceHealth, Immutable current-source connection, integrity, and replacement projection., Return one immutable current-source health snapshot., monitored_runtime(), MutableHealthSource, FakeMonotonicClock, Path, replacement_snapshot() (+12 more)

### Community 41 - "parser.py"
Cohesion: 0.13
Nodes (35): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol boundaries., Base class for host-device protocol errors. (+27 more)

### Community 42 - "store.py"
Cohesion: 0.07
Nodes (43): Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., BaselineOperation, Designate a stored session without requiring a backend connection., Clear a named designation without requiring a backend connection., clear_baseline(), _ineligibility_reason(), mark_baseline() (+35 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.11
Nodes (26): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+18 more)

### Community 44 - "FakeAsyncFrameWriter"
Cohesion: 0.10
Nodes (19): FakeAsyncFrameWriter, Fails if same-batch response success masks invalid input or drops its prefix., Fails if post-transmission cancellation leaves an orphan response path., Fails if command routing consumes or reorders interleaved UART evidence., Fails if a response overtakes earlier evidence blocked outside the FIFO., Fails if a second uncorrelated command is written before the first resolves., Fails if async routing replaces write accounting or its repeatable terminal., Fails if caller cancellation leaves an uncorrelated response path alive. (+11 more)

### Community 45 - "command_decode.c"
Cohesion: 0.08
Nodes (54): append_string_byte(), base64_value(), decode_base64(), decode_channel(), decode_configure(), decode_level(), decode_pulse(), decode_state() (+46 more)

### Community 46 - "enhanced.py"
Cohesion: 0.07
Nodes (42): BackendInputError, Raised when a backend emits malformed or otherwise invalid input., backend_input_error_from_protocol(), _control_success_timestamp(), enhanced_message_timestamp_us(), enhanced_segment_context(), normalize_enhanced_hello(), normalize_enhanced_message() (+34 more)

### Community 47 - "uart_rx_ring.c"
Cohesion: 0.22
Nodes (28): append_descriptor(), copy_into_ring(), dmh_uart_rx_ring_claim_overflow(), dmh_uart_rx_ring_init(), dmh_uart_rx_ring_next_observation(), dmh_uart_rx_ring_peek_observation(), dmh_uart_rx_ring_push(), dmh_uart_rx_ring_snapshot() (+20 more)

### Community 48 - "Service-Owned Continuous Ingestion Design"
Cohesion: 0.09
Nodes (21): Active, Architectural Decision, Closing / Closed, Components And Boundaries, Concurrency Invariants, Context, `ContinuousIngestionCoordinator`, Coordinator State Model (+13 more)

### Community 49 - "format_uart_send"
Cohesion: 0.40
Nodes (5): _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., test_format_forced_send_reports_attempt_and_evidence_pair()

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "helpers.py"
Cohesion: 0.09
Nodes (27): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _append_line(), BaselineRuntime, _capture() (+19 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.10
Nodes (18): DUTchMate Device Core Service package., BlockingCaptureSource, ClosableFakeRuntime, _hardware_config(), NoopDeviceControl, BackendEvent, ControlState, Exception (+10 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "Continuous Connection And Integrity Monitoring Design"
Cohesion: 0.08
Nodes (24): Acceptance Criteria, Architectural Decision, Buffer Overflow, Buffer Status, Concurrency And Ownership Invariants, Context, Continuous Connection And Integrity Monitoring Design, Coordinator State And Event Projection (+16 more)

### Community 55 - "SessionComparison"
Cohesion: 0.06
Nodes (29): BaselineComparisonSummary, BaselineComparisonUnavailable, load_baseline_context(), _pointer_changed(), Explicit project-baseline context for a bounded Debug Agent evidence package., Bounded comparison facts without repeating UART line text., A valid baseline exists, but the subject cannot be compared yet., Use only the validated project pointer; never pick a baseline by recency. (+21 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.18
Nodes (28): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events() (+20 more)

### Community 57 - "test_retrieval.py"
Cohesion: 0.22
Nodes (18): _create_native_session(), parametrize, Path, test_get_session_distinguishes_not_found_unsupported_and_corrupt(), test_latest_session_returns_newest_or_none(), test_legacy_session_detail_returns_only_identity_and_artifact_sizes(), test_list_sessions_applies_positive_limit(), test_list_sessions_ignores_unrelated_files_and_directories() (+10 more)

### Community 58 - "fixed_clock"
Cohesion: 0.34
Nodes (19): Create a capture session and return a recorder for it., enhanced_snapshot(), fixed_clock(), fixed_id(), datetime, Path, read_jsonl(), Path (+11 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "models.py"
Cohesion: 0.08
Nodes (47): EvidenceTypeCount, FirstError, FirstErrorReference, LegacySessionDetail, LegacySessionListItem, NativeSessionListItem, Public session-store data models and lifecycle errors., Reference-bearing view of the first stored failure-pattern match. (+39 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.19
Nodes (31): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), MonkeyPatch, Path (+23 more)

### Community 63 - "persistence.py"
Cohesion: 0.13
Nodes (34): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+26 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.10
Nodes (19): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+11 more)

### Community 66 - "BasicBackendConnection"
Cohesion: 0.13
Nodes (13): Return an opened Basic connection., _basic_settings(), FakeBasicSerial, test_basic_active_candidate_uses_coordinator_and_replaces_sender(), test_basic_active_rejection_retains_candidate_cleanup_failure(), test_basic_idle_candidate_preserves_identity_and_segment_zero(), test_basic_reconnect_rejects_identity_before_transferring_source(), BasicBackendConnection (+5 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "dutchmate_mcp_server/main.py"
Cohesion: 0.23
Nodes (10): main(), _parser(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server over stdio., MonkeyPatch, test_main_explicit_service_url_overrides_environment(), test_main_runs_stdio_with_default_service_and_log_level(), test_main_uses_service_environment_and_normalizes_log_level() (+2 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.08
Nodes (35): test_exception_handlers_preserve_firmware_error_code(), BootMode, DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., CommandSuccessMessage, Successful command response from the Debug Helper., Return a supported DUT boot mode., validate_boot_mode() (+27 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "InputValidationError"
Cohesion: 0.09
Nodes (25): DeviceControl, ControlState, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time., Apply one configured channel's active or idle state and return device time., GpioConfigurator, GpioModeRequestSource (+17 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.49
Nodes (13): _create_capture(), datetime, MonkeyPatch, Path, _store(), test_atomic_write_failure_preserves_existing_pointer(), test_basic_not_observable_session_is_baseline_eligible(), test_dangling_or_corrupt_pointer_fails_reads_and_mutations() (+5 more)

### Community 73 - "enhanced_serial_io.py"
Cohesion: 0.10
Nodes (20): _close_without_masking_primary(), _DtrControl, open_async_enhanced_serial_adapter(), OpenSerialConnection, _OwnedStreamReader, Protocol, setter, Concrete stream and exact-write I/O for one Enhanced serial connection. (+12 more)

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 76 - "CaptureWorkflow"
Cohesion: 0.13
Nodes (27): CaptureWorkflow, Own the complete lifecycle of one finite capture session., FakeCaptureEventSource, FakeMonotonicClock, LifecycleCaptureEventSource, BackendEvent, Record a finite Enhanced fixture stream and return its summary., run_enhanced_capture_fixture() (+19 more)

### Community 77 - "Ring Buffer Sizing Plan"
Cohesion: 0.18
Nodes (13): Revision A and Phase 1 Hardware Acceptance, 32 KiB UART RX Ring Buffer, Buffer Integrity Reporting, Drop-Oldest Overflow Policy, RP2040 Memory Budget, Ring Buffer Sizing Plan, Ring Buffer Validation Gate, Ring Buffer Acceptance Checklist (+5 more)

### Community 78 - "DUTchMate Project Context"
Cohesion: 0.17
Nodes (13): Backend-Independent Host Pipeline, Phase 1A Basic Backend, Phase 1B Enhanced Backend, Enhanced NDJSON Protocol Contract, Normalized Backend Contract, AI-Assisted Embedded Debugging, Human and AI Clients, Normalized Evidence Boundary (+5 more)

### Community 79 - "test_reconnect_evidence.py"
Cohesion: 0.44
Nodes (12): _create_active_session(), parametrize, Path, _snapshot_for_segment(), test_disconnect_and_resume_append_segment_lifecycle_evidence(), test_disconnect_quota_rejection_keeps_summary_without_detailed_event(), test_reconnect_quota_rejection_does_not_publish_new_segment(), test_resume_rejects_incompatible_backend_without_writing() (+4 more)

### Community 80 - "FakeAsyncSerialReader"
Cohesion: 0.08
Nodes (21): FakeAsyncSerialReader, Fails if shutdown leaves the sole reader blocked or closes it more than once., Fails if pending-frame overflow loses its exact bounded size context., Fails if a second hello is accepted as evidence or connection state., Fails if an orphan response discards valid evidence preceding it., Fails if concurrent starts each own a reader or do not share one hello., Fails if hello resolves before all same-batch event semantics are valid., Fails if same-batch evidence still terminalizes a valid hello handshake. (+13 more)

### Community 82 - "zephyr_dut/src/main.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "dutchmate_usb_connection_run"
Cohesion: 0.07
Nodes (41): dutchmate_cdc_tx_initialize(), dmh_command_executor_init(), dutchmate_command_runtime_discard_input(), dutchmate_command_runtime_end_epoch(), dutchmate_command_runtime_faulted(), dutchmate_command_runtime_initialize(), dutchmate_command_runtime_start_epoch(), main() (+33 more)

### Community 84 - "build_session_evidence"
Cohesion: 0.07
Nodes (58): build_session_evidence(), EvidenceLimits, Deterministic, bounded excerpts from one validated native session., Assemble bounded, priority-selected evidence without changing stored facts., SessionEvidence, _evidence_fault(), _integer(), _jsonl_objects() (+50 more)

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): _build_harness(), CompletedProcess, Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "gpio_config/config.py"
Cohesion: 0.16
Nodes (20): GpioConfigError, HardwareControlMapping, load_hardware_gpio_config(), _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName (+12 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "BackendInfo"
Cohesion: 0.11
Nodes (20): enhanced_replacement_snapshot(), NoopDeviceControl, BackendEvent, BaseException, ControlState, Path, QueueSource, Catch startup health omitting initial identity, segment, or integrity. (+12 more)

### Community 90 - "GPIO Configuration Semantics"
Cohesion: 0.18
Nodes (11): Control Channel State Model, Commanded Boot Mode State, GPIO Configuration Semantics, Role and DUT Signal Identifier Contract, Runtime GPIO Override Semantics, Safe High-Impedance Behavior, Semantic Control Workflows, GPIO Validation Order (+3 more)

### Community 91 - "Enhanced Asynchronous Serial I/O Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Connection And Resource Ownership, `dutchmate_core.backends.enhanced_serial_io`, `dutchmate_core.device_connection.serial_transport`, Enhanced Asynchronous Serial I/O Design, Factory Contract, Module Ownership, Purpose (+6 more)

### Community 92 - "Reconnect and Session Semantics"
Cohesion: 0.22
Nodes (10): Backend Event Boundary Ownership, Workflow and Reconnect Deadline Precedence, Reconnect Duplicate Prevention Policy, Incremental Evidence Writes, Reconnect and Session Semantics, Process Restart Recovery, Reconnect Resume Policy, Bounded Session Segments (+2 more)

### Community 93 - "test_dependencies.py"
Cohesion: 0.47
Nodes (9): _matches_prefix(), _module_imports(), _production_modules(), Path, Executable dependency constraints for the DUTchMate modular monolith., test_core_never_depends_on_delivery_packages_or_frameworks(), test_delivery_packages_do_not_import_each_other(), test_known_application_adapter_exceptions_do_not_expand_or_go_stale() (+1 more)

### Community 94 - "test_comparison.py"
Cohesion: 0.51
Nodes (10): _active_capture(), _capture_with_lines(), _pattern(), Path, _store(), test_comparison_allows_cross_backend_logs_but_rejects_timing_mismatch(), test_comparison_reports_bounded_line_pattern_and_timing_deltas(), test_comparison_requires_designation_and_comparable_subject() (+2 more)

### Community 95 - "DUTchMate"
Cohesion: 0.25
Nodes (9): Dependency Direction, Development Status Single Source of Truth, Modular Monolith, Ports and Adapters, Basic Device Backend, DUTchMate, Enhanced Device Backend, Enhanced Host-Device Wire Contract (+1 more)

### Community 96 - "Debug Agent Context Contract"
Cohesion: 0.28
Nodes (9): Bounded Hardware Evidence, Coding Agent Context Package, Debug Agent Context Contract, Pluggable AI Provider Boundary, Remote Submission Manifest, Structured Debug Report, Bounded MCP Tool Results, Deterministic Hardware Control and Advisory AI (+1 more)

### Community 97 - "MCP Integration Plan"
Cohesion: 0.32
Nodes (8): Device Core HTTP Adapter, MCP 2026-07-28 Specification, MCP Integration Plan, Official MCP Python SDK v2, Phase 2 MCP Tool Set, Stateless MCP Layer, MCP Stdio Transport, Deferred Streamable HTTP

### Community 98 - "BlockingCloseSource"
Cohesion: 0.11
Nodes (12): BlockingCloseSource, BlockingFailingCloseSource, EventReleasedByCloseSource, FailingCloseSource, BackendEvent, BaseException, setter, test_close_while_workflow_active_is_safe_for_finally_cleanup() (+4 more)

### Community 99 - "make_adapter"
Cohesion: 0.08
Nodes (25): make_adapter(), Fails if a full FIFO drops/reorders evidence or lets its sole reader advance., Fails if the initial device frame is accepted without a hello handshake., Fails if post-hello input masks a retained parser terminal error., Fails if segment readiness consumes the first normalized evidence event., Fails if a terminal disconnect leaves readiness callers blocked or changes its…, Fails if terminal input failures leave readiness callers blocked or change…, Fails if terminalization overtakes evidence that was already accepted into FIFO. (+17 more)

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.16
Nodes (8): _basic_segment(), ConditionBackedBasicSource, _publish_after_barrier(), BackendEvent, Exception, test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator, ThreadEvent

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "ReplaceableDeviceControl"
Cohesion: 0.12
Nodes (22): ControlState, Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., ReplaceableDeviceControl, _enhanced_info(), _enhanced_settings(), FakeClock, FakeControl (+14 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "EnhancedCaptureFixtureRecorder"
Cohesion: 0.23
Nodes (9): CaptureRecordResult, Result of recording one normalized event into a capture session., EnhancedCaptureFixtureRecorder, Compose Enhanced fixture parsing with the shared capture recorder., test_stream_recorder_buffers_split_ndjson_until_complete(), test_stream_recorder_ignores_non_capture_messages(), test_stream_recorder_records_complete_uart_ndjson(), test_stream_recorder_records_multiple_capture_messages_from_one_chunk() (+1 more)

### Community 106 - ".run"
Cohesion: 0.12
Nodes (9): Return timestamp provenance once the source origin is established., CommandedBootMode, Exception, SessionWorkflow, Create one capture session., Record parsed transport messages until one fixed workflow deadline., Record supported messages until the host-monotonic deadline., Create, record, terminalize, and summarize one capture session. (+1 more)

### Community 107 - "_validator"
Cohesion: 0.47
Nodes (8): Draft202012Validator, parametrize, test_gpio_schema_accepts_safe_electrical_combinations(), test_gpio_schema_rejects_host_only_metadata(), test_gpio_schema_rejects_unsafe_electrical_combinations(), test_schema_accepts_generic_control_actions(), test_schema_rejects_legacy_role_specific_actions(), _validator()

### Community 108 - "Phase 1A Basic Hardware-in-the-Loop Validation"
Cohesion: 0.07
Nodes (27): Boot modes, Build, Create a Zephyr 4.4 workspace, DUTchMate Zephyr DUT Fixture, Flash, HIL provenance, Local protocol verification, Supported baseline (+19 more)

### Community 109 - "test_device_message_schema.py"
Cohesion: 0.48
Nodes (6): _hello(), Draft202012Validator, parametrize, test_schema_accepts_phase1_enhanced_capability(), test_schema_rejects_legacy_uart_capture_capability(), _validator()

### Community 110 - "host_to_device.schema.json"
Cohesion: 0.40
Nodes (4): $id, oneOf, $schema, title

### Community 111 - "DtrControlledSerial"
Cohesion: 0.12
Nodes (10): AttachedSerialTransport, DtrControlledSerial, OrderedCloseStreamWriter, MonkeyPatch, setter, Fails if restart can hide DTR low from the firmware epoch poller., Fails if graceful shutdown can leave the firmware epoch active., test_owned_stream_reader_holds_dtr_low_before_closing() (+2 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.40
Nodes (5): dutchmate-cli, dutchmate-core, dutchmate-debug-agent, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.19
Nodes (5): DeviceCoreClient, BaseException, TracebackType, Close the owned HTTP connection pool., Call bounded Device Core endpoints without owning hardware or sessions.

### Community 114 - "FakeDeviceControl"
Cohesion: 0.25
Nodes (6): FakeDeviceControl, _hello(), ControlState, DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status()

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.11
Nodes (26): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+18 more)

### Community 126 - "SerialFrameSink"
Cohesion: 0.15
Nodes (10): _ThreadedSerialFrameWriter, Protocol, Pyserial-compatible surface for exact host frame writes., Return the number of bytes accepted from data., Wait until accepted output is flushed., SerialFrameSink, Fails if command writes use the event loop or skip partial-write recovery., Fails if a worker-thread write loses exact accepted-byte accounting. (+2 more)

### Community 127 - "FakeEnhancedAsyncHost"
Cohesion: 0.18
Nodes (3): FakeEnhancedAsyncHost, BaseException, Synchronous test double for the service-owned async Enhanced host.

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "BackendDisconnectedError"
Cohesion: 0.16
Nodes (12): Close the source and join the single ingestion thread., backend_snapshot(), Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open., segment(), test_failed_idle_replacement_publication_closes_candidate(), test_idle_replacement_commits_snapshot_and_next_connection_generation() (+4 more)

### Community 130 - "uart_tx.c"
Cohesion: 0.12
Nodes (23): cdc_callback(), dutchmate_cdc_tx_cancel(), dutchmate_cdc_tx_poll(), dutchmate_cdc_tx_start(), command_uart_cancel(), command_uart_poll(), command_uart_start(), dutchmate_command_runtime_on_cdc_rx_ready() (+15 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "BlockingCloseStreamWriter"
Cohesion: 0.33
Nodes (3): BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 134 - "test_protocol_integration.py"
Cohesion: 0.22
Nodes (9): _client_factory(), parametrize, Request, Response, test_modern_stream_client_cancellation_stops_the_tool_call(), test_modern_stream_client_discovers_lists_and_calls_tools(), test_modern_stream_client_rejects_unsupported_protocol_version(), test_modern_stream_rejects_unadvertised_capabilities() (+1 more)

### Community 135 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

### Community 136 - "EvidenceQuotaExceeded"
Cohesion: 0.18
Nodes (6): EvidenceQuotaExceeded, Path, RuntimeError, Raised when stale native session metadata cannot be safely replaced., Raised after an evidence unit is rejected and its session is terminalized., SessionRecoveryError

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 140 - "telemetry.c"
Cohesion: 0.20
Nodes (20): append_bytes(), append_decimal(), append_literal(), dmh_buffer_overflow_encode(), dmh_buffer_status_encode(), dmh_telemetry_pending_status(), dmh_telemetry_schedule_init(), dmh_telemetry_schedule_stage_status() (+12 more)

### Community 141 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 143 - "BasicSerialPort"
Cohesion: 0.22
Nodes (6): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port.

### Community 144 - "command_runtime.c"
Cohesion: 0.27
Nodes (15): atomic_val_t, cdc_rx_thread(), command_thread(), dutchmate_command_runtime_response_sent(), dutchmate_command_runtime_take_response(), epoch_matches(), mark_runtime_fault(), publish_response() (+7 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "BasicBackendEventSource"
Cohesion: 0.13
Nodes (11): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner., Advance a workflow ingestion cursor past already-normalized UART events. (+3 more)

### Community 147 - "UartIntegrity"
Cohesion: 0.07
Nodes (19): _close_source(), _project_event_health(), BackendEvent, Exception, Service-owned continuous draining for finite capture workflows., Return the next active-workflow event or an inactivity timeout., Detach and close the consumed disconnected source., Transfer one validated replacement into the stable coordinator. (+11 more)

### Community 149 - "test_recovery.py"
Cohesion: 0.35
Nodes (14): _clock(), _create_active_native(), datetime, MonkeyPatch, parametrize, Path, _recovery_clock(), _snapshot() (+6 more)

### Community 150 - "test_enhanced_serial.py"
Cohesion: 0.10
Nodes (20): _close_after_entering(), CloseBlockingAsyncSerialReader, _compact_json_frame_of_size(), Async Enhanced serial reader lifecycle tests., Fails if terminal input overtakes accepted evidence or changes on replay., Fails if close strands hello or exposes a different terminal object., Fails if cancellation turns resource-close start into false completion., Fails if an invalid host frame reaches the serial writer. (+12 more)

### Community 151 - "test_transactions.py"
Cohesion: 0.58
Nodes (8): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_batch_rolls_back_every_file_when_metadata_write_fails(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 152 - "_run"
Cohesion: 0.32
Nodes (11): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), test_uart_event_accepts_bounded_staging_maximum(), test_uart_event_encodes_binary_and_base64_padding() (+3 more)

### Community 153 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 154 - "SegmentContext"
Cohesion: 0.06
Nodes (44): backend_snapshot(), Basic generic USB-to-UART connection, receive, and send adapter., Write a complete UART payload, retrying ordered short writes., apply_capability_policy(), BackendCapabilityError, BackendCapabilityPolicy, BackendUartSendResult, BackendWriteError (+36 more)

### Community 155 - "BackendSnapshot"
Cohesion: 0.22
Nodes (5): Accept ownership of one validated concrete replacement., _require_matching_basic_snapshot(), Return the complete Basic identity/policy/provenance snapshot., BackendSnapshot, Backend identity, effective policy, timing, and integrity for one segment.

### Community 156 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, response_harness(), _run(), test_error_response_preserves_utf8_and_escapes_json() (+2 more)

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "test_host_command_encoder.py"
Cohesion: 0.06
Nodes (57): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command. (+49 more)

### Community 159 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), telemetry_harness(), test_buffer_overflow_matches_canonical_v1_frame() (+2 more)

### Community 160 - "RP2350 Debug Helper Firmware Design"
Cohesion: 0.20
Nodes (9): Authority And Scope, Component Boundaries, Concurrency And Interrupt Ownership, Existing Contract Alignment, Failure Semantics, RP2350 Debug Helper Firmware Design, Safe-State Lifecycle, Test Boundary And Milestone Evidence (+1 more)

### Community 161 - "CaptureSessionStorage"
Cohesion: 0.04
Nodes (30): CaptureReconnect, CaptureSessionStorage, CaptureSourceMonitor, CaptureWorkflowLifecycle, BaseException, Protocol, TracebackType, Persistence operations required by the capture application service. (+22 more)

### Community 162 - ".close"
Cohesion: 0.22
Nodes (6): _CandidateCleanupFailure, _close_unpublished_candidate(), BaseException, Exception, Keep a rejected candidate's primary failure distinct from close failure., Stop reconnect activity and join the idle worker exactly once.

### Community 163 - "dmh_uart_event_encode"
Cohesion: 0.33
Nodes (6): decimal_length(), dmh_uart_event_encode(), write_base64(), write_decimal(), encode_and_write(), main()

### Community 164 - "Q: commit and tell me what is next development step in phase-1"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: commit and tell me what is next development step in phase-1, Source Nodes

### Community 165 - "Q: Before that what does Zephyr DUT exactly do and what is its use?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Before that what does Zephyr DUT exactly do and what is its use?, Source Nodes

### Community 166 - "Q: What does DMF stands for"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What does DMF stands for, Source Nodes

### Community 167 - "Q: I am ready to flash the pico."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: I am ready to flash the pico., Source Nodes

### Community 168 - "Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host., Source Nodes

### Community 169 - "Q: commit and go to next step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: commit and go to next step, Source Nodes

### Community 170 - "Q: move to next step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: move to next step, Source Nodes

### Community 171 - "Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy, Source Nodes

### Community 172 - "Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries, Source Nodes

### Community 173 - "Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests., Source Nodes

### Community 174 - "Q: Where is the shared Enhanced host-command encoding and dispatch boundary?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Where is the shared Enhanced host-command encoding and dispatch boundary?, Source Nodes

### Community 175 - "Q: How should Enhanced serial command short writes complete or report partial acceptance?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: How should Enhanced serial command short writes complete or report partial acceptance?, Source Nodes

### Community 176 - "Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?, Source Nodes

### Community 177 - "Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?, Source Nodes

### Community 178 - "Q: What is the next Phase 1 development step after pushing main?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What is the next Phase 1 development step after pushing main?, Source Nodes

### Community 179 - "Q: What remains in Phase 1 before proceeding with the Enhanced async service integration design?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What remains in Phase 1 before proceeding with the Enhanced async service integration design?, Source Nodes

### Community 180 - "Q: How should the service-owned continuous ingestion coordinator fit the current backend, runtime, session, and reconnect boundaries?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: How should the service-owned continuous ingestion coordinator fit the current backend, runtime, session, and reconnect boundaries?, Source Nodes

### Community 181 - "Q: Create a detailed implementation plan for the approved service-owned continuous ingestion coordinator design"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Create a detailed implementation plan for the approved service-owned continuous ingestion coordinator design, Source Nodes

### Community 182 - "Q: Create implementation plan for approved continuous connection monitoring design"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Create implementation plan for approved continuous connection monitoring design, Source Nodes

### Community 183 - "Q: done, what is the next steps to finish phase 1"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: done, what is the next steps to finish phase 1, Source Nodes

### Community 184 - ".__init__"
Cohesion: 0.25
Nodes (3): BackendInputKind, BackendMode, Return the same classified failure with workflow-owned context.

### Community 185 - "connection_epoch.c"
Cohesion: 0.40
Nodes (3): dmh_connection_epoch_init(), dmh_connection_epoch_update(), main()

### Community 186 - "_run_hello"
Cohesion: 0.44
Nodes (8): _build_harness(), CompletedProcess, parametrize, Path, _run_hello(), test_hello_accepts_64_byte_safe_firmware_identifier(), test_hello_matches_complete_v1_identity_and_capability_contract(), test_hello_rejects_unsafe_firmware_identifier()

### Community 187 - "load_startup_hardware_config"
Cohesion: 0.50
Nodes (4): load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., test_load_startup_hardware_config_returns_empty_config_when_missing()

### Community 189 - "backend_reconnect.py"
Cohesion: 0.07
Nodes (28): _build_async_enhanced_capture_reconnect(), build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), EnhancedReconnectHost, OpenBasicConnection, OpenCaptureReplacement, OpenEnhancedHost, Event (+20 more)

### Community 190 - "decoder_harness"
Cohesion: 0.33
Nodes (6): decoder_harness(), fixture, parametrize, Path, TempPathFactory, test_command_decoder_contract()

### Community 191 - "executor_harness"
Cohesion: 0.33
Nodes (6): executor_harness(), fixture, parametrize, Path, TempPathFactory, test_command_executor_routes_one_command_to_one_exact_response()

### Community 192 - "ingress_harness"
Cohesion: 0.33
Nodes (6): ingress_harness(), fixture, parametrize, Path, TempPathFactory, test_command_ingress_emits_one_bounded_request()

### Community 193 - "_run_states"
Cohesion: 0.61
Nodes (7): _build_harness(), Path, _run_states(), test_epoch_can_stabilize_when_first_observation_is_asserted(), test_epoch_ignores_a_transient_dtr_assertion(), test_epoch_restarts_after_each_stable_assertion(), test_epoch_starts_after_stable_dtr_and_ends_immediately_on_loss()

### Community 194 - "framer_harness"
Cohesion: 0.33
Nodes (6): framer_harness(), fixture, parametrize, Path, TempPathFactory, test_ndjson_framer_contract()

### Community 195 - "ring_harness"
Cohesion: 0.33
Nodes (6): fixture, parametrize, Path, TempPathFactory, ring_harness(), test_uart_rx_ring_invariants()

### Community 196 - "Q: What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?, Source Nodes

### Community 197 - "DUTchMate RP2350 Debug Helper Firmware"
Cohesion: 0.29
Nodes (6): Build, Current slice, DUTchMate RP2350 Debug Helper Firmware, Hardware-independent verification, Revision A mapping, USB-only stack measurement build

### Community 198 - "test_control_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_control_state_machine()

### Community 199 - "test_uart_tx_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_uart_tx_state_machine()

### Community 202 - "TerminationBarrierAdapter"
Cohesion: 0.20
Nodes (5): BlockingAsyncFrameWriter, Pause cleanup after request code has selected its terminal outcome., Fails if cancelling the response future races terminal cause selection., TerminationBarrierAdapter, test_cancellation_selects_terminal_before_response_can_be_orphaned()

### Community 203 - "dmh_output_drain_batch"
Cohesion: 0.33
Nodes (7): dmh_output_drain_one_fn, dmh_output_drain_batch(), drain_one(), main(), test_drains_until_idle(), test_error_stops_batch(), test_full_batch_keeps_draining()

### Community 204 - "test_device_core_wait.py"
Cohesion: 0.39
Nodes (14): FakeMonotonicClock, parametrize, Path, Catch capability admission before newer connected monitor health is adopted., _runtime(), _store(), test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(), test_wait_pattern_excludes_oversized_lines_and_persists_default_matches() (+6 more)

### Community 206 - "service_client.py"
Cohesion: 0.13
Nodes (15): DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, _json_object(), NoReturn, Response, RuntimeError, _raise_service_error() (+7 more)

### Community 207 - "Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?, Source Nodes

### Community 208 - "test_cdc_tx_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_cdc_tx_state_machine()

### Community 209 - "create_server"
Cohesion: 0.17
Nodes (19): create_server(), Run the server over stdio; no other MCP transport is exposed., Create one stateless MCP server with fixed protocol-facing metadata., run_stdio(), test_sdk_legacy_compatibility_path_lists_the_same_tools(), _client_factory(), Request, Response (+11 more)

### Community 212 - "server.py"
Cohesion: 0.23
Nodes (10): _execute(), ValueError, Stateless MCP server composition for the stdio delivery adapter., _tool_result(), _validation_error_payload(), DeviceCoreUnavailableError, Raised when the configured Device Core Service cannot be reached., Return a canonical structured error for a future MCP tool result. (+2 more)

### Community 213 - "collect_stack_probe.py"
Cohesion: 0.27
Nodes (10): collect(), main(), Read a frozen post-epoch Zephyr stack report over the normal USB CDC port., read_hello(), main(), _open_port(), probe(), Any (+2 more)

### Community 214 - "CaptureRecorder"
Cohesion: 0.08
Nodes (17): CaptureRecorder, _normalized_control_timestamp(), BackendEvent, Route normalized backend events into UART processing and session storage., Handle for the session this recorder writes to., Session identifier this recorder writes to., Return the next normalized event, or ``None`` after read inactivity., Whether storage has already ended this recorder's native session. (+9 more)

### Community 216 - "dmh_hello_encode"
Cohesion: 0.40
Nodes (3): dmh_hello_encode(), is_safe_firmware_byte(), main()

### Community 217 - "mcp"
Cohesion: 0.13
Nodes (22): mcp(), Run the MCP server over stdio., launch_mcp(), McpLaunchError, McpLogLevel, NoReturn, RuntimeError, Process launcher for the separately packaged MCP stdio adapter. (+14 more)

### Community 218 - "Q: Which RP2350 firmware boundaries need hardware-independent automated coverage and reproducible build instructions?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Which RP2350 firmware boundaries need hardware-independent automated coverage and reproducible build instructions?, Source Nodes

### Community 219 - "Q: what is next"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: what is next, Source Nodes

### Community 220 - "Q: ok we can do this, tell me what to do"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: ok we can do this, tell me what to do, Source Nodes

### Community 221 - "Q: I have the schematic and layout file for Eagle CAD, where you want me to add. I have the fully assembled board with me that I use it with Pico 2."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: I have the schematic and layout file for Eagle CAD, where you want me to add. I have the fully assembled board with me that I use it with Pico 2., Source Nodes

### Community 222 - "Q: Review the supplied Eagle schematic only against Revision A Pico 2/RP2350A requirements and safe-state contracts"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Review the supplied Eagle schematic only against Revision A Pico 2/RP2350A requirements and safe-state contracts, Source Nodes

### Community 223 - "Q: ok lets move to next step than"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: ok lets move to next step than, Source Nodes

### Community 224 - "Q: Trace Enhanced RP2350 UART receive events from async serial parsing through continuous ingestion to active session persistence, especially per-event processing, locking, flushing, and filesystem writes that could limit throughput"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Trace Enhanced RP2350 UART receive events from async serial parsing through continuous ingestion to active session persistence, especially per-event processing, locking, flushing, and filesystem writes that could limit throughput, Source Nodes

### Community 225 - "test_output_drain_batch_policy"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_output_drain_batch_policy()

### Community 226 - "test_uart_rx_adapter_error_policy"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_uart_rx_adapter_error_policy()

### Community 228 - "_decimal_define"
Cohesion: 0.67
Nodes (3): _decimal_define(), Path, test_cdc_tx_fifo_holds_one_maximum_evidence_frame()

### Community 232 - "test_reader_failure_is_repeatable_disconnect"
Cohesion: 0.18
Nodes (10): Exception, parametrize, Fails if invalid values can create ambiguous reader or queue bounds., Fails if EOF/read failure is raw, transient, or loses its original cause., Fails if a non-positive or non-finite command timeout reaches the writer., Fails if invalid waits are passed to asyncio instead of rejected at the…, test_constructor_rejects_invalid_bounds(), test_reader_failure_is_repeatable_disconnect() (+2 more)

### Community 233 - "_request_after_entering"
Cohesion: 0.22
Nodes (11): Event, Fails if pre-transmission cancellation poisons the shared connection., Fails if close strands a consumer or closes its owned reader twice., Fails if close strands waiters, changes errors, or transmits queued work., Fails if close cannot release a transmitted request blocked in the writer., _receive_after_entering(), _request_after_entering(), test_cancel_while_waiting_for_command_lock_keeps_connection() (+3 more)

### Community 234 - "_BoundedNewest"
Cohesion: 0.33
Nodes (4): _BoundedNewest, _T, Retain the newest coordinate-ordered records with bounded memory., _record_key()

### Community 237 - "test_service_client.py"
Cohesion: 0.22
Nodes (10): parametrize, Request, Response, _request_json(), test_client_maps_the_phase2_tool_surface_to_device_core(), test_client_preserves_structured_service_errors(), test_client_rejects_invalid_service_response_contracts(), test_client_rejects_invalid_service_urls() (+2 more)

### Community 238 - "test_close_wakes_idle_disconnect_waiter"
Cohesion: 0.50
Nodes (3): Wait until an idle source disconnect can be claimed for replacement., Catches close leaving an idle reconnect waiter blocked until its timeout., test_close_wakes_idle_disconnect_waiter()

### Community 242 - "Phase 1B Enhanced Workflow HIL Evidence"
Cohesion: 0.40
Nodes (4): Basic and Enhanced downstream evidence structure, Configured boot-mode workflow, Controlled USB reconnect, Phase 1B Enhanced Workflow HIL Evidence

### Community 243 - "TransportTimeoutError"
Cohesion: 0.20
Nodes (10): Raised when the Debug Helper does not provide a complete message in time., TransportTimeoutError, Fails if response timeout permits reuse of an uncorrelated command stream., Fails if hello timeout leaks the reader or permits a later restart., Fails if a timed-out response leaves the reader or connection reusable., Fails if a missing hello leaks the reader or exposes asyncio timeout errors., test_command_timeout_closes_connection(), test_hello_timeout_is_transport_timeout_then_disconnect() (+2 more)

### Community 248 - "Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step, Source Nodes

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **397 isolated node(s):** `dutchmate-cli`, `dutchmate-debug-agent`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema` (+392 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `Revision A Prototype Validation Checklist` (5× useful, score=3.845371563)
- `Hardware Safe Startup State` (5× useful, score=3.801932668)
- `Revision A Voltage-Domain GPIO and UART Interface` (4× useful, score=3.189720344)
- `Reconnect and Session Semantics` (4× useful, score=2.58921265)
- `DeviceCoreRuntime` (4× useful, score=2.555880294)
- `BackendEventSource` (4× useful, score=2.517083044)
- `Phase 1 Implementation Spec` (3× useful, score=2.060371873)
- `Firmware RAM Report` (3× useful, score=2.060371873)
- `Development Status` (3× useful, score=1.996558438) _(code changed — re-verify)_
- `Continuous Ingestion and Async Enhanced Adapter` (3× useful, score=1.916276225) _(code changed — re-verify)_

**Known dead ends** — questions that led nowhere; don't re-derive.
- "What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?" -> `NdjsonStreamParser`, `AsyncEnhancedSerialAdapter`

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SegmentContext` connect `SegmentContext` to `test_backend_reconnect.py`, `BackendDisconnectedError`, `workflows/capture.py`, `fixed_clock`, `FakeDeviceControl`, `metadata.py`, `create_app`, `SessionStore`, `runtime.py`, `BasicBackendEventSource`, `UartIntegrity`, `SessionSummary`, `test_recovery.py`, `DeviceCoreStatus`, `test_contracts.py`, `CaptureSessionStorage`, `DeviceCoreRuntime`, `EnhancedAsyncHost`, `CaptureSourceHealth`, `store.py`, `enhanced.py`, `helpers.py`, `fixed_clock`, `backend_reconnect.py`, `test_startup_config.py`, `models.py`, `test_capture_reconnect.py`, `CaptureWorkflow`, `test_device_core_wait.py`, `test_reconnect_evidence.py`, `.__init__`, `build_session_evidence`, `CaptureRecorder`, `BackendInfo`, `test_comparison.py`, `BlockingCloseSource`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `ReplaceableDeviceControl`, `.run`, `test_device_core_lifecycle.py`, `FakeEnhancedAsyncHost`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `SessionStore` connect `SessionStore` to `workflows/capture.py`, `EvidenceQuotaExceeded`, `fixed_clock`, `FakeDeviceControl`, `test_log_replay.py`, `SessionSummary`, `test_recovery.py`, `test_transactions.py`, `comparison.py`, `SegmentContext`, `BackendSnapshot`, `SessionPersistenceError`, `test_basic.py`, `UartReceiveEvent`, `DeviceCoreRuntime`, `CaptureSourceHealth`, `store.py`, `helpers.py`, `test_app_lifecycle.py`, `SessionComparison`, `test_device_core_uart_send.py`, `test_retrieval.py`, `fixed_clock`, `models.py`, `test_startup_config.py`, `persistence.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_retention.py`, `test_device_core_wait.py`, `CaptureWorkflow`, `test_reconnect_evidence.py`, `build_session_evidence`, `BackendInfo`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `EnhancedCaptureFixtureRecorder`, `FakeDeviceControl`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `test_backend_reconnect.py`, `workflows/capture.py`, `FakeDeviceControl`, `create_app`, `SessionStore`, `runtime.py`, `UartIntegrity`, `SessionSummary`, `service_error_from_exception`, `comparison.py`, `SegmentContext`, `BackendSnapshot`, `DeviceCoreStatus`, `CaptureSessionStorage`, `UartReceiveEvent`, `GpioModeRegistry`, `CaptureSourceHealth`, `store.py`, `enhanced.py`, `helpers.py`, `test_app_lifecycle.py`, `SessionComparison`, `test_device_core_uart_send.py`, `test_startup_config.py`, `CommandSuccessMessage`, `InputValidationError`, `CaptureWorkflow`, `test_device_core_wait.py`, `BackendInfo`, `.run`, `FakeDeviceControl`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 197 inferred relationships involving `SessionStore` (e.g. with `load_baseline_context()` and `build_session_evidence()`) actually correct?**
  _`SessionStore` has 197 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 94 INFERRED edges - model-reasoned connections that need verification._