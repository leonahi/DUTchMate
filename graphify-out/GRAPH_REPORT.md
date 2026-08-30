# Graph Report - service-continuous-ingestion  (2026-08-30)

## Corpus Check
- 211 files · ~180,220 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3819 nodes · 10457 edges · 167 communities (152 shown, 15 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 1913 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2f03b022`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_backend_reconnect.py
- format_status
- test_host_command_encoder.py
- client.py
- dutchmate_cli/main.py
- ContinuousIngestionCoordinator
- UartLine
- main
- settings.py
- fixed_clock
- EnhancedDeviceControl
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- test_transactions.py
- validation.py
- SerialCommandTransport
- runtime.py
- parse_device_message
- UartReceiveEvent
- log_replay.py
- ValueError
- service_error_from_exception
- SerialPortCandidate
- comparison.py
- test_retrieval.py
- DeviceCoreStatus
- SessionPersistenceError
- SessionListPage
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- service_client.py
- evidence.py
- test_basic.py
- backends/__init__.py
- GpioModeRegistry
- DeviceCoreRuntime
- EnhancedAsyncHost
- enhanced_serial_io.py
- parser.py
- session_store/baseline.py
- dutchmate_cli/capture.py
- FakeAsyncFrameWriter
- AsyncEnhancedUartSender
- enhanced.py
- parse_hardware_gpio_config
- Service-Owned Continuous Ingestion Design
- BackendInputError
- errors.schema.json
- modes.py
- test_app_lifecycle.py
- dutchmate_cli/__init__.py
- _StreamWriter
- BaselineMutationResult
- test_device_core_uart_send.py
- SessionStore
- CaptureRecorder
- Incremental Re-Extraction
- sessions.py
- store.py
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
- BasicSerialPort
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- FakeAsyncSerialReader
- FakeTransport
- fixture_protocol.c
- SerialPort
- SegmentContext
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- format_wait_pattern
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
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- test_enhanced_serial.py
- ReconnectedCaptureSource
- Software Architecture
- UartSendSessionStorage
- gpio_config/config.py
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- FakeMonotonicClock
- dutchmate-core
- DeviceCoreClient
- test_create_app_applies_startup_hardware_config_when_runtime_is_connected
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
- _OwnedStreamReader
- ScriptedBasicSerial
- Enhanced Async Service Integration Design
- TerminationBarrierAdapter
- Event
- test_reader_failure_is_repeatable_disconnect
- File Responsibility Map
- _summary_from_metadata
- runtime_test_support.py
- SessionRecoveryResult
- DeviceActionError
- File Map
- File Responsibility Map
- test_log_replay.py
- _validate_native_lifecycle_inputs
- test_send.py
- test_gpio.py
- field_validator
- _encode_payload
- FakeStreamTransport
- GpioControlChannelState
- .__exit__
- HardwareGpioConfig
- pulse_control_command
- test_threaded_writer_uses_shared_exact_loop_off_event_loop
- test_threaded_writer_preserves_partial_acceptance_error
- LineProcessing
- device_actions.py
- AsyncEnhancedDeviceControl
- ._read_serial_message
- set_control_state_command
- File Responsibility Map
- commands.py
- _UnavailableDeviceControl
- GpioConfigurationError
- .list_sessions
- _BoundedNewest
- .__init__
- GpioIdentifierValidationError
- project_diagnostic_detail
- enhanced_async.py

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 243 edges
2. `DeviceCoreRuntime` - 124 edges
3. `UartReceiveEvent` - 101 edges
4. `create_app()` - 85 edges
5. `EnhancedDeviceControl` - 82 edges
6. `SegmentContext` - 80 edges
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

## Communities (167 total, 15 thin omitted)

### Community 0 - "test_backend_reconnect.py"
Cohesion: 0.09
Nodes (16): _basic_settings(), ClosableSource, FakeBasicSerial, FakeClock, FakeControl, FakeSourceOwner, BackendEvent, ControlState (+8 more)

### Community 1 - "format_status"
Cohesion: 0.20
Nodes (21): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+13 more)

### Community 2 - "test_host_command_encoder.py"
Cohesion: 0.13
Nodes (22): configure_gpio_mode_command(), ConfigureGpioModeCommand, Build a validated `configure_gpio_mode` command., Build a validated `uart_send` command from raw bytes., Configure the electrical behavior of a physical control channel., uart_send_command(), parametrize, test_build_configure_gpio_mode_command() (+14 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (64): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+56 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (56): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, _display(), format_boot_mode_result(), format_reset_result() (+48 more)

### Community 5 - "ContinuousIngestionCoordinator"
Cohesion: 0.07
Nodes (52): _close_source(), ContinuousIngestionCoordinator, BackendEvent, Exception, Return to idle draining and discard unread workflow events., Return the next active-workflow event or an inactivity timeout., Retain active events because workflow activation owns cursor freshness., Detach and close the consumed disconnected source. (+44 more)

### Community 6 - "UartLine"
Cohesion: 0.06
Nodes (52): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+44 more)

### Community 7 - "main"
Cohesion: 0.08
Nodes (49): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+41 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (48): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError, _baudrate() (+40 more)

### Community 9 - "fixed_clock"
Cohesion: 0.16
Nodes (45): BufferStatusEvent, Enhanced-backend UART receive-buffer telemetry., enhanced_snapshot(), evidence_bytes(), fixed_clock(), fixed_id(), datetime, Path (+37 more)

### Community 10 - "EnhancedDeviceControl"
Cohesion: 0.23
Nodes (30): EnhancedDeviceControl, Translate semantic control operations to Enhanced protocol commands., enhanced_info(), FakeCaptureSource, BackendCapability, _fixed_session_time(), datetime, MonkeyPatch (+22 more)

### Community 11 - "app.py"
Cohesion: 0.06
Nodes (50): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload() (+42 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.11
Nodes (28): HelloMessage, Typed protocol messages received from the Debug Helper., Debug Helper hello handshake., UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser, DeviceMessage, Buffer serial chunks and parse complete newline-terminated messages. (+20 more)

### Community 13 - "metadata.py"
Cohesion: 0.18
Nodes (13): _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _metadata_segment(), datetime (+5 more)

### Community 14 - "create_app"
Cohesion: 0.14
Nodes (39): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+31 more)

### Community 15 - "test_transactions.py"
Cohesion: 0.56
Nodes (8): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_keeps_unit_when_expected_metadata_was_written(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 16 - "validation.py"
Cohesion: 0.10
Nodes (36): Capture new UART evidence until one literal completes or time expires., _is_unicode_whitespace(), prepare_uart_send_payload(), Shared validation for public Device Core input contracts., Return a valid Phase 1 wait-pattern timeout in seconds., Validate and preserve one case-sensitive literal wait pattern., Encode one public text command and enforce its final UART payload bound., Return a positive per-session evidence budget in MiB units. (+28 more)

### Community 17 - "SerialCommandTransport"
Cohesion: 0.07
Nodes (50): Return an opened Enhanced command transport., _classify_serial_write_error(), open_serial_command_transport(), Exception, TransportWriteErrorCode, _pyserial_factory(), Synchronous serial transport for Debug Helper command exchange., Close the underlying serial port. (+42 more)

### Community 18 - "runtime.py"
Cohesion: 0.06
Nodes (33): Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter., ReplaceableUartSender, Write a complete UART payload, retrying ordered short writes., BackendCapabilityError, BackendUartSendResult, BackendWriteError, DeviceControlError (+25 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (62): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+54 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.08
Nodes (48): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, line_limit_exceeded_event_json(), OversizedUartLine, Bounded descriptor for one physical line that exceeded the derived limit., Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches. (+40 more)

### Community 21 - "log_replay.py"
Cohesion: 0.12
Nodes (47): _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path, Bounded replay of persisted native UART evidence. (+39 more)

### Community 22 - "ValueError"
Cohesion: 0.17
Nodes (15): BootMode, GpioModeRequestSource, ValueError, Return a supported DUT boot mode., Return a supported GPIO electrical mode., Return a supported GPIO logic level., Validate the complete Phase 1 GPIO electrical-mode matrix., Return a known GPIO request source. (+7 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (38): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+30 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "comparison.py"
Cohesion: 0.11
Nodes (31): Register service exception handlers on an app., register_error_handlers(), test_recent_logs_payload_removes_oldest_whole_records_to_fit_body_cap(), _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary() (+23 more)

### Community 26 - "test_retrieval.py"
Cohesion: 0.22
Nodes (18): _create_native_session(), parametrize, Path, test_get_session_distinguishes_not_found_unsupported_and_corrupt(), test_latest_session_returns_newest_or_none(), test_legacy_session_detail_returns_only_identity_and_artifact_sizes(), test_list_sessions_applies_positive_limit(), test_list_sessions_ignores_unrelated_files_and_directories() (+10 more)

### Community 27 - "DeviceCoreStatus"
Cohesion: 0.06
Nodes (21): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+13 more)

### Community 28 - "SessionPersistenceError"
Cohesion: 0.12
Nodes (38): Raised when durable session evidence cannot be read or written., Filesystem paths for the required Phase 1 session files., SessionPaths, SessionPersistenceError, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups() (+30 more)

### Community 29 - "SessionListPage"
Cohesion: 0.12
Nodes (16): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+8 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.06
Nodes (53): EnhancedCaptureEventSource, EnhancedNdjsonEventStream, EnhancedUartSender, Translate complete UART payloads to Enhanced protocol commands., Interim synchronous adapter for the existing Enhanced serial transport., Return device-timer provenance for this compatibility source., Establish timestamp provenance while retaining the first evidence event., Close the owned message source when it exposes a close operation. (+45 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "service_client.py"
Cohesion: 0.11
Nodes (18): DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), NoReturn, Response, RuntimeError (+10 more)

### Community 34 - "evidence.py"
Cohesion: 0.13
Nodes (21): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), _match_coordinate() (+13 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "backends/__init__.py"
Cohesion: 0.08
Nodes (31): _backend_snapshot(), Return an opened Basic connection., test_status_returns_connected_gpio_mapping_state(), BasicBackendConnection, BackendCapability, Return capabilities remaining after host policy is applied., Close the underlying serial port., An opened Basic serial port and its immutable backend identity. (+23 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.19
Nodes (26): GpioModeRegistry, Track accepted and rejected GPIO mode configuration per control channel., GPIO role configuration state used by this runtime., fixed_clock(), datetime, parametrize, test_accept_mode_can_record_custom_role_and_idle_level(), test_accept_mode_marks_channel_configured_with_role_metadata() (+18 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.09
Nodes (20): Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError, SessionWorkflow (+12 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.06
Nodes (38): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), OpenAsyncEnhancedAdapter, Any, BackendEvent, ControlState, DeviceMessage (+30 more)

### Community 40 - "enhanced_serial_io.py"
Cohesion: 0.18
Nodes (12): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener(), _ThreadedSerialFrameWriter (+4 more)

### Community 41 - "parser.py"
Cohesion: 0.12
Nodes (37): Single-owner asynchronous adapter for one Enhanced serial connection., InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol boundaries. (+29 more)

### Community 42 - "session_store/baseline.py"
Cohesion: 0.10
Nodes (32): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+24 more)

### Community 43 - "dutchmate_cli/capture.py"
Cohesion: 0.12
Nodes (25): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+17 more)

### Community 44 - "FakeAsyncFrameWriter"
Cohesion: 0.08
Nodes (23): FakeAsyncFrameWriter, Fails if same-batch response success masks invalid input or drops its prefix., Fails if post-transmission cancellation leaves an orphan response path., Fails if response timeout permits reuse of an uncorrelated command stream., Fails if command routing consumes or reorders interleaved UART evidence., Fails if a response overtakes earlier evidence blocked outside the FIFO., Fails if a second uncorrelated command is written before the first resolves., Fails if async routing replaces write accounting or its repeatable terminal. (+15 more)

### Community 45 - "AsyncEnhancedUartSender"
Cohesion: 0.14
Nodes (10): AsyncEnhancedUartSender, Translate complete UART payloads through an async Enhanced transport., AsyncCommandTransport, CommandTransport, DeviceMessage, Protocol, Transport capable of sending one host command and returning its response., Send one encoded command and return one parsed device response. (+2 more)

### Community 46 - "enhanced.py"
Cohesion: 0.06
Nodes (47): BackendDisconnectedError, BackendInfo, BufferOverflowEvent, Raised when the selected backend connection is lost., Identity and physical capabilities reported by one selected backend., Observed Enhanced-backend UART receive-buffer loss., enhanced_message_timestamp_us(), enhanced_segment_context() (+39 more)

### Community 47 - "parse_hardware_gpio_config"
Cohesion: 0.16
Nodes (23): HardwareControlMapping, parse_hardware_gpio_config(), Configured mapping from a DUTchMate control channel to a DUT role., Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level() (+15 more)

### Community 48 - "Service-Owned Continuous Ingestion Design"
Cohesion: 0.09
Nodes (21): Active, Architectural Decision, Closing / Closed, Components And Boundaries, Concurrency Invariants, Context, `ContinuousIngestionCoordinator`, Coordinator State Model (+13 more)

### Community 49 - "BackendInputError"
Cohesion: 0.07
Nodes (21): BackendInputKind, BasicBackendEventSource, BackendEvent, Basic generic USB-to-UART connection, receive, and send adapter., Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation. (+13 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "modes.py"
Cohesion: 0.20
Nodes (14): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _capture(), Path, _store() (+6 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.10
Nodes (18): DUTchMate Device Core Service package., BlockingCaptureSource, ClosableFakeRuntime, _hardware_config(), NoopDeviceControl, BackendEvent, ControlState, Exception (+10 more)

### Community 53 - "dutchmate_cli/__init__.py"
Cohesion: 0.13
Nodes (19): DUTchMate CLI package., _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int() (+11 more)

### Community 54 - "_StreamWriter"
Cohesion: 0.15
Nodes (9): Protocol, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Open one pyserial-asyncio stream pair., _StreamReader, _StreamTransport (+1 more)

### Community 55 - "BaselineMutationResult"
Cohesion: 0.05
Nodes (24): BaselineRuntime, SessionDetail, DeviceCoreSessionStorage, Protocol, SessionDetail, Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record. (+16 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.24
Nodes (26): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events() (+18 more)

### Community 57 - "SessionStore"
Cohesion: 0.06
Nodes (34): _append_line(), Reference to a created debug session., SessionHandle, CommandedBootMode, SessionDetail, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Create filesystem-backed debug sessions. (+26 more)

### Community 58 - "CaptureRecorder"
Cohesion: 0.06
Nodes (61): CaptureRecorder, CaptureRecordResult, BackendEvent, Result of recording one normalized event into a capture session., Route normalized backend events into UART processing and session storage., Create a capture session and return a recorder for it., Handle for the session this recorder writes to., Session identifier this recorder writes to. (+53 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "store.py"
Cohesion: 0.06
Nodes (56): test_capture_summary_serializes_bounded_first_error_evidence(), EvidenceTypeCount, FirstError, FirstErrorReference, LegacySessionDetail, LegacySessionListItem, MatchExcerpt, NativeSessionListItem (+48 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.19
Nodes (27): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), FakeEnhancedAsyncHost, MonkeyPatch (+19 more)

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
Cohesion: 0.21
Nodes (19): CommandSuccessMessage, Successful command response from the Debug Helper., DeviceActionRunner, Run reset/boot commands only when required GPIO roles are configured., FakeTransport, parametrize, test_action_result_rejects_mismatched_accepted_fields(), test_boot_mode_requires_configured_boot_role() (+11 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.24
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "InputValidationError"
Cohesion: 0.21
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

### Community 76 - "BasicSerialPort"
Cohesion: 0.18
Nodes (7): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port., Return the owned raw serial port for the receive adapter.

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
Nodes (19): FakeAsyncSerialReader, Fails if an orphan response discards valid evidence preceding it., Fails if concurrent starts each own a reader or do not share one hello., Fails if hello resolves before all same-batch event semantics are valid., Fails if same-batch evidence still terminalizes a valid hello handshake., Fails if hello resolves before later same-batch input is validated., Fails if a non-blocking evidence poll is rejected as an invalid timeout., Fails if discarding queued evidence masks a retained terminal error. (+11 more)

### Community 81 - "FakeTransport"
Cohesion: 0.29
Nodes (13): FakeTransport, DeviceMessage, Path, test_apply_hardware_config_requires_connection(), test_apply_hardware_config_sends_configured_modes(), test_boot_mode_tracks_only_accepted_commands_and_disconnect_invalidates_it(), test_disconnect_clears_connection_metadata_but_keeps_gpio_state(), test_initial_status_is_disconnected_with_unconfigured_gpio() (+5 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "SerialPort"
Cohesion: 0.25
Nodes (5): Protocol, Small pyserial-compatible surface used by the command transport., Read bytes until a delimiter or timeout., Close the serial port., SerialPort

### Community 84 - "SegmentContext"
Cohesion: 0.05
Nodes (43): Service-owned continuous draining for finite capture workflows., Return the latest timestamp provenance published by the source., _source_segment(), BackendSnapshot, Backend identity, effective policy, timing, and integrity for one segment., Return timestamp provenance once the source origin is established., Session-local connection segment and its timestamp provenance., SegmentContext (+35 more)

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): CompletedProcess, _build_harness(), Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "make_adapter"
Cohesion: 0.09
Nodes (23): make_adapter(), Fails if a second hello is accepted as evidence or connection state., Fails if hello timeout leaks the reader or permits a later restart., Fails if an uncorrelated response is dropped or exposed as evidence., Fails if the initial device frame is accepted without a hello handshake., Fails if post-hello input masks a retained parser terminal error., Fails if terminalization overtakes evidence that was already accepted into FIFO., Fails if cancelling an event wait leaves queue or terminal waiter tasks pending. (+15 more)

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

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.17
Nodes (8): _basic_segment(), ConditionBackedBasicSource, _publish_after_barrier(), BackendEvent, BaseException, test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator, ThreadEvent

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "test_enhanced_serial.py"
Cohesion: 0.11
Nodes (18): _compact_json_frame_of_size(), Async Enhanced serial reader lifecycle tests., Fails if close strands hello or exposes a different terminal object., Fails if an invalid host frame reaches the serial writer., Fails if evidence is not normalized in wire order from its first timestamp., Fails if discarding a workflow cursor affects the sole reader or parser., Fails if a full bounded queue lets the sole reader advance before a drain., Fails if a missing hello leaks the reader or exposes asyncio timeout errors. (+10 more)

### Community 103 - "ReconnectedCaptureSource"
Cohesion: 0.08
Nodes (28): build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), OpenBasicConnection, OpenCaptureReplacement, OpenEnhancedTransport, Protocol, Service-owned backend reopen and replaceable-control composition., Build the bounded reopen adapter for one selected Basic backend. (+20 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "UartSendSessionStorage"
Cohesion: 0.29
Nodes (5): Protocol, Perturbation evidence operations required by UART send., Append an admitted pre-dispatch attempt., Append the matching post-dispatch result., UartSendSessionStorage

### Community 106 - "gpio_config/config.py"
Cohesion: 0.10
Nodes (27): GpioConfigError, load_hardware_gpio_config(), _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, Path (+19 more)

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

### Community 111 - "FakeMonotonicClock"
Cohesion: 0.24
Nodes (14): FakeMonotonicClock, BackendEvent, Exception, FakeMonotonicClock, parametrize, Path, _runtime(), _store() (+6 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.10
Nodes (17): DeviceCoreClient, BaseException, TracebackType, Close the owned HTTP connection pool., Call bounded Device Core endpoints without owning hardware or sessions., parametrize, Response, _request_json() (+9 more)

### Community 114 - "test_create_app_applies_startup_hardware_config_when_runtime_is_connected"
Cohesion: 0.13
Nodes (10): Read and validate the initial Debug Helper hello message., read_startup_hello(), FakeSerial, FakeTransport, _hello(), DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_read_startup_hello_rejects_non_hello_message() (+2 more)

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.14
Nodes (22): BlockingCloseCaptureSource, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch later close calls returning before the first cleanup outcome is known., Catch close returning while reconnect can still publish a live replacement. (+14 more)

### Community 126 - "_OwnedStreamReader"
Cohesion: 0.22
Nodes (4): _OwnedStreamReader, BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 127 - "ScriptedBasicSerial"
Cohesion: 0.20
Nodes (3): Exception, ScriptedBasicSerial, ScriptedEnhancedSerial

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "TerminationBarrierAdapter"
Cohesion: 0.14
Nodes (9): BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, Fails if cancellation turns resource-close start into false completion., Pause cleanup after request code has selected its terminal outcome., Fails if cancelling the response future races terminal cause selection., TerminationBarrierAdapter, test_cancellation_selects_terminal_before_response_can_be_orphaned() (+1 more)

### Community 130 - "Event"
Cohesion: 0.22
Nodes (11): Event, Fails if pre-transmission cancellation poisons the shared connection., Fails if close strands a consumer or closes its owned reader twice., Fails if close strands waiters, changes errors, or transmits queued work., Fails if close cannot release a transmitted request blocked in the writer., _receive_after_entering(), _request_after_entering(), test_cancel_while_waiting_for_command_lock_keeps_connection() (+3 more)

### Community 131 - "test_reader_failure_is_repeatable_disconnect"
Cohesion: 0.18
Nodes (10): Exception, parametrize, Fails if EOF/read failure is raw, transient, or loses its original cause., Fails if a non-positive or non-finite command timeout reaches the writer., Fails if invalid waits are passed to asyncio instead of rejected at the…, Fails if invalid values can create ambiguous reader or queue bounds., test_constructor_rejects_invalid_bounds(), test_reader_failure_is_repeatable_disconnect() (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "_summary_from_metadata"
Cohesion: 0.19
Nodes (14): _native_state(), _optional_backend_mode(), _optional_capability_policy(), _optional_integrity(), _optional_object(), _optional_str(), _optional_string_tuple(), BackendMode (+6 more)

### Community 135 - "SessionRecoveryResult"
Cohesion: 0.13
Nodes (11): RuntimeError, Sessions abandoned at startup plus non-fatal compatibility diagnostics., Raised when stale native session metadata cannot be safely replaced., SessionRecoveryError, SessionRecoveryResult, datetime, Path, Directory containing all sessions. (+3 more)

### Community 136 - "DeviceActionError"
Cohesion: 0.16
Nodes (9): Return a valid DUT reset pulse duration in milliseconds., validate_reset_pulse(), DeviceActionError, _format_utc(), datetime, RuntimeError, Raised when firmware rejects a hardware action command., Pulse the DUT reset role after confirming reset GPIO configuration. (+1 more)

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 140 - "_validate_native_lifecycle_inputs"
Cohesion: 0.33
Nodes (6): _native_workflow(), _optional_positive_number(), CommandedBootMode, SessionWorkflow, _require_positive_number(), _validate_native_lifecycle_inputs()

### Community 141 - "test_send.py"
Cohesion: 0.22
Nodes (9): _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., MonkeyPatch, test_format_forced_send_reports_attempt_and_evidence_pair(), test_send_client_forwards_text_flags_without_raw_encoding(), test_send_client_validates_final_payload_before_http() (+1 more)

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 144 - "_encode_payload"
Cohesion: 0.21
Nodes (6): _encode_payload(), Apply the active or idle behavior of one configured control channel., SetControlStateCommand, test_host_command_encoder_accepts_exact_total_frame_limit(), test_host_command_encoder_emits_unescaped_utf8(), test_host_command_encoder_rejects_frame_above_total_limit()

### Community 146 - "GpioControlChannelState"
Cohesion: 0.10
Nodes (16): _format_utc_timestamp(), GpioControlChannelState, GpioModeRejection, datetime, GpioControlChannel, GpioModeRequestSource, GpioRoleName, Return current states for all physical control channels. (+8 more)

### Community 147 - ".__exit__"
Cohesion: 0.50
Nodes (3): BaseException, TracebackType, Release the mutation guard.

### Community 148 - "HardwareGpioConfig"
Cohesion: 0.12
Nodes (14): apply_startup_hardware_config(), load_startup_hardware_config(), GpioRoleName, Path, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings. (+6 more)

### Community 149 - "pulse_control_command"
Cohesion: 0.18
Nodes (11): pulse_control_command(), PulseControlCommand, Build a validated `pulse_control` command., Pulse one configured physical control channel., test_build_pulse_control_command(), test_encode_pulse_control_command_as_ndjson(), test_pulse_control_command_matches_canonical_example(), test_pulse_control_rejects_boolean_pulse() (+3 more)

### Community 152 - "LineProcessing"
Cohesion: 0.36
Nodes (7): _initial_metadata(), _integrity_json(), _line_processing_json(), _optional_line_processing(), _record_line_processing(), LineProcessing, Bounded derived-line processing status for one session.

### Community 153 - "device_actions.py"
Cohesion: 0.18
Nodes (5): Pulse the configured DUT reset role., Set the configured DUT boot/control role., DeviceActionResult, Hardware action workflows guarded by GPIO configuration state., Successful hardware action result.

### Community 154 - "AsyncEnhancedDeviceControl"
Cohesion: 0.29
Nodes (3): AsyncEnhancedDeviceControl, ControlState, Translate semantic control operations through an async Enhanced transport.

### Community 155 - "._read_serial_message"
Cohesion: 0.24
Nodes (5): Advance a workflow ingestion cursor past already-normalized events., DeviceMessage, Return the oldest queued or newly read Debug Helper message., Return and clear messages queued during command requests., Send one encoded command and return the matching command response.

### Community 156 - "set_control_state_command"
Cohesion: 0.20
Nodes (10): Build a validated `set_control_state` command., set_control_state_command(), GpioControlChannel, Return a known physical GPIO control channel., validate_gpio_channel(), test_build_set_control_state_command(), test_encode_set_control_state_command_as_ndjson(), test_set_control_state_command_matches_canonical_example() (+2 more)

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "commands.py"
Cohesion: 0.31
Nodes (8): Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a `uart_send` command from UTF-8 text., uart_send_text_command(), UartSendCommand, test_build_uart_send_text_command_appends_newline(), test_build_uart_send_text_command_can_preserve_text_without_newline(), test_uart_send_text_preserves_existing_crlf_and_completes_trailing_cr()

### Community 159 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 160 - "GpioConfigurationError"
Cohesion: 0.25
Nodes (6): GpioModeRequestSource, Send `configure_gpio_mode` and record the firmware result., GpioConfigurationError, RuntimeError, Raised when a GPIO-controlled workflow cannot run with current state., GpioRoleRequirementState

### Community 161 - ".list_sessions"
Cohesion: 0.25
Nodes (4): Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists.

### Community 162 - "_BoundedNewest"
Cohesion: 0.40
Nodes (3): _BoundedNewest, _T, Retain the newest coordinate-ordered records with bounded memory.

### Community 164 - "GpioIdentifierValidationError"
Cohesion: 0.40
Nodes (3): GpioIdentifierValidationError, Raised when a GPIO role or DUT signal violates the exact identifier contract., IdentifierValidationReason

### Community 165 - "project_diagnostic_detail"
Cohesion: 0.40
Nodes (4): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _bounded_error()

### Community 166 - "enhanced_async.py"
Cohesion: 0.67
Nodes (3): _open_host_on_owner_loop(), _OpenedHost, Synchronous service facade for one owner-loop Enhanced async adapter.

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **199 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+194 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `SessionRecoveryResult`, `fixed_clock`, `EnhancedDeviceControl`, `test_log_replay.py`, `test_transactions.py`, `runtime.py`, `UartReceiveEvent`, `comparison.py`, `test_retrieval.py`, `SessionPersistenceError`, `SessionListPage`, `.list_sessions`, `test_basic.py`, `session_store/baseline.py`, `enhanced.py`, `modes.py`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `CaptureRecorder`, `store.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `FakeTransport`, `SegmentContext`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `FakeMonotonicClock`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `test_backend_reconnect.py`, `ContinuousIngestionCoordinator`, `_summary_from_metadata`, `fixed_clock`, `metadata.py`, `runtime.py`, `DeviceCoreStatus`, `test_contracts.py`, `test_enhanced.py`, `backends/__init__.py`, `enhanced_async.py`, `EnhancedAsyncHost`, `DeviceCoreRuntime`, `parser.py`, `enhanced.py`, `BackendInputError`, `modes.py`, `SessionStore`, `CaptureRecorder`, `store.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `test_reconnect_evidence.py`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `FakeMonotonicClock`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `UartLine`, `DeviceActionError`, `EnhancedDeviceControl`, `validation.py`, `runtime.py`, `GpioControlChannelState`, `UartReceiveEvent`, `comparison.py`, `device_actions.py`, `DeviceCoreStatus`, `SessionListPage`, `GpioConfigurationError`, `backends/__init__.py`, `GpioModeRegistry`, `session_store/baseline.py`, `enhanced.py`, `BackendInputError`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionStore`, `store.py`, `test_startup_config.py`, `DeviceControl`, `CommandSuccessMessage`, `InputValidationError`, `WaitPatternResult`, `FakeTransport`, `SegmentContext`, `ReconnectedCaptureSource`, `FakeMonotonicClock`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 172 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()`) actually correct?**
  _`SessionStore` has 172 INFERRED edges - model-reasoned connections that need verification._
- **Are the 83 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_create_app_applies_startup_hardware_config_when_runtime_is_connected()`) actually correct?**
  _`DeviceCoreRuntime` has 83 INFERRED edges - model-reasoned connections that need verification._