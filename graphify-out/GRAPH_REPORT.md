# Graph Report - enhanced-async-service-integration  (2026-08-29)

## Corpus Check
- 207 files · ~168,883 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3628 nodes · 9966 edges · 153 communities (140 shown, 13 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1838 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e32e3c9a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FakeControl
- format_status
- test_host_command_encoder.py
- client.py
- dutchmate_cli/main.py
- AsyncEnhancedSerialAdapter
- workflows/capture.py
- main
- settings.py
- fixed_clock
- EnhancedDeviceControl
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- test_transactions.py
- test_validation.py
- SerialCommandTransport
- BackendUartSendResult
- parse_device_message
- UartReceiveEvent
- log_replay.py
- validation.py
- service_error_from_exception
- SerialPortCandidate
- store.py
- SessionStore
- DeviceCoreStatus
- SessionPaths
- SessionListPage
- BackendInfo
- test_enhanced.py
- test_enhanced_serial_io.py
- service_client.py
- evidence.py
- test_basic.py
- SegmentContext
- GpioModeRegistry
- device_actions.py
- EnhancedAsyncHost
- enhanced_serial_io.py
- parser.py
- SessionPersistenceError
- dutchmate_cli/capture.py
- FakeAsyncFrameWriter
- AsyncEnhancedDeviceControl
- enhanced.py
- parse_hardware_gpio_config
- test_dut.py
- contracts.py
- errors.schema.json
- helpers.py
- test_app_lifecycle.py
- logs.py
- _StreamWriter
- BaselineMutationResult
- test_device_core_uart_send.py
- SessionHandle
- CaptureRecorder
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- DeviceControl
- Enhanced Asynchronous Serial Adapter Design
- create_server
- CommandSuccessMessage
- test_capture_reconnect.py
- InputValidationError
- test_baseline.py
- test_recovery.py
- test_retention.py
- WaitPatternResult
- BasicBackendConnection
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- FakeAsyncSerialReader
- FakeTransport
- fixture_protocol.c
- SerialPort
- CaptureWorkflow
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- dutchmate_cli/__init__.py
- format_baseline_mutation
- make_adapter
- GPIO Configuration Semantics
- Enhanced Asynchronous Serial I/O Design
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- test_device_message_examples.py
- dutchmate_cli/config.py
- CaptureEventSource
- AsyncSerialReader
- test_enhanced_serial.py
- ReconnectedCaptureSource
- Software Architecture
- runtime.py
- gpio_config/config.py
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- test_device_core_wait.py
- dutchmate-core
- DeviceCoreClient
- startup.py
- test_runtime_close_during_reconnect_waits_and_rejects_replacement
- Graph Exports
- dutchmate_mcp_server/__init__.py
- device_connection/__init__.py
- gpio_config/__init__.py
- log_processing/__init__.py
- session_store/__init__.py
- uart_capture/__init__.py
- workflows/__init__.py
- dutchmate-workspace
- _OwnedStreamReader
- FakeSerial
- Enhanced Async Service Integration Design
- TerminationBarrierAdapter
- _request_after_entering
- test_reader_failure_is_repeatable_disconnect
- File Responsibility Map
- _summary_from_metadata
- FakeSerial
- test_service_client.py
- DeviceCoreRuntime
- File Map
- File Responsibility Map
- test_log_replay.py
- _initial_metadata
- format_uart_send
- HardwareGpioConfig
- validate_wait_pattern
- load_startup_hardware_config
- FakeStreamTransport
- GpioControlChannelState
- SessionMutationLock
- StartupConfigRuntime
- validate_capture_duration
- test_threaded_writer_uses_shared_exact_loop_off_event_loop
- test_threaded_writer_preserves_partial_acceptance_error
- LineProcessing

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 235 edges
2. `DeviceCoreRuntime` - 121 edges
3. `UartReceiveEvent` - 100 edges
4. `create_app()` - 85 edges
5. `EnhancedDeviceControl` - 80 edges
6. `SegmentContext` - 75 edges
7. `FakeRuntime` - 73 edges
8. `SessionHandle` - 73 edges
9. `parse_device_message()` - 71 edges
10. `GpioModeRegistry` - 65 edges

## Surprising Connections (you probably didn't know these)
- `Ring Buffer Validation Gate` --semantically_similar_to--> `Ring Buffer Acceptance Checklist`  [INFERRED] [semantically similar]
  docs/ring_buffer_sizing_plan.md → hardware/validation/phase1_ring_buffer.md
- `Safe High-Impedance Behavior` --semantically_similar_to--> `Hardware Safe Startup State`  [INFERRED] [semantically similar]
  docs/gpio_configuration_semantics.md → hardware/schematics/revision_a.md
- `_summary_from_metadata()` --calls--> `_first_error()`  [INFERRED]
  core/src/dutchmate_core/session_store/metadata.py → apps/cli/src/dutchmate_cli/capture.py
- `CliConfig` --uses--> `BackendConfig`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py
- `parse_cli_config()` --uses--> `BackendConfigError`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DUTchMate Backend Pipeline** — readme_basic_backend, readme_enhanced_backend, readme_shared_host_processing_and_session_pipeline [EXTRACTED 1.00]
- **Graphify Operational Pipeline** — _codex_skills_graphify_skill_extraction_pipeline, _codex_skills_graphify_references_update_incremental_re_extraction, _codex_skills_graphify_skill_graph_health_check [EXTRACTED 1.00]
- **Bounded Evidence Integrity Contract** — docs_debug_agent_context_contract_bounded_hardware_evidence, docs_reconnect_session_semantics_incremental_evidence_writes, docs_software_architecture_session_store, docs_ring_buffer_sizing_plan_buffer_integrity_reporting, docs_mcp_integration_plan_bounded_tool_results [INFERRED 0.85]
- **Backend-Independent Evidence Pipeline** — docs_project_context_normalized_evidence_boundary, docs_phase1_implementation_spec_backend_independent_pipeline, docs_software_architecture_normalized_event_boundary, docs_software_architecture_backends_contracts [INFERRED 0.95]
- **Phase 1 Hardware Acceptance Gate** — docs_development_status_hardware_acceptance, docs_phase1_implementation_spec_phase1_done_criteria, docs_ring_buffer_sizing_plan_validation_gate, hardware_schematics_revision_a_prototype_validation, hardware_validation_phase1_ring_buffer_acceptance_checklist [INFERRED 0.95]

## Communities (153 total, 13 thin omitted)

### Community 0 - "FakeControl"
Cohesion: 0.29
Nodes (3): FakeControl, ControlState, test_replaceable_device_control_forwards_to_latest_adapter()

### Community 1 - "format_status"
Cohesion: 0.20
Nodes (21): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+13 more)

### Community 2 - "test_host_command_encoder.py"
Cohesion: 0.05
Nodes (57): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command. (+49 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (66): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+58 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (54): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands. (+46 more)

### Community 5 - "AsyncEnhancedSerialAdapter"
Cohesion: 0.11
Nodes (18): BackendDisconnectedError, Raised when the selected backend connection is lost., AsyncEnhancedSerialAdapter, _consume_hello_waiter_exception(), _consume_response_waiter_exception(), BackendEvent, Future, Return normalized identity after a valid hello. (+10 more)

### Community 6 - "workflows/capture.py"
Cohesion: 0.06
Nodes (55): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+47 more)

### Community 7 - "main"
Cohesion: 0.08
Nodes (49): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+41 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (47): main(), Service entrypoint for DUTchMate., Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError (+39 more)

### Community 9 - "fixed_clock"
Cohesion: 0.12
Nodes (65): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., enhanced_snapshot(), evidence_bytes(), fixed_clock(), fixed_id() (+57 more)

### Community 10 - "EnhancedDeviceControl"
Cohesion: 0.18
Nodes (30): EnhancedDeviceControl, Translate semantic control operations to Enhanced protocol commands., AdvancingMonotonicClock, FakeCaptureSource, FakeMonotonicClock, _fixed_session_time(), datetime, MonkeyPatch (+22 more)

### Community 11 - "app.py"
Cohesion: 0.06
Nodes (51): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., DUTchMate Device Core Service package., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload() (+43 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.11
Nodes (25): UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser, DeviceMessage, Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline., Return the first terminal parsing failure, if parsing has stopped., Consume a serial byte chunk and return parsed complete messages. (+17 more)

### Community 13 - "metadata.py"
Cohesion: 0.15
Nodes (14): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _append_resumed_backend_segment(), _bounded_error(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp() (+6 more)

### Community 14 - "create_app"
Cohesion: 0.14
Nodes (40): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+32 more)

### Community 15 - "test_transactions.py"
Cohesion: 0.57
Nodes (7): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 16 - "test_validation.py"
Cohesion: 0.13
Nodes (22): GpioIdentifierValidationError, prepare_uart_send_payload(), Return a valid Phase 1 wait-pattern timeout in seconds., Encode one public text command and enforce its final UART payload bound., Validate and return an exact 1..64-byte GPIO role or signal identifier., Raised when a public UART-send request has an invalid final payload., Raised when a GPIO role or DUT signal violates the exact identifier contract., UartSendValidationError (+14 more)

### Community 17 - "SerialCommandTransport"
Cohesion: 0.07
Nodes (45): Return an opened Enhanced command transport., Advance a workflow ingestion cursor past already-normalized events., open_serial_command_transport(), DeviceMessage, _pyserial_factory(), Return the oldest queued or newly read Debug Helper message., Return and clear messages queued during command requests., Close the underlying serial port. (+37 more)

### Community 18 - "BackendUartSendResult"
Cohesion: 0.09
Nodes (23): Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter., ReplaceableUartSender, Write a complete UART payload, retrying ordered short writes., BackendUartSendResult, BackendWriteError, Raised when a backend cannot accept a complete UART payload., Complete backend acceptance of one UART payload. (+15 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (62): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+54 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.12
Nodes (26): _append_line(), Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission. (+18 more)

### Community 21 - "log_replay.py"
Cohesion: 0.11
Nodes (35): _BoundedNewest, _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path (+27 more)

### Community 22 - "validation.py"
Cohesion: 0.11
Nodes (27): BootMode, _is_unicode_whitespace(), ValueError, Shared validation for public Device Core input contracts., Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., Return a valid DUT reset pulse duration in milliseconds., Return a supported DUT boot mode. (+19 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.09
Nodes (43): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+35 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "store.py"
Cohesion: 0.06
Nodes (54): test_capture_summary_serializes_bounded_first_error_evidence(), _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary(), _line_excerpt(), _logs() (+46 more)

### Community 26 - "SessionStore"
Cohesion: 0.09
Nodes (31): SessionDetail, Create filesystem-backed debug sessions., Load one authoritative reference-bearing detected-pattern record., Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists., Return bounded schema-aware detail for one stored session. (+23 more)

### Community 27 - "DeviceCoreStatus"
Cohesion: 0.06
Nodes (18): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+10 more)

### Community 28 - "SessionPaths"
Cohesion: 0.13
Nodes (36): Filesystem paths for the required Phase 1 session files., SessionPaths, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file() (+28 more)

### Community 29 - "SessionListPage"
Cohesion: 0.14
Nodes (13): Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), test_session_endpoints_use_validation_and_query_error_contracts() (+5 more)

### Community 30 - "BackendInfo"
Cohesion: 0.10
Nodes (24): BackendEventSource, BackendInfo, BackendEvent, Protocol, Identity and physical capabilities reported by one selected backend., Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source. (+16 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.05
Nodes (57): AsyncEnhancedUartSender, EnhancedCaptureEventSource, EnhancedNdjsonEventStream, EnhancedUartSender, Translate complete UART payloads to Enhanced protocol commands., Translate complete UART payloads through an async Enhanced transport., Interim synchronous adapter for the existing Enhanced serial transport., Return device-timer provenance for this compatibility source. (+49 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "service_client.py"
Cohesion: 0.11
Nodes (18): DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), NoReturn, Response, RuntimeError (+10 more)

### Community 34 - "evidence.py"
Cohesion: 0.13
Nodes (22): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), line_limit_exceeded_event_json() (+14 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "SegmentContext"
Cohesion: 0.09
Nodes (31): _backend_snapshot(), _snapshot(), test_status_returns_connected_gpio_mapping_state(), Return the complete Basic identity/policy/provenance snapshot., apply_capability_policy(), BackendCapabilityPolicy, BackendSnapshot, integrity_for_backend() (+23 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.19
Nodes (26): GpioModeRegistry, Track accepted and rejected GPIO mode configuration per control channel., GPIO role configuration state used by this runtime., fixed_clock(), datetime, parametrize, test_accept_mode_can_record_custom_role_and_idle_level(), test_accept_mode_marks_channel_configured_with_role_metadata() (+18 more)

### Community 38 - "device_actions.py"
Cohesion: 0.08
Nodes (22): DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError, SessionWorkflow, Apply configured GPIO modes after a Debug Helper hello is available., Configure one GPIO role through firmware and update runtime state. (+14 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.05
Nodes (41): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, BackendEvent (+33 more)

### Community 40 - "enhanced_serial_io.py"
Cohesion: 0.18
Nodes (12): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener(), _ThreadedSerialFrameWriter (+4 more)

### Community 41 - "parser.py"
Cohesion: 0.10
Nodes (42): InvalidUtf8Error, MalformedMessageError, ProtocolValidationError, ProtocolVersionError, Typed failures at Enhanced wire-protocol boundaries., Raised when a UTF-8 protocol frame is not valid JSON., Raised when a bounded frame body is not valid UTF-8., Raised when a JSON object does not match the v1 protocol contract. (+34 more)

### Community 42 - "SessionPersistenceError"
Cohesion: 0.09
Nodes (35): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+27 more)

### Community 43 - "dutchmate_cli/capture.py"
Cohesion: 0.12
Nodes (25): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+17 more)

### Community 44 - "FakeAsyncFrameWriter"
Cohesion: 0.08
Nodes (23): FakeAsyncFrameWriter, Fails if same-batch response success masks invalid input or drops its prefix., Fails if post-transmission cancellation leaves an orphan response path., Fails if response timeout permits reuse of an uncorrelated command stream., Fails if command routing consumes or reorders interleaved UART evidence., Fails if a response overtakes earlier evidence blocked outside the FIFO., Fails if a second uncorrelated command is written before the first resolves., Fails if async routing replaces write accounting or its repeatable terminal. (+15 more)

### Community 45 - "AsyncEnhancedDeviceControl"
Cohesion: 0.10
Nodes (14): DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., AsyncEnhancedDeviceControl, _control_success_timestamp(), ControlState, Translate semantic control operations through an async Enhanced transport., AsyncCommandTransport, CommandTransport (+6 more)

### Community 46 - "enhanced.py"
Cohesion: 0.09
Nodes (32): enhanced_message_timestamp_us(), enhanced_segment_context(), EnhancedMessageSource, normalize_enhanced_hello(), normalize_enhanced_message(), BackendEvent, DeviceMessage, Protocol (+24 more)

### Community 47 - "parse_hardware_gpio_config"
Cohesion: 0.19
Nodes (20): parse_hardware_gpio_config(), Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level(), test_rejects_duplicate_channel_assignments(), test_rejects_empty_role() (+12 more)

### Community 48 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 49 - "contracts.py"
Cohesion: 0.07
Nodes (23): BackendInputKind, BasicBackendEventSource, BackendEvent, Basic generic USB-to-UART connection, receive, and send adapter., Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation. (+15 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "helpers.py"
Cohesion: 0.20
Nodes (14): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), BaselineRuntime, _capture(), Path (+6 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.22
Nodes (10): ClosableFakeRuntime, _hardware_config(), Exception, MonkeyPatch, Catch an application shutdown that leaks the runtime it constructed., Catch application shutdown closing a runtime supplied by its caller., Catch startup cleanup that leaks its runtime or masks its primary failure., test_app_lifespan_closes_internally_constructed_runtime() (+2 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "_StreamWriter"
Cohesion: 0.15
Nodes (9): Protocol, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Open one pyserial-asyncio stream pair., _StreamReader, _StreamTransport (+1 more)

### Community 55 - "BaselineMutationResult"
Cohesion: 0.09
Nodes (14): DeviceCoreSessionStorage, Protocol, Return one bounded newest-first session page., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record., Designate one eligible session as the project baseline., Clear the project baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+6 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.26
Nodes (24): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FakeSender, _fixed_time(), _hardware_events(), ProtocolFailingTransport, datetime (+16 more)

### Community 57 - "SessionHandle"
Cohesion: 0.05
Nodes (36): Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session. (+28 more)

### Community 58 - "CaptureRecorder"
Cohesion: 0.07
Nodes (52): CaptureRecorder, CaptureRecordResult, _normalized_control_timestamp(), Result of recording one normalized event into a capture session., Route normalized backend events into UART processing and session storage., Create a capture session and return a recorder for it., Handle for the session this recorder writes to., Session identifier this recorder writes to. (+44 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.08
Nodes (62): _native_detail(), _native_item(), _stable_uart_snapshot(), _validate_session_command(), EvidenceTypeCount, FirstErrorReference, LegacySessionListItem, NativeSessionListItem (+54 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.12
Nodes (37): apply_startup_hardware_config(), build_startup_runtime(), Apply startup GPIO mappings if a Debug Helper is already connected., Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment() (+29 more)

### Community 63 - "persistence.py"
Cohesion: 0.13
Nodes (34): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+26 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "DeviceControl"
Cohesion: 0.12
Nodes (10): ControlState, Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., ReplaceableDeviceControl, DeviceControl, ControlState, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time. (+2 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.17
Nodes (19): CommandSuccessMessage, Successful command response from the Debug Helper., DeviceActionRunner, Run reset/boot commands only when required GPIO roles are configured., FakeTransport, parametrize, test_action_result_rejects_mismatched_accepted_fields(), test_boot_mode_requires_configured_boot_role() (+11 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.24
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "InputValidationError"
Cohesion: 0.23
Nodes (16): GpioConfigurator, GPIO mode configuration workflow., Configure GPIO modes through firmware and update accepted host state., InputValidationError, Raised when an application input violates a Device Core contract., FakeTransport, test_configure_mode_accepts_boot_role_with_idle_level(), test_configure_mode_records_firmware_rejection() (+8 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.49
Nodes (13): _create_capture(), datetime, MonkeyPatch, Path, _store(), test_atomic_write_failure_preserves_existing_pointer(), test_basic_not_observable_session_is_baseline_eligible(), test_dangling_or_corrupt_pointer_fails_reads_and_mutations() (+5 more)

### Community 73 - "test_recovery.py"
Cohesion: 0.38
Nodes (13): _clock(), _create_active_native(), datetime, MonkeyPatch, parametrize, Path, _recovery_clock(), test_recovery_abandons_stale_active_native_session() (+5 more)

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 75 - "WaitPatternResult"
Cohesion: 0.20
Nodes (11): Wait for one literal in new UART evidence., _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error(), test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(), test_wait_pattern_endpoint_returns_structured_capability_error(), test_wait_pattern_endpoint_serializes_authoritative_match_reference(), test_wait_pattern_timeout_is_successful_with_null_match_fields() (+3 more)

### Community 76 - "BasicBackendConnection"
Cohesion: 0.07
Nodes (18): Return an opened Basic connection., ControlState, NoReturn, _UnavailableDeviceControl, BasicBackendConnection, BasicSerialPort, BackendCapability, Protocol (+10 more)

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
Cohesion: 0.09
Nodes (19): FakeAsyncSerialReader, Fails if close strands hello or exposes a different terminal object., Fails if concurrent starts each own a reader or do not share one hello., Fails if hello resolves before all same-batch event semantics are valid., Fails if hello resolves before later same-batch input is validated., Fails if a non-blocking evidence poll is rejected as an invalid timeout., Fails if cancelling an event wait leaves queue or terminal waiter tasks pending., Fails if input terminalization leaves the only reader blocked for close(). (+11 more)

### Community 81 - "FakeTransport"
Cohesion: 0.24
Nodes (17): enhanced_info(), FakeTransport, BackendCapability, DeviceMessage, Catch runtime shutdown leaving service-visible backend metadata connected., test_runtime_close_publishes_disconnected_status(), Path, test_apply_hardware_config_requires_connection() (+9 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "SerialPort"
Cohesion: 0.25
Nodes (5): Protocol, Small pyserial-compatible surface used by the command transport., Read bytes until a delimiter or timeout., Close the serial port., SerialPort

### Community 84 - "CaptureWorkflow"
Cohesion: 0.20
Nodes (7): CaptureWorkflow, CommandedBootMode, Exception, SessionWorkflow, Create one capture session., Own the complete lifecycle of one finite capture session., Create, record, terminalize, and summarize one capture session.

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): CompletedProcess, _build_harness(), Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "dutchmate_cli/__init__.py"
Cohesion: 0.13
Nodes (16): DUTchMate CLI package., _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, parametrize (+8 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "make_adapter"
Cohesion: 0.09
Nodes (23): make_adapter(), Fails if a second hello is accepted as evidence or connection state., Fails if hello timeout leaks the reader or permits a later restart., Fails if an orphan response discards valid evidence preceding it., Fails if the initial device frame is accepted without a hello handshake., Fails if same-batch evidence still terminalizes a valid hello handshake., Fails if terminalization overtakes evidence that was already accepted into FIFO., Fails if a full bounded queue lets the sole reader advance before a drain. (+15 more)

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

### Community 98 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 99 - "dutchmate_cli/config.py"
Cohesion: 0.10
Nodes (38): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+30 more)

### Community 100 - "CaptureEventSource"
Cohesion: 0.11
Nodes (12): BackendEvent, Map one live connection source onto a new session-local segment zero., Advance a wait cursor on the wrapped source when supported., Close the live source represented by this session-local view., _SessionCaptureSource, CaptureEventSource, BackendEvent, Record parsed transport messages until one fixed workflow deadline. (+4 more)

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "test_enhanced_serial.py"
Cohesion: 0.11
Nodes (18): _compact_json_frame_of_size(), Async Enhanced serial reader lifecycle tests., Fails if an invalid host frame reaches the serial writer., Fails if an uncorrelated response is dropped or exposed as evidence., Fails if post-hello input masks a retained parser terminal error., Fails if evidence is not normalized in wire order from its first timestamp., Fails if discarding a workflow cursor affects the sole reader or parser., Fails if discarding queued evidence masks a retained terminal error. (+10 more)

### Community 103 - "ReconnectedCaptureSource"
Cohesion: 0.13
Nodes (13): OpenCaptureReplacement, Open one segment-bound replacement source., Return a fully prepared replacement or raise for a failed attempt., Retry backend opening within the workflow-supplied monotonic deadline., RetryingCaptureReconnect, ClosableSource, FakeClock, test_reconnect_closes_async_host_before_opening_synchronous_replacement() (+5 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "runtime.py"
Cohesion: 0.10
Nodes (15): Send one validated text command to the DUT UART., GPIO role configuration state tracking., datetime, Service-facing Device Core runtime composition., GpioModeRequestSource, Return a known GPIO request source., validate_gpio_source(), Protocol (+7 more)

### Community 106 - "gpio_config/config.py"
Cohesion: 0.15
Nodes (20): GpioConfigError, _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, ValueError, Load and validate hardware GPIO mapping configuration. (+12 more)

### Community 107 - "_validator"
Cohesion: 0.47
Nodes (8): Draft202012Validator, parametrize, test_gpio_schema_accepts_safe_electrical_combinations(), test_gpio_schema_rejects_host_only_metadata(), test_gpio_schema_rejects_unsafe_electrical_combinations(), test_schema_accepts_generic_control_actions(), test_schema_rejects_legacy_role_specific_actions(), _validator()

### Community 108 - "Phase 1A Basic Hardware-in-the-Loop Validation"
Cohesion: 0.07
Nodes (27): Boot modes, Build, Create a Zephyr 4.4 workspace, DUTchMate Zephyr DUT Fixture, Flash, HIL provenance, Local protocol verification, Supported baseline (+19 more)

### Community 109 - "test_device_message_schema.py"
Cohesion: 0.60
Nodes (5): _hello(), Draft202012Validator, test_schema_accepts_uart_receive_capability(), test_schema_rejects_legacy_uart_capture_capability(), _validator()

### Community 110 - "host_to_device.schema.json"
Cohesion: 0.40
Nodes (4): $id, oneOf, $schema, title

### Community 111 - "test_device_core_wait.py"
Cohesion: 0.46
Nodes (12): FakeMonotonicClock, parametrize, Path, _runtime(), _store(), test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(), test_wait_pattern_excludes_oversized_lines_and_persists_default_matches(), test_wait_pattern_never_joins_requested_literal_across_reconnect() (+4 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.17
Nodes (5): DeviceCoreClient, BaseException, TracebackType, Close the owned HTTP connection pool., Call bounded Device Core endpoints without owning hardware or sessions.

### Community 114 - "startup.py"
Cohesion: 0.15
Nodes (17): build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), OpenBasicConnection, OpenEnhancedTransport, Protocol, Service-owned backend reopen and replaceable-control composition., Build the bounded reopen adapter for one selected Basic backend., Build bounded Enhanced reopen, hello, provenance, and control replacement. (+9 more)

### Community 115 - "test_runtime_close_during_reconnect_waits_and_rejects_replacement"
Cohesion: 0.17
Nodes (14): Event, BlockingCloseCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch close returning while reconnect can still publish a live replacement., Catch a close that leaves the source owned or repeats source shutdown. (+6 more)

### Community 126 - "_OwnedStreamReader"
Cohesion: 0.22
Nodes (4): _OwnedStreamReader, BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 127 - "FakeSerial"
Cohesion: 0.10
Nodes (6): FakeSerial, BackendEvent, BaseException, Exception, ScriptedBasicSerial, ScriptedEnhancedSerial

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "TerminationBarrierAdapter"
Cohesion: 0.15
Nodes (8): _close_after_entering(), CloseBlockingAsyncSerialReader, Fails if cancellation turns resource-close start into false completion., Pause cleanup after request code has selected its terminal outcome., Fails if cancelling the response future races terminal cause selection., TerminationBarrierAdapter, test_cancellation_selects_terminal_before_response_can_be_orphaned(), test_resource_close_completion_is_shared_across_reader_cancellation_and_close()

### Community 130 - "_request_after_entering"
Cohesion: 0.18
Nodes (11): BlockingAsyncFrameWriter, Fails if pre-transmission cancellation poisons the shared connection., Fails if close strands a consumer or closes its owned reader twice., Fails if close strands waiters, changes errors, or transmits queued work., Fails if close cannot release a transmitted request blocked in the writer., _receive_after_entering(), _request_after_entering(), test_cancel_while_waiting_for_command_lock_keeps_connection() (+3 more)

### Community 131 - "test_reader_failure_is_repeatable_disconnect"
Cohesion: 0.18
Nodes (10): Exception, parametrize, Fails if EOF/read failure is raw, transient, or loses its original cause., Fails if a non-positive or non-finite command timeout reaches the writer., Fails if invalid waits are passed to asyncio instead of rejected at the…, Fails if invalid values can create ambiguous reader or queue bounds., test_constructor_rejects_invalid_bounds(), test_reader_failure_is_repeatable_disconnect() (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "_summary_from_metadata"
Cohesion: 0.19
Nodes (14): _native_state(), _optional_backend_mode(), _optional_capability_policy(), _optional_integrity(), _optional_object(), _optional_str(), _optional_string_tuple(), BackendMode (+6 more)

### Community 135 - "test_service_client.py"
Cohesion: 0.22
Nodes (10): parametrize, Response, _request_json(), test_client_maps_the_phase2_tool_surface_to_device_core(), test_client_preserves_structured_service_errors(), test_client_rejects_invalid_service_response_contracts(), test_client_rejects_invalid_service_urls(), test_client_reports_connection_failure_as_structured_unavailable() (+2 more)

### Community 136 - "DeviceCoreRuntime"
Cohesion: 0.10
Nodes (13): DeviceCoreRuntime, SessionDetail, Return bounded schema-aware detail for one session., Compose Phase 1 core services behind one service-facing object., Close the currently owned backend source exactly once., Return bounded session detail without expanding raw evidence arrays., Return recent UART evidence without requiring a backend connection., Compare stored evidence without requiring a backend connection. (+5 more)

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 140 - "_initial_metadata"
Cohesion: 0.22
Nodes (11): _backend_segment_json(), _capability_policy_json(), _initial_metadata(), _integrity_json(), _native_workflow(), _optional_positive_number(), CommandedBootMode, SessionWorkflow (+3 more)

### Community 141 - "format_uart_send"
Cohesion: 0.40
Nodes (5): _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., test_format_forced_send_reports_attempt_and_evidence_pair()

### Community 142 - "HardwareGpioConfig"
Cohesion: 0.22
Nodes (7): Apply startup hardware control mappings., HardwareControlMapping, HardwareGpioConfig, Configured mapping from a DUTchMate control channel to a DUT role., Validated hardware GPIO mappings from project configuration., Return a required control mapping or raise a configuration error., test_parse_valid_hardware_control_mapping()

### Community 143 - "validate_wait_pattern"
Cohesion: 0.22
Nodes (6): Validate and preserve one case-sensitive literal wait pattern., validate_wait_pattern(), field_validator, test_wait_pattern_accepts_exact_bounded_literals(), test_wait_pattern_rejects_invalid_literals(), ValidationInfo

### Community 144 - "load_startup_hardware_config"
Cohesion: 0.25
Nodes (8): load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., load_hardware_gpio_config(), Path, Load hardware GPIO configuration from a TOML file., Path, test_load_hardware_gpio_config_reads_toml_file()

### Community 146 - "GpioControlChannelState"
Cohesion: 0.08
Nodes (20): Configure a control channel GPIO mode., GpioModeRequestSource, Send `configure_gpio_mode` and record the firmware result., _format_utc_timestamp(), GpioControlChannelState, GpioModeRejection, datetime, GpioControlChannel (+12 more)

### Community 147 - "SessionMutationLock"
Cohesion: 0.15
Nodes (10): CaptureReconnect, BaseException, Protocol, TracebackType, Shared guard that serializes active-session evidence mutations., Acquire the mutation guard., Release the mutation guard., Backend-specific reopen operation used by a capture workflow. (+2 more)

### Community 148 - "StartupConfigRuntime"
Cohesion: 0.25
Nodes (6): GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., StartupConfigRuntime

### Community 149 - "validate_capture_duration"
Cohesion: 0.25
Nodes (6): Capture UART and telemetry messages into one filesystem session., Reset the DUT and capture its boot UART into one session., Return a valid Phase 1 capture duration in seconds., validate_capture_duration(), test_capture_duration_accepts_phase_one_range(), test_capture_duration_rejects_values_outside_exact_contract()

### Community 152 - "LineProcessing"
Cohesion: 0.47
Nodes (5): _line_processing_json(), _optional_line_processing(), _record_line_processing(), LineProcessing, Bounded derived-line processing status for one session.

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **175 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+170 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `DeviceCoreRuntime`, `fixed_clock`, `EnhancedDeviceControl`, `test_log_replay.py`, `test_transactions.py`, `UartReceiveEvent`, `store.py`, `SessionListPage`, `test_basic.py`, `SegmentContext`, `SessionPersistenceError`, `helpers.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionHandle`, `CaptureRecorder`, `retrieval.py`, `test_startup_config.py`, `persistence.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `FakeTransport`, `test_comparison.py`, `test_device_core_wait.py`, `test_runtime_close_during_reconnect_waits_and_rejects_replacement`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `AsyncEnhancedSerialAdapter`, `_summary_from_metadata`, `workflows/capture.py`, `DeviceCoreRuntime`, `fixed_clock`, `metadata.py`, `BackendUartSendResult`, `store.py`, `SessionStore`, `DeviceCoreStatus`, `BackendInfo`, `test_enhanced.py`, `EnhancedAsyncHost`, `enhanced.py`, `contracts.py`, `helpers.py`, `SessionHandle`, `CaptureRecorder`, `retrieval.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `test_reconnect_evidence.py`, `CaptureWorkflow`, `test_comparison.py`, `CaptureEventSource`, `runtime.py`, `test_device_core_wait.py`, `test_runtime_close_during_reconnect_waits_and_rejects_replacement`, `FakeSerial`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `workflows/capture.py`, `EnhancedDeviceControl`, `test_validation.py`, `BackendUartSendResult`, `GpioControlChannelState`, `UartReceiveEvent`, `validate_capture_duration`, `SessionMutationLock`, `service_error_from_exception`, `store.py`, `DeviceCoreStatus`, `SessionListPage`, `BackendInfo`, `SegmentContext`, `GpioModeRegistry`, `device_actions.py`, `SessionPersistenceError`, `contracts.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionHandle`, `retrieval.py`, `test_startup_config.py`, `DeviceControl`, `CommandSuccessMessage`, `InputValidationError`, `WaitPatternResult`, `FakeTransport`, `CaptureWorkflow`, `CaptureEventSource`, `ReconnectedCaptureSource`, `runtime.py`, `test_device_core_wait.py`, `test_runtime_close_during_reconnect_waits_and_rejects_replacement`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 164 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `_append_line()`) actually correct?**
  _`SessionStore` has 164 INFERRED edges - model-reasoned connections that need verification._
- **Are the 80 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_create_app_applies_startup_hardware_config_when_runtime_is_connected()` and `test_enhanced_startup_closes_host_when_connection_recording_fails()`) actually correct?**
  _`DeviceCoreRuntime` has 80 INFERRED edges - model-reasoned connections that need verification._