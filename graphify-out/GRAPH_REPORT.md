# Graph Report - DUTchMate  (2026-08-23)

## Corpus Check
- 185 files · ~134,080 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2986 nodes · 8450 edges · 121 communities (110 shown, 11 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 1677 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `93c606aa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- persistence.py
- CaptureRecorder
- test_host_command_encoder.py
- client.py
- dutchmate_cli/main.py
- DeviceCoreClient
- UartLine
- main
- settings.py
- enhanced_snapshot
- DeviceCoreRuntime
- app.py
- messages.py
- metadata.py
- create_app
- log_replay.py
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
- DeviceActionResult
- SegmentContext
- session_store/baseline.py
- test_contracts.py
- test_enhanced.py
- UartCaptureResult
- ReconnectedCaptureSource
- evidence.py
- test_basic.py
- BackendSnapshot
- GpioModeRegistry
- DeviceActionError
- UartLineBuffer
- runtime.py
- parser.py
- UartReceiveEvent
- dutchmate_cli/__init__.py
- enhanced.py
- ValueError
- BasicBackendEventSource
- processor.py
- test_capture_reconnect.py
- FrameTooLargeError
- errors.schema.json
- helpers.py
- parse_hardware_gpio_config
- logs.py
- format_status
- SessionListPage
- DeviceCoreSessionStorage
- SessionHandle
- SessionSummary
- Incremental Re-Extraction
- sessions.py
- store.py
- test_startup_config.py
- test_dut.py
- Phase 1 Implementation Spec
- enum
- DeviceControl
- CommandTransport
- create_server
- main
- uart_send_command
- resolve_backend_settings
- test_baseline.py
- test_recovery.py
- test_retention.py
- WaitPatternResult
- BasicSerialPort
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- format_baseline_mutation
- test_gpio.py
- reset_command
- SerialPort
- GpioIdentifierValidationError
- Revision A Voltage-Domain GPIO and UART Interface
- UartSender
- format_wait_pattern
- boot_mode_command
- commands.py
- GPIO Configuration Semantics
- _encode_payload
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- normalize_enhanced_message
- test_log_replay.py
- .__init__
- project_diagnostic_detail
- .read_event
- default_cli_config
- Software Architecture
- _replay_uart_prefix
- _validator
- host_to_device.schema.json
- .__exit__
- dutchmate-core
- DeviceCoreStatus
- Graph Exports
- dutchmate_mcp_server/__init__.py
- device_connection/__init__.py
- gpio_config/__init__.py
- log_processing/__init__.py
- session_store/__init__.py
- uart_capture/__init__.py
- workflows/__init__.py
- dutchmate-workspace

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

## Communities (121 total, 11 thin omitted)

### Community 0 - "persistence.py"
Cohesion: 0.06
Nodes (78): Filesystem paths for the required Phase 1 session files., SessionPaths, append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory() (+70 more)

### Community 1 - "CaptureRecorder"
Cohesion: 0.07
Nodes (51): CaptureRecorder, CaptureRecordResult, Result of recording one normalized event into a capture session., Route normalized backend events into UART processing and session storage., Create a capture session and return a recorder for it., Handle for the session this recorder writes to., Session identifier this recorder writes to., Whether storage has already ended this recorder's native session. (+43 more)

### Community 2 - "test_host_command_encoder.py"
Cohesion: 0.23
Nodes (14): configure_gpio_mode_command(), Build a validated `configure_gpio_mode` command., parametrize, test_build_configure_gpio_mode_command(), test_build_configure_gpio_mode_command_with_custom_role(), test_build_configure_gpio_mode_command_with_idle_level(), test_configure_gpio_mode_matches_canonical_example(), test_encode_configure_gpio_mode_command_as_ndjson() (+6 more)

### Community 3 - "client.py"
Cohesion: 0.06
Nodes (67): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+59 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (54): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+46 more)

### Community 5 - "DeviceCoreClient"
Cohesion: 0.05
Nodes (37): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+29 more)

### Community 6 - "UartLine"
Cohesion: 0.12
Nodes (28): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+20 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (47): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+39 more)

### Community 8 - "settings.py"
Cohesion: 0.16
Nodes (24): BackendConfigError, _baudrate(), _boolean(), _finite_number(), _fixed_integer(), _fixed_string(), _optional_baudrate(), _optional_table() (+16 more)

### Community 9 - "enhanced_snapshot"
Cohesion: 0.19
Nodes (25): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., test_normalizes_buffer_telemetry(), enhanced_snapshot(), Path, read_jsonl() (+17 more)

### Community 10 - "DeviceCoreRuntime"
Cohesion: 0.06
Nodes (91): EnhancedDeviceControl, Translate semantic control operations to Enhanced protocol commands., DeviceCoreRuntime, Compose Phase 1 core services behind one service-facing object., Return one bounded page without requiring a backend connection., Return recent UART evidence without requiring a backend connection., Compare stored evidence without requiring a backend connection., Mark the Debug Helper connection as disconnected. (+83 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (52): FastAPI, FastAPI application factory for the Device Core Service., DUTchMate Device Core Service package., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload(), CaptureRequest (+44 more)

### Community 12 - "messages.py"
Cohesion: 0.13
Nodes (22): Read and validate one Debug Helper hello message., read_enhanced_hello(), HelloMessage, Typed protocol messages received from the Debug Helper., Debug Helper hello handshake., UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser (+14 more)

### Community 13 - "metadata.py"
Cohesion: 0.09
Nodes (40): _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata(), _integrity_json() (+32 more)

### Community 14 - "create_app"
Cohesion: 0.15
Nodes (39): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, parametrize, test_boot_test_active_uses_conflict_error_contract(), test_boot_test_disconnected_uses_service_unavailable_contract() (+31 more)

### Community 15 - "log_replay.py"
Cohesion: 0.15
Nodes (35): SessionDetail, _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), Path, Bounded replay of persisted native UART evidence., Select one native session and replay its newest bounded UART lines. (+27 more)

### Community 16 - "test_validation.py"
Cohesion: 0.12
Nodes (27): prepare_uart_send_payload(), Return a valid Phase 1 wait-pattern timeout in seconds., Validate and preserve one case-sensitive literal wait pattern., Encode one public text command and enforce its final UART payload bound., Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., Raised when a public UART-send request has an invalid final payload., session_evidence_budget_bytes() (+19 more)

### Community 17 - "SerialCommandTransport"
Cohesion: 0.10
Nodes (28): Return an opened Enhanced command transport., open_serial_command_transport(), _pyserial_factory(), Synchronous serial transport for Debug Helper command exchange., Close the underlying serial port., Open a pyserial-backed command transport., Send NDJSON commands and read command responses from a serial port., SerialCommandTransport (+20 more)

### Community 18 - "uart_send.py"
Cohesion: 0.08
Nodes (22): Send one validated text command to the DUT UART., Close the live source represented by this session-local view., Validate and transmit one public UTF-8 UART command., EvidenceQuotaExceeded, Raised after an evidence unit is rejected and its session is terminalized., ActiveUartSendSession, _format_utc(), BackendMode (+14 more)

### Community 19 - "parse_device_message"
Cohesion: 0.09
Nodes (43): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, test_parse_buffer_overflow_message(), test_parse_buffer_status_message(), test_parse_command_error_message(), test_parse_command_success_message(), test_parse_command_success_without_timestamp() (+35 more)

### Community 20 - "UartCaptureProcessor"
Cohesion: 0.13
Nodes (18): Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission., Return bytes awaiting a line terminator for one segment and channel., UartCaptureProcessor, test_flush_channel_returns_none_for_empty_channel(), test_flush_channel_returns_none_when_channel_has_no_pending_line(), test_flush_channel_returns_partial_line_and_matches() (+10 more)

### Community 21 - "retrieval.py"
Cohesion: 0.09
Nodes (44): EvidenceTypeCount, FirstErrorReference, NativeSessionListItem, Raised when durable session evidence cannot be read or written., Compact first-error location used by bounded session list items., Bounded native lifecycle projection for one session list item., Logical size and optional record count for one session artifact., Bounded count for one detected-pattern or hardware-event type. (+36 more)

### Community 22 - "dutchmate_cli/config.py"
Cohesion: 0.11
Nodes (35): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+27 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.11
Nodes (35): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+27 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "models.py"
Cohesion: 0.08
Nodes (38): Return bounded recent UART replay for one selected session., Compare one terminal session with the designated baseline., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary(), _line_excerpt() (+30 more)

### Community 26 - "SessionStore"
Cohesion: 0.09
Nodes (32): Sessions abandoned at startup plus non-fatal compatibility diagnostics., SessionRecoveryResult, SessionDetail, Create filesystem-backed debug sessions., Most recent startup-recovery result for this store instance., Abandon stale native active sessions without mutating other schemas., Perform startup recovery while the store-wide lock is held., Transition one stale active native session during startup recovery. (+24 more)

### Community 27 - "DeviceActionResult"
Cohesion: 0.08
Nodes (16): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Apply startup hardware control mappings., Runtime surface needed by the current service API., Configure a control channel GPIO mode., Pulse the configured DUT reset role. (+8 more)

### Community 28 - "SegmentContext"
Cohesion: 0.05
Nodes (39): Return timestamp provenance once the source origin is established., Session-local connection segment and its timestamp provenance., SegmentContext, BackendEvent, BackendMode, datetime, Map one live connection source onto a new session-local segment zero., Advance a wait cursor on the wrapped source when supported. (+31 more)

### Community 29 - "session_store/baseline.py"
Cohesion: 0.10
Nodes (27): Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., BaselineOperation, Designate a stored session without requiring a backend connection., Clear a named designation without requiring a backend connection., clear_baseline(), _ineligibility_reason(), mark_baseline() (+19 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.08
Nodes (28): EnhancedCaptureEventSource, EnhancedNdjsonEventStream, Interim synchronous adapter for the existing Enhanced serial transport., Return device-timer provenance for this compatibility source., Establish timestamp provenance while retaining the first evidence event., Close the owned message source when it exposes a close operation., Parse Enhanced NDJSON chunks and expose only normalized evidence events., Return an incomplete Enhanced NDJSON frame buffered by the parser. (+20 more)

### Community 32 - "UartCaptureResult"
Cohesion: 0.20
Nodes (7): Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Flush one segment/channel's trailing partial line, if any., Finalize trailing derived state for every segment/channel., UartCaptureResult, Persist one UART evidence unit., Persist derived UART records finalized at capture close.

### Community 33 - "ReconnectedCaptureSource"
Cohesion: 0.08
Nodes (18): build_basic_capture_reconnect(), OpenCaptureReplacement, Build the bounded reopen adapter for one selected Basic backend., Open one segment-bound replacement source., Return a fully prepared replacement or raise for a failed attempt., Retry backend opening within the workflow-supplied monotonic deadline., RetryingCaptureReconnect, ClosableSource (+10 more)

### Community 34 - "evidence.py"
Cohesion: 0.13
Nodes (22): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), line_limit_exceeded_event_json() (+14 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "BackendSnapshot"
Cohesion: 0.10
Nodes (24): _backend_snapshot(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), test_status_returns_connected_gpio_mapping_state(), BackendCapability, Return capabilities remaining after host policy is applied., Return the configured software capability policy., apply_capability_policy(), BackendCapabilityPolicy (+16 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.07
Nodes (63): CommandSuccessMessage, Successful command response from the Debug Helper., GpioConfigurator, Configure GPIO modes through firmware and update accepted host state., GpioModeRegistry, GpioModeRejection, GpioModeRequestSource, Record a firmware- or host-rejected GPIO control channel mode request. (+55 more)

### Community 38 - "DeviceActionError"
Cohesion: 0.10
Nodes (19): Register service exception handlers on an app., register_error_handlers(), test_exception_handlers_preserve_firmware_error_code(), Core DUTchMate library., DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName (+11 more)

### Community 39 - "UartLineBuffer"
Cohesion: 0.18
Nodes (16): Buffer raw UART bytes until complete newline-terminated lines are available., Raw UART bytes not yet terminated by a newline., UartLineBuffer, test_byte_after_limit_discards_only_derived_copy_and_counts_until_lf(), test_exact_limit_line_is_emitted_normally(), test_feed_complete_line(), test_feed_multiple_lines(), test_feed_requires_bytes() (+8 more)

### Community 40 - "runtime.py"
Cohesion: 0.05
Nodes (45): Service entrypoint for DUTchMate., load_startup_hardware_config(), Device Core Service startup configuration helpers., Load startup hardware configuration, treating a missing file as empty config., test_exception_handlers_return_json_error_response(), GpioModeRequestSource, GPIO mode configuration workflow., Send `configure_gpio_mode` and record the firmware result. (+37 more)

### Community 41 - "parser.py"
Cohesion: 0.14
Nodes (31): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol input boundaries., Base class for host-device protocol errors. (+23 more)

### Community 42 - "UartReceiveEvent"
Cohesion: 0.17
Nodes (43): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, evidence_bytes(), fixed_clock(), fixed_id(), datetime, MonkeyPatch, Path (+35 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.11
Nodes (26): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+18 more)

### Community 44 - "enhanced.py"
Cohesion: 0.06
Nodes (43): build_enhanced_capture_reconnect(), OpenBasicConnection, OpenEnhancedTransport, Protocol, Service-owned backend reopen and replaceable-control composition., Build bounded Enhanced reopen, hello, provenance, and control replacement., Open one raw Basic connection from resolved settings., Return an opened Basic connection. (+35 more)

### Community 45 - "ValueError"
Cohesion: 0.33
Nodes (9): ValueError, Return a supported GPIO electrical mode., Return a supported GPIO logic level., Validate the complete Phase 1 GPIO electrical-mode matrix., validate_gpio_level(), validate_gpio_mode(), validate_gpio_mode_configuration(), GpioControlMode (+1 more)

### Community 46 - "BasicBackendEventSource"
Cohesion: 0.10
Nodes (16): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the complete Basic identity/policy/provenance snapshot., Return the next FIFO event, or ``None`` for an ordinary timeout. (+8 more)

### Community 47 - "processor.py"
Cohesion: 0.14
Nodes (10): OversizedUartLine, Line buffering for decoded DUT UART bytes., Return the trailing partial line, if any, and clear the buffer., Finalize trailing normal or oversized state at segment/session close., Bounded descriptor for one physical line that exceeded the derived limit., Normal lines and bounded oversized-line facts produced by one input., Consume UART bytes and return complete lines. Returned line `raw` values…, Consume bytes and return normal lines plus bounded overflow facts. (+2 more)

### Community 48 - "test_capture_reconnect.py"
Cohesion: 0.24
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 49 - "FrameTooLargeError"
Cohesion: 0.13
Nodes (10): Advance a workflow ingestion cursor past already-normalized events., FrameTooLargeError, Raised before decoding when a device-to-host frame exceeds its bound., DeviceMessage, Send one encoded command and return the matching command response., Return the oldest queued or newly read Debug Helper message., Return and clear messages queued during command requests., DeviceMessage (+2 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (24): additionalProperties, minLength, type, enum, type, $id, const, properties (+16 more)

### Community 51 - "helpers.py"
Cohesion: 0.20
Nodes (15): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _append_line(), BaselineRuntime, _capture() (+7 more)

### Community 52 - "parse_hardware_gpio_config"
Cohesion: 0.09
Nodes (43): GpioConfigError, HardwareControlMapping, HardwareGpioConfig, load_hardware_gpio_config(), _optional_string(), _optional_voltage(), _parse_control_mapping(), parse_hardware_gpio_config() (+35 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 55 - "SessionListPage"
Cohesion: 0.17
Nodes (12): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+4 more)

### Community 56 - "DeviceCoreSessionStorage"
Cohesion: 0.07
Nodes (19): test_capture_summary_serializes_bounded_first_error_evidence(), DeviceCoreSessionStorage, Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record. (+11 more)

### Community 57 - "SessionHandle"
Cohesion: 0.07
Nodes (24): Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session. (+16 more)

### Community 58 - "SessionSummary"
Cohesion: 0.14
Nodes (9): Capture UART and telemetry messages into a session., Reset the DUT and capture boot evidence into a session., Compact summary of a debug session for workflow/API responses., SessionSummary, Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists. (+1 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "store.py"
Cohesion: 0.11
Nodes (19): RuntimeError, Outcome of the most recent configured session-retention pass., Raised when stale native session metadata cannot be safely replaced., One non-fatal startup-recovery observation for a stored session., SessionRecoveryDiagnostic, SessionRecoveryError, SessionRetentionStatus, apply_session_retention() (+11 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.07
Nodes (36): build_startup_runtime(), NoReturn, Path, Read and validate the initial Debug Helper hello message., Build the service runtime for one explicitly selected backend., read_startup_hello(), _UnavailableDeviceControl, AdvancingClock (+28 more)

### Community 63 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "DeviceControl"
Cohesion: 0.13
Nodes (8): Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., ReplaceableDeviceControl, DeviceControl, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse the DUT reset line and return device time., Set DUT boot mode and return device time.

### Community 67 - "CommandTransport"
Cohesion: 0.25
Nodes (5): CommandTransport, DeviceMessage, Protocol, Transport capable of sending one host command and returning its response., Send one encoded command and return one parsed device response.

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "main"
Cohesion: 0.13
Nodes (12): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), load_backend_config(), Any, Path (+4 more)

### Community 70 - "uart_send_command"
Cohesion: 0.17
Nodes (15): Send raw bytes to the DUT UART RX line., Build a validated `uart_send` command from raw bytes., Build a `uart_send` command from UTF-8 text., uart_send_command(), uart_send_text_command(), UartSendCommand, test_build_uart_send_command_from_bytes(), test_build_uart_send_text_command_appends_newline() (+7 more)

### Community 71 - "resolve_backend_settings"
Cohesion: 0.27
Nodes (13): BackendConfig, Apply explicit overrides and backend-specific defaults., Optional project backend selection loaded from TOML., resolve_backend_settings(), parametrize, test_backend_mode_is_required_without_cli_or_config_value(), test_basic_backend_requires_explicit_or_configured_port(), test_enhanced_backend_rejects_non_protocol_baudrate() (+5 more)

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
Cohesion: 0.18
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

### Community 80 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 81 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 82 - "reset_command"
Cohesion: 0.20
Nodes (10): Build a validated `reset` command., Pulse the configured DUT reset line., reset_command(), ResetCommand, test_build_reset_command(), test_encode_reset_command_as_ndjson(), test_rejects_boolean_reset_pulse(), test_rejects_reset_pulse_above_limit() (+2 more)

### Community 83 - "SerialPort"
Cohesion: 0.17
Nodes (7): Protocol, Small pyserial-compatible surface used by the command transport., Write bytes to the serial port., Flush pending output bytes., Read bytes until a delimiter or timeout., Close the serial port., SerialPort

### Community 84 - "GpioIdentifierValidationError"
Cohesion: 0.25
Nodes (8): GpioIdentifierValidationError, Validate and return an exact 1..64-byte GPIO role or signal identifier., Raised when a GPIO role or DUT signal violates the exact identifier contract., validate_gpio_identifier(), IdentifierValidationReason, test_gpio_identifier_counts_utf8_bytes_instead_of_characters(), test_gpio_identifier_rejects_unicode_control_characters(), test_gpio_identifier_rejects_unicode_edge_whitespace()

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "UartSender"
Cohesion: 0.24
Nodes (6): Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter., ReplaceableUartSender, Backend-neutral port for complete UART payload transmission., Submit every payload byte or raise a backend write error., UartSender

### Community 87 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

### Community 88 - "boot_mode_command"
Cohesion: 0.25
Nodes (8): boot_mode_command(), BootModeCommand, Build a validated `set_boot_mode` command., Set the configured DUT BOOT/control pin behavior., test_boot_mode_command_matches_canonical_example(), test_build_boot_mode_command(), test_encode_boot_mode_command_as_ndjson(), test_rejects_unknown_boot_mode()

### Community 89 - "commands.py"
Cohesion: 0.25
Nodes (6): BootMode, ConfigureGpioModeCommand, Host-to-device protocol command encoding., Configure a DUT control role on a physical control channel., Return a supported DUT boot mode., validate_boot_mode()

### Community 90 - "GPIO Configuration Semantics"
Cohesion: 0.18
Nodes (11): Control Channel State Model, Commanded Boot Mode State, GPIO Configuration Semantics, Role and DUT Signal Identifier Contract, Runtime GPIO Override Semantics, Safe High-Impedance Behavior, Semantic Control Workflows, GPIO Validation Order (+3 more)

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

### Community 98 - "normalize_enhanced_message"
Cohesion: 0.14
Nodes (18): normalize_enhanced_message(), BackendEvent, Parse a chunk and normalize its UART and buffer-telemetry messages., Translate one parsed Enhanced message into the shared event model., BufferOverflowMessage, BufferStatusMessage, UART/event ring buffer overflow reported by the Debug Helper., Firmware-side UART ring buffer telemetry. (+10 more)

### Community 99 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 101 - "project_diagnostic_detail"
Cohesion: 0.40
Nodes (4): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _bounded_error()

### Community 102 - ".read_event"
Cohesion: 0.18
Nodes (9): _enhanced_segment_context(), EnhancedMessageSource, _message_timestamp_us(), DeviceMessage, Protocol, Read and normalize one wire message, returning ``None`` for inactivity., Read and normalize one event without consulting the retained queue., Synchronous source of parsed Enhanced wire-protocol messages. (+1 more)

### Community 103 - "default_cli_config"
Cohesion: 0.50
Nodes (3): default_cli_config(), MonkeyPatch, fixture

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "_replay_uart_prefix"
Cohesion: 0.17
Nodes (14): test_recent_logs_payload_removes_oldest_whole_records_to_fit_body_cap(), _BoundedNewest, _normal_record(), _oversized_record(), Retain the newest coordinate-ordered records with bounded memory., _record_key(), _replay_uart_prefix(), _ReplayResult (+6 more)

### Community 107 - "_validator"
Cohesion: 0.53
Nodes (5): Draft202012Validator, parametrize, test_gpio_schema_accepts_safe_electrical_combinations(), test_gpio_schema_rejects_unsafe_electrical_combinations(), _validator()

### Community 110 - "host_to_device.schema.json"
Cohesion: 0.40
Nodes (4): $id, oneOf, $schema, title

### Community 111 - ".__exit__"
Cohesion: 0.50
Nodes (3): BaseException, TracebackType, Release the mutation guard.

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreStatus"
Cohesion: 0.12
Nodes (12): Return the current Device Core status., apply_startup_hardware_config(), GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., Apply startup GPIO mappings if a Debug Helper is already connected. (+4 more)

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **91 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `persistence.py`, `CaptureRecorder`, `enhanced_snapshot`, `DeviceCoreRuntime`, `uart_send.py`, `retrieval.py`, `models.py`, `SegmentContext`, `session_store/baseline.py`, `UartCaptureResult`, `test_basic.py`, `BackendSnapshot`, `UartReceiveEvent`, `test_capture_reconnect.py`, `helpers.py`, `SessionListPage`, `DeviceCoreSessionStorage`, `SessionHandle`, `SessionSummary`, `store.py`, `test_startup_config.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `test_comparison.py`, `test_log_replay.py`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `DeviceCoreClient`, `UartLine`, `test_validation.py`, `uart_send.py`, `UartCaptureProcessor`, `models.py`, `DeviceActionResult`, `SegmentContext`, `session_store/baseline.py`, `ReconnectedCaptureSource`, `BackendSnapshot`, `GpioModeRegistry`, `DeviceActionError`, `runtime.py`, `enhanced.py`, `SessionListPage`, `DeviceCoreSessionStorage`, `SessionHandle`, `SessionSummary`, `store.py`, `test_startup_config.py`, `DeviceControl`, `WaitPatternResult`, `UartSender`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `CaptureRecorder`, `enhanced_snapshot`, `DeviceCoreRuntime`, `metadata.py`, `uart_send.py`, `models.py`, `SessionStore`, `test_contracts.py`, `test_enhanced.py`, `ReconnectedCaptureSource`, `BackendSnapshot`, `runtime.py`, `UartReceiveEvent`, `enhanced.py`, `BasicBackendEventSource`, `test_capture_reconnect.py`, `helpers.py`, `SessionHandle`, `SessionSummary`, `store.py`, `test_reconnect_evidence.py`, `test_comparison.py`, `.read_event`, `DeviceCoreStatus`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 158 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `_append_line()`) actually correct?**
  _`SessionStore` has 158 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_create_app_applies_startup_hardware_config_when_runtime_is_connected()` and `test_rejected_startup_hardware_config_is_visible_in_status()`) actually correct?**
  _`DeviceCoreRuntime` has 73 INFERRED edges - model-reasoned connections that need verification._