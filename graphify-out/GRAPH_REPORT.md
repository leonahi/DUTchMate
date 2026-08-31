# Graph Report - coordinated-background-reconnect  (2026-08-31)

## Corpus Check
- 217 files · ~198,462 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4077 nodes · 11235 edges · 164 communities (149 shown, 15 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2014 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1af0876d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ReconnectedCaptureSource
- format_status
- dutchmate_cli/config.py
- client.py
- dutchmate_cli/main.py
- test_continuous_ingestion.py
- UartLine
- main
- settings.py
- fixed_clock
- EnhancedDeviceControl
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- validation.py
- test_validation.py
- CommandSuccessMessage
- SegmentContext
- parse_device_message
- UartReceiveEvent
- log_replay.py
- ContinuousIngestionCoordinator
- service_error_from_exception
- SerialPortCandidate
- models.py
- test_retrieval.py
- DeviceActionResult
- transactions.py
- SessionListPage
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- DeviceCoreClient
- evidence.py
- test_basic.py
- BasicSerialPort
- GpioModeRegistry
- DeviceCoreRuntime
- EnhancedAsyncHost
- CaptureSourceHealth
- parser.py
- store.py
- dutchmate_cli/capture.py
- test_enhanced_serial.py
- AsyncEnhancedUartSender
- enhanced.py
- gpio_config/config.py
- Service-Owned Continuous Ingestion Design
- BasicBackendEventSource
- errors.schema.json
- modes.py
- test_app_lifecycle.py
- logs.py
- Continuous Connection And Integrity Monitoring Design
- DeviceCoreSessionStorage
- test_device_core_uart_send.py
- SessionStore
- test_capture_workflows.py
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- SessionPersistenceError
- Phase 1 Implementation Spec
- enum
- DeviceControl
- Enhanced Asynchronous Serial Adapter Design
- create_server
- device_actions.py
- test_capture_reconnect.py
- InputValidationError
- test_baseline.py
- test_recovery.py
- test_retention.py
- WaitPatternResult
- CaptureRecorder
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- parse_hardware_gpio_config
- FakeTransport
- fixture_protocol.c
- SerialPort
- CaptureWorkflow
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- dutchmate_cli/__init__.py
- format_baseline_mutation
- test_connection_monitoring.py
- GPIO Configuration Semantics
- Enhanced Asynchronous Serial I/O Design
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- BlockingCloseSource
- FakeMonotonicClock
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- Coordinated Background Reconnect Design
- backend_reconnect.py
- Software Architecture
- ServiceApiError
- BackendInputError
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- test_device_core_wait.py
- dutchmate-core
- service_client.py
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
- enhanced_serial_io.py
- fixed_id
- Enhanced Async Service Integration Design
- backend_snapshot
- BackendDisconnectedError
- File Responsibility Map
- File Responsibility Map
- _StreamWriter
- FakeSerial
- AsyncEnhancedDeviceControl
- StartupConfigRuntime
- File Map
- File Responsibility Map
- test_log_replay.py
- SessionRecoveryResult
- _UnavailableDeviceControl
- test_gpio.py
- ScriptedBasicSerial
- CaptureEventSource
- File Responsibility Map
- GpioControlChannelState
- SessionMutationLock
- _OwnedStreamReader
- test_transactions.py
- load_backend_config
- test_main.py
- .get_session
- TransportCaptureRunner
- BackendUartSendResult
- FakeStreamTransport
- commands.py
- File Responsibility Map
- test_host_command_encoder.py
- BackendSettings
- test_threaded_writer_uses_shared_exact_loop_off_event_loop
- test_threaded_writer_preserves_partial_acceptance_error
- apply_startup_hardware_config
- .get_session

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 252 edges
2. `DeviceCoreRuntime` - 136 edges
3. `UartReceiveEvent` - 104 edges
4. `SegmentContext` - 96 edges
5. `create_app()` - 90 edges
6. `EnhancedDeviceControl` - 86 edges
7. `ContinuousIngestionCoordinator` - 81 edges
8. `FakeRuntime` - 73 edges
9. `SessionHandle` - 73 edges
10. `parse_device_message()` - 71 edges

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

## Communities (164 total, 15 thin omitted)

### Community 0 - "ReconnectedCaptureSource"
Cohesion: 0.09
Nodes (33): BackendReconnectCoordinator, BaseException, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt., Stop reconnect activity and join the idle worker exactly once., Retry backend opening within the workflow-supplied monotonic deadline., RetryingCaptureReconnect (+25 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "dutchmate_cli/config.py"
Cohesion: 0.11
Nodes (35): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+27 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (61): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+53 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (54): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+46 more)

### Community 5 - "test_continuous_ingestion.py"
Cohesion: 0.14
Nodes (36): buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, parametrize, Catches malformed backend input being retried as an idle disconnect., test_active_fifo_preserves_exact_order(), test_active_telemetry_updates_health_and_enters_fifo_once() (+28 more)

### Community 6 - "UartLine"
Cohesion: 0.06
Nodes (52): PatternDetector, Pattern detection for completed UART log lines., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines., _validate_patterns(), line_limit_exceeded_event_json() (+44 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (43): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+35 more)

### Community 8 - "settings.py"
Cohesion: 0.13
Nodes (37): main(), Service entrypoint for DUTchMate., Start the Device Core Service., BackendConfig, BackendConfigError, _baudrate(), _boolean(), _finite_number() (+29 more)

### Community 9 - "fixed_clock"
Cohesion: 0.16
Nodes (44): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., enhanced_snapshot(), fixed_clock(), fixed_id(), datetime (+36 more)

### Community 10 - "EnhancedDeviceControl"
Cohesion: 0.18
Nodes (33): EnhancedDeviceControl, Translate semantic control operations to Enhanced protocol commands., enhanced_info(), FakeCaptureSource, FakeMonotonicClock, BackendCapability, BackendEvent, Exception (+25 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (52): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload(), CaptureRequest (+44 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.09
Nodes (35): HelloMessage, Typed protocol messages received from the Debug Helper., Debug Helper hello handshake., UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser, DeviceMessage, Buffer serial chunks and parse complete newline-terminated messages. (+27 more)

### Community 13 - "metadata.py"
Cohesion: 0.08
Nodes (43): test_recent_logs_payload_removes_oldest_whole_records_to_fit_body_cap(), project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _append_resumed_backend_segment(), _backend_segment_json(), _bounded_error(), _capability_policy_json() (+35 more)

### Community 14 - "create_app"
Cohesion: 0.15
Nodes (39): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, parametrize, test_boot_test_active_uses_conflict_error_contract(), test_boot_test_disconnected_uses_service_unavailable_contract() (+31 more)

### Community 15 - "validation.py"
Cohesion: 0.09
Nodes (30): BootMode, _is_unicode_whitespace(), GpioModeRequestSource, GpioRoleName, ValueError, Shared validation for public Device Core input contracts., Return a supported DUT boot mode., Validate and preserve an exact serial-port identifier. (+22 more)

### Community 16 - "test_validation.py"
Cohesion: 0.09
Nodes (35): CommandedBootMode, _validate_native_lifecycle_inputs(), GpioIdentifierValidationError, prepare_uart_send_payload(), Return a valid Phase 1 wait-pattern timeout in seconds., Validate and preserve one case-sensitive literal wait pattern., Encode one public text command and enforce its final UART payload bound., Return a positive per-session evidence budget in MiB units. (+27 more)

### Community 17 - "CommandSuccessMessage"
Cohesion: 0.06
Nodes (58): Return an opened Enhanced command transport., CommandSuccessMessage, Successful command response from the Debug Helper., _classify_serial_write_error(), open_serial_command_transport(), DeviceMessage, Exception, TransportWriteErrorCode (+50 more)

### Community 18 - "SegmentContext"
Cohesion: 0.12
Nodes (36): backend_snapshot(), enhanced_replacement_snapshot(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), _basic_segment(), test_status_returns_connected_gpio_mapping_state(), Basic generic USB-to-UART connection, receive, and send adapter., Return the complete Basic identity/policy/provenance snapshot., apply_capability_policy() (+28 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (62): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+54 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.09
Nodes (50): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, PatternMatch, A configured pattern found in one UART log line., Backend-independent UART receive processing to log lines and matches., Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches. (+42 more)

### Community 21 - "log_replay.py"
Cohesion: 0.16
Nodes (19): _BoundedNewest, _decode_uart_event(), _non_negative_int(), _normal_record(), _oversized_record(), _T, Bounded replay of persisted native UART evidence., Retain the newest coordinate-ordered records with bounded memory. (+11 more)

### Community 22 - "ContinuousIngestionCoordinator"
Cohesion: 0.08
Nodes (19): _close_source(), ContinuousIngestionCoordinator, _project_event_health(), BackendEvent, Exception, Service-owned continuous draining for finite capture workflows., Return one immutable health snapshot for the installed source., Establish a fresh cursor for one finite workflow. (+11 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (38): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+30 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "models.py"
Cohesion: 0.11
Nodes (34): _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary(), _line_excerpt(), _logs(), _native_detail() (+26 more)

### Community 26 - "test_retrieval.py"
Cohesion: 0.22
Nodes (18): _create_native_session(), parametrize, Path, test_get_session_distinguishes_not_found_unsupported_and_corrupt(), test_latest_session_returns_newest_or_none(), test_legacy_session_detail_returns_only_identity_and_artifact_sizes(), test_list_sessions_applies_positive_limit(), test_list_sessions_ignores_unrelated_files_and_directories() (+10 more)

### Community 27 - "DeviceActionResult"
Cohesion: 0.06
Nodes (21): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+13 more)

### Community 28 - "transactions.py"
Cohesion: 0.13
Nodes (34): _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file(), _error(), evidence_transaction() (+26 more)

### Community 29 - "SessionListPage"
Cohesion: 0.13
Nodes (14): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+6 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.06
Nodes (54): EnhancedCaptureEventSource, EnhancedNdjsonEventStream, EnhancedUartSender, Translate complete UART payloads to Enhanced protocol commands., Interim synchronous adapter for the existing Enhanced serial transport., Return device-timer provenance for this compatibility source., Advance a workflow ingestion cursor past already-normalized events., Establish timestamp provenance while retaining the first evidence event. (+46 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "DeviceCoreClient"
Cohesion: 0.14
Nodes (8): DeviceCoreClient, BaseException, TracebackType, Close the owned HTTP connection pool., Call bounded Device Core endpoints without owning hardware or sessions., Return a valid Phase 1 capture duration in seconds., validate_capture_duration(), test_capture_duration_accepts_phase_one_range()

### Community 34 - "evidence.py"
Cohesion: 0.11
Nodes (26): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), _match_coordinate() (+18 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "BasicSerialPort"
Cohesion: 0.18
Nodes (7): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port., Return the owned raw serial port for the receive adapter.

### Community 37 - "GpioModeRegistry"
Cohesion: 0.19
Nodes (26): GpioModeRegistry, Track accepted and rejected GPIO mode configuration per control channel., GPIO role configuration state used by this runtime., fixed_clock(), datetime, parametrize, test_accept_mode_can_record_custom_role_and_idle_level(), test_accept_mode_marks_channel_configured_with_role_metadata() (+18 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.05
Nodes (31): Return timestamp provenance once the source origin is established., Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, DeviceCoreStatus, BackendCapability, GpioModeRequestSource, GpioRoleName (+23 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.05
Nodes (43): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, BackendEvent (+35 more)

### Community 40 - "CaptureSourceHealth"
Cohesion: 0.22
Nodes (18): CaptureSourceHealth, Immutable current-source connection, integrity, and replacement projection., Return one immutable current-source health snapshot., monitored_runtime(), MutableHealthSource, FakeMonotonicClock, Path, test_basic_monitor_without_integrity_stays_not_observable() (+10 more)

### Community 41 - "parser.py"
Cohesion: 0.13
Nodes (35): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol boundaries., Base class for host-device protocol errors. (+27 more)

### Community 42 - "store.py"
Cohesion: 0.06
Nodes (53): Register service exception handlers on an app., register_error_handlers(), BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime (+45 more)

### Community 43 - "dutchmate_cli/capture.py"
Cohesion: 0.12
Nodes (25): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+17 more)

### Community 44 - "test_enhanced_serial.py"
Cohesion: 0.03
Nodes (121): BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, _compact_json_frame_of_size(), FakeAsyncFrameWriter, FakeAsyncSerialReader, make_adapter(), Event (+113 more)

### Community 45 - "AsyncEnhancedUartSender"
Cohesion: 0.14
Nodes (10): AsyncEnhancedUartSender, Translate complete UART payloads through an async Enhanced transport., AsyncCommandTransport, CommandTransport, DeviceMessage, Protocol, Transport capable of sending one host command and returning its response., Send one encoded command and return one parsed device response. (+2 more)

### Community 46 - "enhanced.py"
Cohesion: 0.05
Nodes (48): DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., backend_input_error_from_protocol(), _control_success_timestamp(), enhanced_message_timestamp_us(), enhanced_segment_context(), EnhancedMessageSource, normalize_enhanced_hello() (+40 more)

### Community 47 - "gpio_config/config.py"
Cohesion: 0.12
Nodes (24): load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., test_load_startup_hardware_config_returns_empty_config_when_missing(), GpioConfigError, HardwareGpioConfig, load_hardware_gpio_config(), _optional_string() (+16 more)

### Community 48 - "Service-Owned Continuous Ingestion Design"
Cohesion: 0.09
Nodes (21): Active, Architectural Decision, Closing / Closed, Components And Boundaries, Concurrency Invariants, Context, `ContinuousIngestionCoordinator`, Coordinator State Model (+13 more)

### Community 49 - "BasicBackendEventSource"
Cohesion: 0.11
Nodes (12): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner. (+4 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "modes.py"
Cohesion: 0.17
Nodes (15): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), BaselineRuntime, _capture(), Path (+7 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.10
Nodes (18): DUTchMate Device Core Service package., BlockingCaptureSource, ClosableFakeRuntime, _hardware_config(), NoopDeviceControl, BackendEvent, ControlState, Exception (+10 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "Continuous Connection And Integrity Monitoring Design"
Cohesion: 0.08
Nodes (24): Acceptance Criteria, Architectural Decision, Buffer Overflow, Buffer Status, Concurrency And Ownership Invariants, Context, Continuous Connection And Integrity Monitoring Design, Coordinator State And Event Projection (+16 more)

### Community 55 - "DeviceCoreSessionStorage"
Cohesion: 0.12
Nodes (10): DeviceCoreSessionStorage, Protocol, Return one bounded newest-first session page., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record., Designate one eligible session as the project baseline., Clear the project baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+2 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.21
Nodes (24): FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events(), ProtocolFailingTransport, datetime, DeviceMessage (+16 more)

### Community 57 - "SessionStore"
Cohesion: 0.05
Nodes (45): _append_line(), Reference to a created debug session., SessionHandle, CommandedBootMode, SessionDetail, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Create filesystem-backed debug sessions. (+37 more)

### Community 58 - "test_capture_workflows.py"
Cohesion: 0.21
Nodes (21): EnhancedCaptureFixtureRecorder, fixed_clock(), datetime, Record a finite Enhanced fixture stream and return its summary., Compose Enhanced fixture parsing with the shared capture recorder., run_enhanced_capture_fixture(), _failing_session_callback(), Path (+13 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.08
Nodes (70): _existing_paths(), _latest_terminal_native(), Path, _require_native_schema(), _select_session(), _stable_uart_snapshot(), _validate_snapshot_storage(), _validate_session_command() (+62 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.18
Nodes (29): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), FakeEnhancedAsyncHost, MonkeyPatch (+21 more)

### Community 63 - "SessionPersistenceError"
Cohesion: 0.11
Nodes (38): Path, Raised when durable session evidence cannot be read or written., SessionPersistenceError, append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes() (+30 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "DeviceControl"
Cohesion: 0.10
Nodes (9): EnhancedReconnectHost, Ready async Enhanced host used as source, control, and UART sender., Publish a newly connected backend control adapter., DeviceControl, ControlState, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time. (+1 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "device_actions.py"
Cohesion: 0.11
Nodes (25): Return a valid DUT reset pulse duration in milliseconds., validate_reset_pulse(), DeviceActionError, DeviceActionRunner, _format_utc(), datetime, RuntimeError, Hardware action workflows guarded by GPIO configuration state. (+17 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "InputValidationError"
Cohesion: 0.17
Nodes (21): GpioConfigurator, GpioModeRequestSource, GPIO mode configuration workflow., Configure GPIO modes through firmware and update accepted host state., Send `configure_gpio_mode` and record the firmware result., GpioConfigurationError, RuntimeError, Raised when a GPIO-controlled workflow cannot run with current state. (+13 more)

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
Cohesion: 0.22
Nodes (10): _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error(), test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(), test_wait_pattern_endpoint_returns_structured_capability_error(), test_wait_pattern_endpoint_serializes_authoritative_match_reference(), test_wait_pattern_timeout_is_successful_with_null_match_fields(), WaitRuntime (+2 more)

### Community 76 - "CaptureRecorder"
Cohesion: 0.09
Nodes (15): CaptureRecorder, BackendEvent, Route normalized backend events into UART processing and session storage., Handle for the session this recorder writes to., Session identifier this recorder writes to., Whether storage has already ended this recorder's native session., Observe terminalization performed by a coordinated external evidence writer., Record one normalized backend event into the session. (+7 more)

### Community 77 - "Ring Buffer Sizing Plan"
Cohesion: 0.18
Nodes (13): Revision A and Phase 1 Hardware Acceptance, 32 KiB UART RX Ring Buffer, Buffer Integrity Reporting, Drop-Oldest Overflow Policy, RP2040 Memory Budget, Ring Buffer Sizing Plan, Ring Buffer Validation Gate, Ring Buffer Acceptance Checklist (+5 more)

### Community 78 - "DUTchMate Project Context"
Cohesion: 0.17
Nodes (13): Backend-Independent Host Pipeline, Phase 1A Basic Backend, Phase 1B Enhanced Backend, Enhanced NDJSON Protocol Contract, Normalized Backend Contract, AI-Assisted Embedded Debugging, Human and AI Clients, Normalized Evidence Boundary (+5 more)

### Community 79 - "test_reconnect_evidence.py"
Cohesion: 0.44
Nodes (12): _create_active_session(), parametrize, Path, _snapshot_for_segment(), test_disconnect_and_resume_append_segment_lifecycle_evidence(), test_disconnect_quota_rejection_keeps_summary_without_detailed_event(), test_reconnect_quota_rejection_does_not_publish_new_segment(), test_resume_rejects_incompatible_backend_without_writing() (+4 more)

### Community 80 - "parse_hardware_gpio_config"
Cohesion: 0.16
Nodes (23): HardwareControlMapping, parse_hardware_gpio_config(), Configured mapping from a DUTchMate control channel to a DUT role., Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level() (+15 more)

### Community 81 - "FakeTransport"
Cohesion: 0.21
Nodes (14): AdvancingMonotonicClock, FakeTransport, DeviceMessage, Path, test_apply_hardware_config_requires_connection(), test_apply_hardware_config_sends_configured_modes(), test_boot_mode_tracks_only_accepted_commands_and_disconnect_invalidates_it(), test_disconnect_clears_connection_metadata_but_keeps_gpio_state() (+6 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "SerialPort"
Cohesion: 0.25
Nodes (5): Protocol, Small pyserial-compatible surface used by the command transport., Read bytes until a delimiter or timeout., Close the serial port., SerialPort

### Community 84 - "CaptureWorkflow"
Cohesion: 0.15
Nodes (9): CaptureRecordResult, CaptureWorkflow, CommandedBootMode, Exception, SessionWorkflow, Create one capture session., Result of recording one normalized event into a capture session., Own the complete lifecycle of one finite capture session. (+1 more)

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): CompletedProcess, _build_harness(), Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "dutchmate_cli/__init__.py"
Cohesion: 0.10
Nodes (19): DUTchMate CLI package., _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., default_cli_config(), MonkeyPatch (+11 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "test_connection_monitoring.py"
Cohesion: 0.15
Nodes (14): NoopDeviceControl, BackendEvent, BaseException, ControlState, Path, QueueSource, Catch startup health omitting initial identity, segment, or integrity., Catches replacement health omitting identity, integrity, or segment projection. (+6 more)

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
Cohesion: 0.13
Nodes (11): BlockingCloseSource, BlockingFailingCloseSource, EventReleasedByCloseSource, FailingCloseSource, BackendEvent, BaseException, test_close_while_workflow_active_is_safe_for_finally_cleanup(), test_concurrent_close_calls_share_exact_cleanup_error_and_close_once() (+3 more)

### Community 99 - "FakeMonotonicClock"
Cohesion: 0.14
Nodes (11): FakeCaptureEventSource, FakeMonotonicClock, LifecycleCaptureEventSource, BackendEvent, MonkeyPatch, parametrize, test_capture_activates_cursor_after_session_creation_before_callbacks(), test_capture_does_not_activate_cursor_when_session_creation_fails() (+3 more)

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.19
Nodes (7): ConditionBackedBasicSource, _publish_after_barrier(), BackendEvent, BaseException, test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator, ThreadEvent

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "backend_reconnect.py"
Cohesion: 0.06
Nodes (43): _build_async_enhanced_capture_reconnect(), build_enhanced_capture_reconnect(), _build_legacy_enhanced_capture_reconnect(), _LegacyOpenCaptureReplacement, OpenCaptureReplacement, OpenEnhancedHost, OpenEnhancedTransport, ControlState (+35 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "ServiceApiError"
Cohesion: 0.18
Nodes (15): Raised when the local Device Core Service returns an error response., ServiceApiError, _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response. (+7 more)

### Community 106 - "BackendInputError"
Cohesion: 0.14
Nodes (10): _require_matching_basic_snapshot(), _require_matching_enhanced_identity(), BackendInputKind, _ReaderFailure, BackendInputError, BackendMode, Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context. (+2 more)

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
Cohesion: 0.48
Nodes (11): FakeMonotonicClock, parametrize, Path, _runtime(), _store(), test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(), test_wait_pattern_excludes_oversized_lines_and_persists_default_matches(), test_wait_pattern_requires_effective_uart_receive_before_session_creation() (+3 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "service_client.py"
Cohesion: 0.08
Nodes (28): DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), NoReturn, Response, RuntimeError (+20 more)

### Community 114 - "test_create_app_applies_startup_hardware_config_when_runtime_is_connected"
Cohesion: 0.13
Nodes (10): Read and validate the initial Debug Helper hello message., read_startup_hello(), FakeSerial, FakeTransport, _hello(), DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_read_startup_hello_rejects_non_hello_message() (+2 more)

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.10
Nodes (28): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+20 more)

### Community 126 - "enhanced_serial_io.py"
Cohesion: 0.18
Nodes (12): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener(), _ThreadedSerialFrameWriter (+4 more)

### Community 127 - "fixed_id"
Cohesion: 0.41
Nodes (12): Create a capture session and return a recorder for it., fixed_id(), Path, read_jsonl(), Path, test_finalize_persists_unterminated_oversized_line_descriptor(), test_record_buffer_overflow_writes_hardware_event(), test_record_buffer_status_writes_hardware_event() (+4 more)

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "backend_snapshot"
Cohesion: 0.17
Nodes (10): backend_snapshot(), Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open., segment(), test_failed_idle_replacement_publication_closes_candidate(), test_idle_replacement_commits_snapshot_and_next_connection_generation(), test_replacement_segment_failure_closes_candidate_without_publishing() (+2 more)

### Community 130 - "BackendDisconnectedError"
Cohesion: 0.17
Nodes (12): Catches an idle reconnect path that requires a synthetic workflow read., Catches an idle claimant detaching a source owned by an active workflow., Catches changing active reconnect callers to require the idle claim path., test_active_terminal_consumption_permits_legacy_reconnect_detach(), test_active_workflow_cannot_claim_idle_disconnect(), test_close_while_ingestion_waits_for_replacement_stops_thread(), test_idle_disconnect_claim_detaches_without_workflow_read(), test_idle_disconnect_is_retained_for_next_workflow() (+4 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "_StreamWriter"
Cohesion: 0.15
Nodes (9): Protocol, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Open one pyserial-asyncio stream pair., _StreamReader, _StreamTransport (+1 more)

### Community 135 - "AsyncEnhancedDeviceControl"
Cohesion: 0.29
Nodes (3): AsyncEnhancedDeviceControl, ControlState, Translate semantic control operations through an async Enhanced transport.

### Community 136 - "StartupConfigRuntime"
Cohesion: 0.25
Nodes (6): GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., StartupConfigRuntime

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 140 - "SessionRecoveryResult"
Cohesion: 0.22
Nodes (7): Sessions abandoned at startup plus non-fatal compatibility diagnostics., One non-fatal startup-recovery observation for a stored session., SessionRecoveryDiagnostic, SessionRecoveryResult, Most recent startup-recovery result for this store instance., Abandon stale native active sessions without mutating other schemas., Perform startup recovery while the store-wide lock is held.

### Community 141 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 144 - "CaptureEventSource"
Cohesion: 0.13
Nodes (9): Accept ownership of one validated concrete replacement., Transfer one validated replacement into the stable coordinator., Return the latest timestamp provenance published by the source., _source_segment(), Map one live connection source onto a new session-local segment zero., Advance a wait cursor on the wrapped source when supported., _SessionCaptureSource, CaptureEventSource (+1 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "GpioControlChannelState"
Cohesion: 0.08
Nodes (19): Apply startup hardware control mappings., Configure a control channel GPIO mode., _format_utc_timestamp(), GpioControlChannelState, GpioModeRejection, datetime, GpioControlChannel, GpioModeRequestSource (+11 more)

### Community 147 - "SessionMutationLock"
Cohesion: 0.10
Nodes (15): CaptureReconnect, CaptureSourceMonitor, CaptureWorkflowLifecycle, BaseException, Protocol, TracebackType, Shared guard that serializes active-session evidence mutations., Acquire the mutation guard. (+7 more)

### Community 148 - "_OwnedStreamReader"
Cohesion: 0.22
Nodes (4): _OwnedStreamReader, BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 149 - "test_transactions.py"
Cohesion: 0.57
Nodes (7): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 150 - "load_backend_config"
Cohesion: 0.29
Nodes (7): load_backend_config(), Any, Path, Load backend/UART configuration from a TOML file., _toml_module(), Path, test_load_backend_config_reads_shared_project_toml()

### Community 151 - "test_main.py"
Cohesion: 0.33
Nodes (3): Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn()

### Community 152 - ".get_session"
Cohesion: 0.40
Nodes (3): SessionDetail, Return bounded schema-aware detail for one session., Return bounded session detail without expanding raw evidence arrays.

### Community 153 - "TransportCaptureRunner"
Cohesion: 0.40
Nodes (3): Record parsed transport messages until one fixed workflow deadline., Record supported messages until the host-monotonic deadline., TransportCaptureRunner

### Community 154 - "BackendUartSendResult"
Cohesion: 0.06
Nodes (32): Publish a newly connected UART-send adapter., Write a complete UART payload, retrying ordered short writes., BackendCapabilityError, BackendUartSendResult, BackendWriteError, RuntimeError, Raised when an operation is disabled or unsupported by the backend., Raised when a backend cannot accept a complete UART payload. (+24 more)

### Community 156 - "commands.py"
Cohesion: 0.11
Nodes (18): ConfigureGpioModeCommand, _encode_payload(), PulseControlCommand, Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a `uart_send` command from UTF-8 text., Configure the electrical behavior of a physical control channel., Pulse one configured physical control channel. (+10 more)

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "test_host_command_encoder.py"
Cohesion: 0.08
Nodes (39): configure_gpio_mode_command(), pulse_control_command(), Build a validated `configure_gpio_mode` command., Build a validated `pulse_control` command., Build a validated `set_control_state` command., Build a validated `uart_send` command from raw bytes., set_control_state_command(), uart_send_command() (+31 more)

### Community 159 - "BackendSettings"
Cohesion: 0.11
Nodes (19): build_basic_capture_reconnect(), OpenBasicConnection, Build coordinated idle and active reopen for one selected Basic backend., Open one raw Basic connection from resolved settings., Return an opened Basic connection., _basic_settings(), FakeBasicSerial, test_basic_active_candidate_uses_coordinator_and_replaces_sender() (+11 more)

### Community 162 - "apply_startup_hardware_config"
Cohesion: 0.67
Nodes (3): apply_startup_hardware_config(), Apply startup GPIO mappings if a Debug Helper is already connected., test_apply_startup_hardware_config_skips_disconnected_runtime()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **251 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+246 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `fixed_clock`, `EnhancedDeviceControl`, `test_log_replay.py`, `SessionRecoveryResult`, `SegmentContext`, `UartReceiveEvent`, `test_transactions.py`, `models.py`, `test_retrieval.py`, `SessionListPage`, `evidence.py`, `test_basic.py`, `DeviceCoreRuntime`, `CaptureSourceHealth`, `store.py`, `modes.py`, `test_app_lifecycle.py`, `test_device_core_uart_send.py`, `test_capture_workflows.py`, `retrieval.py`, `test_startup_config.py`, `SessionPersistenceError`, `test_capture_reconnect.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `FakeTransport`, `test_connection_monitoring.py`, `test_comparison.py`, `FakeMonotonicClock`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `test_device_core_wait.py`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `test_device_core_lifecycle.py`, `fixed_id`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `ReconnectedCaptureSource`, `backend_snapshot`, `fixed_clock`, `EnhancedDeviceControl`, `metadata.py`, `CaptureEventSource`, `SessionMutationLock`, `UartReceiveEvent`, `models.py`, `TransportCaptureRunner`, `BackendUartSendResult`, `test_contracts.py`, `test_enhanced.py`, `DeviceCoreRuntime`, `EnhancedAsyncHost`, `CaptureSourceHealth`, `store.py`, `enhanced.py`, `BasicBackendEventSource`, `modes.py`, `SessionStore`, `test_capture_workflows.py`, `retrieval.py`, `test_startup_config.py`, `DeviceControl`, `test_capture_reconnect.py`, `CaptureRecorder`, `test_reconnect_evidence.py`, `CaptureWorkflow`, `test_comparison.py`, `backend_reconnect.py`, `BackendInputError`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `ReconnectedCaptureSource`, `UartLine`, `EnhancedDeviceControl`, `test_validation.py`, `CaptureEventSource`, `SegmentContext`, `GpioControlChannelState`, `UartReceiveEvent`, `SessionMutationLock`, `.get_session`, `models.py`, `BackendUartSendResult`, `DeviceActionResult`, `SessionListPage`, `GpioModeRegistry`, `CaptureSourceHealth`, `store.py`, `test_app_lifecycle.py`, `DeviceCoreSessionStorage`, `test_device_core_uart_send.py`, `SessionStore`, `retrieval.py`, `test_startup_config.py`, `DeviceControl`, `device_actions.py`, `InputValidationError`, `WaitPatternResult`, `FakeTransport`, `CaptureWorkflow`, `test_connection_monitoring.py`, `BackendInputError`, `test_device_core_wait.py`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 181 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()`) actually correct?**
  _`SessionStore` has 181 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 91 INFERRED edges - model-reasoned connections that need verification._