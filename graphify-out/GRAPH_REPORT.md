# Graph Report - DUTchMate  (2026-08-25)

## Corpus Check
- 193 files · ~137,111 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3044 nodes · 8541 edges · 132 communities (118 shown, 14 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 1683 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f6f9a3d5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SessionPersistenceError
- CaptureRecorder
- test_host_command_encoder.py
- client.py
- dutchmate_cli/main.py
- DeviceCoreClient
- workflows/capture.py
- main
- settings.py
- fixed_clock
- FakeMonotonicClock
- app.py
- UartMessage
- metadata.py
- create_app
- SessionPaths
- test_validation.py
- SerialCommandTransport
- uart_send.py
- parse_device_message
- UartCaptureProcessor
- retrieval.py
- dutchmate_cli/config.py
- service_error_from_exception
- SerialPortCandidate
- models.py
- SessionStore
- RuntimeProvider
- .run
- session_store/baseline.py
- test_contracts.py
- test_enhanced.py
- UartCaptureResult
- ReconnectedCaptureSource
- evidence.py
- test_basic.py
- runtime.py
- GpioModeRegistry
- DeviceCoreRuntime
- UartLineBuffer
- GpioControlChannelState
- parser.py
- UartReceiveEvent
- dutchmate_cli/capture.py
- BackendInputError
- validation.py
- BasicBackendEventSource
- test_device_core_uart_send.py
- CaptureWorkflow
- EnhancedDeviceControl
- errors.schema.json
- helpers.py
- parse_hardware_gpio_config
- logs.py
- format_status
- store.py
- DeviceCoreSessionStorage
- SessionHandle
- .list_sessions
- Incremental Re-Extraction
- sessions.py
- SessionRecoveryResult
- test_startup_config.py
- ServiceApiError
- Phase 1 Implementation Spec
- enum
- DeviceControl
- EnhancedUartSender
- create_server
- CommandSuccessMessage
- uart_send_command
- InputValidationError
- test_baseline.py
- test_recovery.py
- test_retention.py
- WaitPatternResult
- BasicSerialPort
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- dutchmate_cli/__init__.py
- test_gpio.py
- fixture_protocol.c
- SerialPort
- CaptureSessionStorage
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- format_wait_pattern
- commands.py
- gpio_config/config.py
- GPIO Configuration Semantics
- validate_gpio_configuration
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- test_device_message_examples.py
- test_log_replay.py
- EvidenceQuotaExceeded
- test_device_core_wait.py
- enhanced.py
- HardwareGpioConfig
- Software Architecture
- log_replay.py
- DeviceActionError
- _validator
- DUTchMate Zephyr DUT Fixture
- device_actions.py
- host_to_device.schema.json
- FakeSerial
- dutchmate-core
- DeviceCoreStatus
- ScriptedBasicSerial
- _UnavailableDeviceControl
- Graph Exports
- dutchmate_mcp_server/__init__.py
- device_connection/__init__.py
- gpio_config/__init__.py
- log_processing/__init__.py
- session_store/__init__.py
- uart_capture/__init__.py
- workflows/__init__.py
- dutchmate-workspace
- FakeSerial
- .get_session
- Q: commit and tell me what is next development step in phase-1
- Q: Before that what does Zephyr DUT exactly do and what is its use?
- .__init__
- .read_event

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 229 edges
2. `DeviceCoreRuntime` - 113 edges
3. `UartReceiveEvent` - 86 edges
4. `create_app()` - 84 edges
5. `SessionHandle` - 73 edges
6. `EnhancedDeviceControl` - 72 edges
7. `FakeRuntime` - 71 edges
8. `GpioModeRegistry` - 64 edges
9. `fixed_clock()` - 62 edges
10. `SegmentContext` - 61 edges

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

## Communities (132 total, 14 thin omitted)

### Community 0 - "SessionPersistenceError"
Cohesion: 0.06
Nodes (79): Path, Raised when durable session evidence cannot be read or written., SessionPersistenceError, append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes() (+71 more)

### Community 1 - "CaptureRecorder"
Cohesion: 0.07
Nodes (51): CaptureRecorder, CaptureRecordResult, Result of recording one normalized event into a capture session., Route normalized backend events into UART processing and session storage., Create a capture session and return a recorder for it., Handle for the session this recorder writes to., Session identifier this recorder writes to., Whether storage has already ended this recorder's native session. (+43 more)

### Community 2 - "test_host_command_encoder.py"
Cohesion: 0.11
Nodes (24): configure_gpio_mode_command(), ConfigureGpioModeCommand, Build a validated `configure_gpio_mode` command., Build a validated `reset` command., Configure a DUT control role on a physical control channel., reset_command(), parametrize, test_build_configure_gpio_mode_command() (+16 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (61): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+53 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.12
Nodes (52): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+44 more)

### Community 5 - "DeviceCoreClient"
Cohesion: 0.06
Nodes (33): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+25 more)

### Community 6 - "workflows/capture.py"
Cohesion: 0.11
Nodes (31): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+23 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (47): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+39 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (46): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError, _baudrate() (+38 more)

### Community 9 - "fixed_clock"
Cohesion: 0.16
Nodes (43): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., enhanced_snapshot(), fixed_clock(), fixed_id(), MonkeyPatch (+35 more)

### Community 10 - "FakeMonotonicClock"
Cohesion: 0.19
Nodes (31): AdvancingMonotonicClock, enhanced_info(), FakeCaptureSource, FakeMonotonicClock, FakeTransport, BackendCapability, _fixed_session_time(), datetime (+23 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (51): FastAPI, FastAPI application factory for the Device Core Service., DUTchMate Device Core Service package., Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload() (+43 more)

### Community 12 - "UartMessage"
Cohesion: 0.17
Nodes (17): UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser, NDJSON stream parsing for serial byte chunks., Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline., test_feed_accepts_exact_maximum_complete_frame(), test_feed_complete_line_returns_message() (+9 more)

### Community 13 - "metadata.py"
Cohesion: 0.08
Nodes (45): Capture new UART evidence until one literal completes or time expires., _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata() (+37 more)

### Community 14 - "create_app"
Cohesion: 0.13
Nodes (39): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+31 more)

### Community 15 - "SessionPaths"
Cohesion: 0.18
Nodes (34): _existing_paths(), _latest_terminal_native(), Path, Select one native session and replay its newest bounded UART lines., replay_recent_logs(), _require_native_schema(), _select_session(), _stable_uart_snapshot() (+26 more)

### Community 16 - "test_validation.py"
Cohesion: 0.12
Nodes (27): GpioIdentifierValidationError, prepare_uart_send_payload(), Return a valid Phase 1 capture duration in seconds., Encode one public text command and enforce its final UART payload bound., Validate and return an exact 1..64-byte GPIO role or signal identifier., Raised when a public UART-send request has an invalid final payload., Raised when a GPIO role or DUT signal violates the exact identifier contract., UartSendValidationError (+19 more)

### Community 17 - "SerialCommandTransport"
Cohesion: 0.08
Nodes (32): Return an opened Enhanced command transport., open_serial_command_transport(), DeviceMessage, _pyserial_factory(), Synchronous serial transport for Debug Helper command exchange., Close the underlying serial port., Open a pyserial-backed command transport., Send NDJSON commands and read command responses from a serial port. (+24 more)

### Community 18 - "uart_send.py"
Cohesion: 0.06
Nodes (34): Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter., ReplaceableUartSender, Write a complete UART payload, retrying ordered short writes., BackendUartSendResult, BackendWriteError, Raised when a backend cannot accept a complete UART payload., Complete backend acceptance of one UART payload. (+26 more)

### Community 19 - "parse_device_message"
Cohesion: 0.09
Nodes (43): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, test_parse_buffer_overflow_message(), test_parse_buffer_status_message(), test_parse_command_error_message(), test_parse_command_success_message(), test_parse_command_success_without_timestamp() (+35 more)

### Community 20 - "UartCaptureProcessor"
Cohesion: 0.13
Nodes (18): Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission., Return bytes awaiting a line terminator for one segment and channel., UartCaptureProcessor, test_flush_channel_returns_none_for_empty_channel(), test_flush_channel_returns_none_when_channel_has_no_pending_line(), test_flush_channel_returns_partial_line_and_matches() (+10 more)

### Community 21 - "retrieval.py"
Cohesion: 0.09
Nodes (42): EvidenceTypeCount, FirstErrorReference, NativeSessionListItem, Compact summary of a debug session for workflow/API responses., Compact first-error location used by bounded session list items., Bounded native lifecycle projection for one session list item., Logical size and optional record count for one session artifact., Bounded count for one detected-pattern or hardware-event type. (+34 more)

### Community 22 - "dutchmate_cli/config.py"
Cohesion: 0.10
Nodes (38): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+30 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.09
Nodes (40): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+32 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "models.py"
Cohesion: 0.10
Nodes (35): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary() (+27 more)

### Community 26 - "SessionStore"
Cohesion: 0.21
Nodes (22): SessionDetail, Create filesystem-backed debug sessions., Return bounded schema-aware detail for one stored session., SessionStore, _create_native_session(), parametrize, Path, test_get_session_distinguishes_not_found_unsupported_and_corrupt() (+14 more)

### Community 27 - "RuntimeProvider"
Cohesion: 0.06
Nodes (19): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+11 more)

### Community 28 - ".run"
Cohesion: 0.06
Nodes (26): Return timestamp provenance once the source origin is established., BackendMode, datetime, Map one live connection source onto a new session-local segment zero., Advance a wait cursor on the wrapped source when supported., Close the live source represented by this session-local view., _SessionCaptureSource, CaptureEventSource (+18 more)

### Community 29 - "session_store/baseline.py"
Cohesion: 0.14
Nodes (28): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+20 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.07
Nodes (31): EnhancedCaptureEventSource, EnhancedNdjsonEventStream, Interim synchronous adapter for the existing Enhanced serial transport., Return device-timer provenance for this compatibility source., Advance a workflow ingestion cursor past already-normalized events., Establish timestamp provenance while retaining the first evidence event., Close the owned message source when it exposes a close operation., Parse Enhanced NDJSON chunks and expose only normalized evidence events. (+23 more)

### Community 32 - "UartCaptureResult"
Cohesion: 0.20
Nodes (7): Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Flush one segment/channel's trailing partial line, if any., Finalize trailing derived state for every segment/channel., UartCaptureResult, Persist one UART evidence unit., Persist derived UART records finalized at capture close.

### Community 33 - "ReconnectedCaptureSource"
Cohesion: 0.07
Nodes (26): build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), OpenBasicConnection, OpenCaptureReplacement, OpenEnhancedTransport, Protocol, Service-owned backend reopen and replaceable-control composition., Build the bounded reopen adapter for one selected Basic backend. (+18 more)

### Community 34 - "evidence.py"
Cohesion: 0.11
Nodes (25): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), line_limit_exceeded_event_json() (+17 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "runtime.py"
Cohesion: 0.08
Nodes (42): _backend_snapshot(), _snapshot(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), test_status_returns_connected_gpio_mapping_state(), BasicBackendConnection, BackendCapability, Basic generic USB-to-UART connection, receive, and send adapter., Return capabilities remaining after host policy is applied. (+34 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.19
Nodes (26): GpioModeRegistry, Track accepted and rejected GPIO mode configuration per control channel., GPIO role configuration state used by this runtime., fixed_clock(), datetime, parametrize, test_accept_mode_can_record_custom_role_and_idle_level(), test_accept_mode_marks_channel_configured_with_role_metadata() (+18 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.08
Nodes (20): Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError, SessionWorkflow (+12 more)

### Community 39 - "UartLineBuffer"
Cohesion: 0.10
Nodes (24): OversizedUartLine, Return the trailing partial line, if any, and clear the buffer., Finalize trailing normal or oversized state at segment/session close., Bounded descriptor for one physical line that exceeded the derived limit., Normal lines and bounded oversized-line facts produced by one input., Buffer raw UART bytes until complete newline-terminated lines are available., Raw UART bytes not yet terminated by a newline., Consume UART bytes and return complete lines. Returned line `raw` values… (+16 more)

### Community 40 - "GpioControlChannelState"
Cohesion: 0.06
Nodes (25): GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., StartupConfigRuntime, GpioModeRequestSource, Send `configure_gpio_mode` and record the firmware result. (+17 more)

### Community 41 - "parser.py"
Cohesion: 0.14
Nodes (31): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol input boundaries., Base class for host-device protocol errors. (+23 more)

### Community 42 - "UartReceiveEvent"
Cohesion: 0.21
Nodes (24): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, evidence_bytes(), datetime, Path, read_jsonl(), Path, test_append_uart_capture_appends_multiple_uart_events() (+16 more)

### Community 43 - "dutchmate_cli/capture.py"
Cohesion: 0.12
Nodes (25): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+17 more)

### Community 44 - "BackendInputError"
Cohesion: 0.14
Nodes (11): BackendInputKind, _ReaderFailure, BackendInputError, DeviceControlError, BackendMode, RuntimeError, Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context. (+3 more)

### Community 45 - "validation.py"
Cohesion: 0.13
Nodes (23): _is_unicode_whitespace(), GpioModeRequestSource, ValueError, Shared validation for public Device Core input contracts., Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., Return a valid DUT reset pulse duration in milliseconds., Validate and preserve an exact serial-port identifier. (+15 more)

### Community 46 - "BasicBackendEventSource"
Cohesion: 0.12
Nodes (11): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner. (+3 more)

### Community 47 - "test_device_core_uart_send.py"
Cohesion: 0.26
Nodes (24): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FakeSender, _fixed_time(), _hardware_events(), ProtocolFailingTransport, datetime (+16 more)

### Community 48 - "CaptureWorkflow"
Cohesion: 0.21
Nodes (23): BackendDisconnectedError, Raised when the selected backend connection is lost., CaptureWorkflow, Own the complete lifecycle of one finite capture session., _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception (+15 more)

### Community 49 - "EnhancedDeviceControl"
Cohesion: 0.17
Nodes (20): FakeTransport, _hello(), DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status(), EnhancedDeviceControl, normalize_enhanced_hello(), Translate one Enhanced hello message into backend-neutral identity. (+12 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (24): additionalProperties, minLength, type, enum, type, $id, const, properties (+16 more)

### Community 51 - "helpers.py"
Cohesion: 0.13
Nodes (19): apply_startup_hardware_config(), Apply startup GPIO mappings if a Debug Helper is already connected., disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _append_line() (+11 more)

### Community 52 - "parse_hardware_gpio_config"
Cohesion: 0.18
Nodes (21): parse_hardware_gpio_config(), Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level(), test_parse_valid_hardware_control_mapping(), test_rejects_duplicate_channel_assignments() (+13 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "format_status"
Cohesion: 0.20
Nodes (21): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+13 more)

### Community 55 - "store.py"
Cohesion: 0.09
Nodes (24): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+16 more)

### Community 56 - "DeviceCoreSessionStorage"
Cohesion: 0.12
Nodes (10): DeviceCoreSessionStorage, Protocol, Return one bounded newest-first session page., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record., Designate one eligible session as the project baseline., Clear the project baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+2 more)

### Community 57 - "SessionHandle"
Cohesion: 0.06
Nodes (28): Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session. (+20 more)

### Community 58 - ".list_sessions"
Cohesion: 0.25
Nodes (4): Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists.

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "SessionRecoveryResult"
Cohesion: 0.22
Nodes (6): Sessions abandoned at startup plus non-fatal compatibility diagnostics., SessionRecoveryResult, datetime, Path, Directory containing all sessions., Most recent startup-recovery result for this store instance.

### Community 62 - "test_startup_config.py"
Cohesion: 0.26
Nodes (18): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), MonkeyPatch, Path, ScriptedEnhancedSerial, test_basic_startup_runtime_reopens_disconnected_capture_source() (+10 more)

### Community 63 - "ServiceApiError"
Cohesion: 0.18
Nodes (15): Raised when the local Device Core Service returns an error response., ServiceApiError, _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response. (+7 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "DeviceControl"
Cohesion: 0.13
Nodes (8): Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., ReplaceableDeviceControl, DeviceControl, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse the DUT reset line and return device time., Set DUT boot mode and return device time.

### Community 67 - "EnhancedUartSender"
Cohesion: 0.12
Nodes (12): EnhancedUartSender, Translate complete UART payloads to Enhanced protocol commands., FrameTooLargeError, Raised before decoding when a device-to-host frame exceeds its bound., DeviceMessage, Consume a serial byte chunk and return parsed complete messages., CommandTransport, DeviceMessage (+4 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.21
Nodes (18): CommandSuccessMessage, Successful command response from the Debug Helper., DeviceActionRunner, Run reset/boot commands only when required GPIO roles are configured., FakeTransport, parametrize, test_action_result_rejects_mismatched_accepted_fields(), test_boot_mode_requires_configured_boot_role() (+10 more)

### Community 70 - "uart_send_command"
Cohesion: 0.17
Nodes (15): Send raw bytes to the DUT UART RX line., Build a validated `uart_send` command from raw bytes., Build a `uart_send` command from UTF-8 text., uart_send_command(), uart_send_text_command(), UartSendCommand, test_build_uart_send_command_from_bytes(), test_build_uart_send_text_command_appends_newline() (+7 more)

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
Cohesion: 0.24
Nodes (10): _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error(), test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(), test_wait_pattern_endpoint_returns_structured_capability_error(), test_wait_pattern_endpoint_serializes_authoritative_match_reference(), test_wait_pattern_timeout_is_successful_with_null_match_fields(), WaitRuntime (+2 more)

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

### Community 80 - "dutchmate_cli/__init__.py"
Cohesion: 0.10
Nodes (21): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., DUTchMate CLI package., _display(), format_uart_send() (+13 more)

### Community 81 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "SerialPort"
Cohesion: 0.17
Nodes (7): Protocol, Small pyserial-compatible surface used by the command transport., Write bytes to the serial port., Flush pending output bytes., Read bytes until a delimiter or timeout., Close the serial port., SerialPort

### Community 84 - "CaptureSessionStorage"
Cohesion: 0.11
Nodes (10): CaptureSessionStorage, Persist one accepted normalized control action., Persist immutable timestamp provenance for a capture segment., Close the current segment and return the persisted segment count., Append a validated reconnect segment and return its segment ID., Complete an active native session., Complete an active wait-pattern session., Fail an active native session. (+2 more)

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): CompletedProcess, _build_harness(), Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

### Community 88 - "commands.py"
Cohesion: 0.12
Nodes (15): BootMode, boot_mode_command(), BootModeCommand, _encode_payload(), Host-to-device protocol command encoding., Build a validated `set_boot_mode` command., Pulse the configured DUT reset line., Set the configured DUT BOOT/control pin behavior. (+7 more)

### Community 89 - "gpio_config/config.py"
Cohesion: 0.22
Nodes (15): GpioConfigError, HardwareControlMapping, _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, ValueError (+7 more)

### Community 90 - "GPIO Configuration Semantics"
Cohesion: 0.18
Nodes (11): Control Channel State Model, Commanded Boot Mode State, GPIO Configuration Semantics, Role and DUT Signal Identifier Contract, Runtime GPIO Override Semantics, Safe High-Impedance Behavior, Semantic Control Workflows, GPIO Validation Order (+3 more)

### Community 91 - "validate_gpio_configuration"
Cohesion: 0.13
Nodes (14): GpioControlChannel, GpioRoleName, Validate and preserve an exact GPIO role identifier., Validate and preserve an exact DUT schematic signal identifier., Return a known physical GPIO control channel., Validate a complete GPIO mapping in the canonical field order., A GPIO request after lexical and electrical validation., validate_gpio_channel() (+6 more)

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

### Community 99 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 100 - "EvidenceQuotaExceeded"
Cohesion: 0.22
Nodes (5): EvidenceQuotaExceeded, RuntimeError, Raised when stale native session metadata cannot be safely replaced., Raised after an evidence unit is rejected and its session is terminalized., SessionRecoveryError

### Community 101 - "test_device_core_wait.py"
Cohesion: 0.46
Nodes (12): FakeMonotonicClock, parametrize, Path, _runtime(), _store(), test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(), test_wait_pattern_excludes_oversized_lines_and_persists_default_matches(), test_wait_pattern_never_joins_requested_literal_across_reconnect() (+4 more)

### Community 102 - "enhanced.py"
Cohesion: 0.09
Nodes (30): Read and validate one Debug Helper hello message., read_enhanced_hello(), Device Core Service startup configuration helpers., Read and validate the initial Debug Helper hello message., read_startup_hello(), backend_input_error_from_protocol(), EnhancedMessageSource, _message_timestamp_us() (+22 more)

### Community 103 - "HardwareGpioConfig"
Cohesion: 0.18
Nodes (11): load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., test_load_startup_hardware_config_returns_empty_config_when_missing(), HardwareGpioConfig, load_hardware_gpio_config(), Path, Validated hardware GPIO mappings from project configuration. (+3 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "log_replay.py"
Cohesion: 0.18
Nodes (17): _BoundedNewest, _decode_uart_event(), _non_negative_int(), _normal_record(), _oversized_record(), Bounded replay of persisted native UART evidence., Retain the newest coordinate-ordered records with bounded memory., _record_key() (+9 more)

### Community 106 - "DeviceActionError"
Cohesion: 0.20
Nodes (7): DeviceActionError, _format_utc(), datetime, RuntimeError, Raised when firmware rejects a hardware action command., Pulse the DUT reset role after confirming reset GPIO configuration., Set DUT boot mode after confirming boot GPIO configuration.

### Community 107 - "_validator"
Cohesion: 0.53
Nodes (5): Draft202012Validator, parametrize, test_gpio_schema_accepts_safe_electrical_combinations(), test_gpio_schema_rejects_unsafe_electrical_combinations(), _validator()

### Community 108 - "DUTchMate Zephyr DUT Fixture"
Cohesion: 0.18
Nodes (10): Boot modes, Build, Create a Zephyr 4.4 workspace, DUTchMate Zephyr DUT Fixture, Flash, HIL provenance, Local protocol verification, Supported baseline (+2 more)

### Community 109 - "device_actions.py"
Cohesion: 0.22
Nodes (5): device_action_payload(), Serialize a successful hardware action response., DeviceActionResult, Hardware action workflows guarded by GPIO configuration state., Successful hardware action result.

### Community 110 - "host_to_device.schema.json"
Cohesion: 0.40
Nodes (4): $id, oneOf, $schema, title

### Community 111 - "FakeSerial"
Cohesion: 0.22
Nodes (3): FakeSerial, test_read_startup_hello_rejects_non_hello_message(), test_read_startup_hello_returns_initial_hello()

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreStatus"
Cohesion: 0.09
Nodes (16): DeviceCoreStatus, Current service-facing Device Core state., Designate a stored session without requiring a backend connection., Clear a named designation without requiring a backend connection., Record normalized identity for the selected connected backend., Mark the Debug Helper connection as disconnected., Return the current service-facing status snapshot., BaselineMutationResult (+8 more)

### Community 127 - ".get_session"
Cohesion: 0.40
Nodes (3): SessionDetail, Return bounded schema-aware detail for one session., Return bounded session detail without expanding raw evidence arrays.

### Community 128 - "Q: commit and tell me what is next development step in phase-1"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: commit and tell me what is next development step in phase-1, Source Nodes

### Community 129 - "Q: Before that what does Zephyr DUT exactly do and what is its use?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Before that what does Zephyr DUT exactly do and what is its use?, Source Nodes

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **106 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `SessionPersistenceError`, `CaptureRecorder`, `fixed_clock`, `FakeMonotonicClock`, `retrieval.py`, `models.py`, `session_store/baseline.py`, `UartCaptureResult`, `evidence.py`, `test_basic.py`, `runtime.py`, `UartReceiveEvent`, `test_device_core_uart_send.py`, `CaptureWorkflow`, `EnhancedDeviceControl`, `helpers.py`, `store.py`, `SessionHandle`, `.list_sessions`, `SessionRecoveryResult`, `test_startup_config.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `test_comparison.py`, `test_log_replay.py`, `EvidenceQuotaExceeded`, `test_device_core_wait.py`, `DeviceCoreStatus`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `runtime.py` to `CaptureRecorder`, `workflows/capture.py`, `fixed_clock`, `metadata.py`, `uart_send.py`, `retrieval.py`, `models.py`, `SessionStore`, `.run`, `test_contracts.py`, `test_enhanced.py`, `DeviceCoreRuntime`, `BackendInputError`, `BasicBackendEventSource`, `CaptureWorkflow`, `helpers.py`, `store.py`, `SessionHandle`, `test_reconnect_evidence.py`, `CaptureSessionStorage`, `test_comparison.py`, `test_device_core_wait.py`, `enhanced.py`, `DeviceCoreStatus`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `workflows/capture.py`, `FakeMonotonicClock`, `metadata.py`, `test_validation.py`, `uart_send.py`, `UartCaptureProcessor`, `retrieval.py`, `service_error_from_exception`, `models.py`, `.run`, `ReconnectedCaptureSource`, `runtime.py`, `GpioModeRegistry`, `GpioControlChannelState`, `BackendInputError`, `test_device_core_uart_send.py`, `CaptureWorkflow`, `EnhancedDeviceControl`, `store.py`, `DeviceCoreSessionStorage`, `SessionHandle`, `test_startup_config.py`, `DeviceControl`, `CommandSuccessMessage`, `InputValidationError`, `WaitPatternResult`, `test_device_core_wait.py`, `DeviceActionError`, `device_actions.py`, `DeviceCoreStatus`, `.get_session`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 158 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `_append_line()`) actually correct?**
  _`SessionStore` has 158 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_create_app_applies_startup_hardware_config_when_runtime_is_connected()` and `test_rejected_startup_hardware_config_is_visible_in_status()`) actually correct?**
  _`DeviceCoreRuntime` has 73 INFERRED edges - model-reasoned connections that need verification._