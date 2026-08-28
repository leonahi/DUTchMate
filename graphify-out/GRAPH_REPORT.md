# Graph Report - DUTchMate  (2026-08-28)

## Corpus Check
- 215 files · ~159,906 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3506 nodes · 9481 edges · 151 communities (136 shown, 15 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 1758 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `46a49dfb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ReconnectedCaptureSource
- format_status
- test_host_command_encoder.py
- client.py
- dutchmate_cli/main.py
- enhanced.py
- workflows/capture.py
- main
- settings.py
- enhanced_snapshot
- EnhancedDeviceControl
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- persistence.py
- test_validation.py
- SerialCommandTransport
- runtime.py
- parse_device_message
- UartReceiveEvent
- log_replay.py
- startup.py
- service_error_from_exception
- SerialPortCandidate
- comparison.py
- SessionStore
- DeviceActionResult
- SessionPaths
- SessionListPage
- backends/__init__.py
- test_enhanced.py
- test_enhanced_serial_io.py
- DeviceCoreClient
- evidence.py
- test_basic.py
- BackendSnapshot
- GpioModeRegistry
- DeviceCoreRuntime
- validation.py
- GpioControlChannelState
- parser.py
- store.py
- dutchmate_cli/__init__.py
- test_enhanced_serial.py
- CommandTransport
- EnhancedMessageSource
- parse_hardware_gpio_config
- ServiceApiError
- BasicBackendEventSource
- errors.schema.json
- helpers.py
- fixed_id
- logs.py
- gpio_config/config.py
- DeviceCoreSessionStorage
- test_device_core_uart_send.py
- SessionHandle
- CaptureRecorder
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- enhanced_serial_io.py
- Phase 1 Implementation Spec
- enum
- DeviceControl
- Enhanced Asynchronous Serial Adapter Design
- create_server
- CommandSuccessMessage
- _StreamWriter
- InputValidationError
- test_baseline.py
- test_recovery.py
- test_retention.py
- WaitPatternResult
- BasicSerialPort
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- test_send.py
- FakeTransport
- fixture_protocol.c
- SerialPort
- SegmentContext
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- format_wait_pattern
- format_baseline_mutation
- Q: How should Enhanced serial command short writes complete or report partial acceptance?
- GPIO Configuration Semantics
- Enhanced Asynchronous Serial I/O Design
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- test_device_message_examples.py
- validate_reset_pulse
- test_gpio.py
- AsyncSerialReader
- SessionComparison
- FakeSerial
- Software Architecture
- _OwnedStreamReader
- SessionMutationLock
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- test_device_core_wait.py
- dutchmate-core
- Q: Where is the shared Enhanced host-command encoding and dispatch boundary?
- Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy
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
- build_enhanced_capture_reconnect
- ScriptedBasicSerial
- Q: commit and tell me what is next development step in phase-1
- Q: Before that what does Zephyr DUT exactly do and what is its use?
- Q: What does DMF stands for
- Q: I am ready to flash the pico.
- Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host.
- Q: commit and go to next step
- runtime_test_support.py
- Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries
- Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests.
- File Map
- File Responsibility Map
- Q: move to next step
- test_create_app_applies_startup_hardware_config_when_runtime_is_connected
- test_log_replay.py
- ._request_success
- .get_session
- Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?
- Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?
- modes.py
- validate_gpio_role
- FakeStreamTransport
- test_threaded_writer_uses_shared_exact_loop_off_event_loop
- test_threaded_writer_preserves_partial_acceptance_error

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 229 edges
2. `DeviceCoreRuntime` - 113 edges
3. `UartReceiveEvent` - 97 edges
4. `create_app()` - 84 edges
5. `EnhancedDeviceControl` - 76 edges
6. `SessionHandle` - 73 edges
7. `FakeRuntime` - 71 edges
8. `parse_device_message()` - 71 edges
9. `GpioModeRegistry` - 65 edges
10. `SegmentContext` - 64 edges

## Surprising Connections (you probably didn't know these)
- `Ring Buffer Validation Gate` --semantically_similar_to--> `Ring Buffer Acceptance Checklist`  [INFERRED] [semantically similar]
  docs/ring_buffer_sizing_plan.md → hardware/validation/phase1_ring_buffer.md
- `Safe High-Impedance Behavior` --semantically_similar_to--> `Hardware Safe Startup State`  [INFERRED] [semantically similar]
  docs/gpio_configuration_semantics.md → hardware/schematics/revision_a.md
- `_summary_from_metadata()` --calls--> `_first_error()`  [INFERRED]
  core/src/dutchmate_core/session_store/metadata.py → apps/cli/src/dutchmate_cli/capture.py
- `CliConfig` --uses--> `BackendConfig`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py
- `start_service()` --uses--> `BackendSettings`  [INFERRED]
  apps/cli/src/dutchmate_cli/lifecycle.py → core/src/dutchmate_core/backends/settings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DUTchMate Backend Pipeline** — readme_basic_backend, readme_enhanced_backend, readme_shared_host_processing_and_session_pipeline [EXTRACTED 1.00]
- **Graphify Operational Pipeline** — _codex_skills_graphify_skill_extraction_pipeline, _codex_skills_graphify_references_update_incremental_re_extraction, _codex_skills_graphify_skill_graph_health_check [EXTRACTED 1.00]
- **Bounded Evidence Integrity Contract** — docs_debug_agent_context_contract_bounded_hardware_evidence, docs_reconnect_session_semantics_incremental_evidence_writes, docs_software_architecture_session_store, docs_ring_buffer_sizing_plan_buffer_integrity_reporting, docs_mcp_integration_plan_bounded_tool_results [INFERRED 0.85]
- **Backend-Independent Evidence Pipeline** — docs_project_context_normalized_evidence_boundary, docs_phase1_implementation_spec_backend_independent_pipeline, docs_software_architecture_normalized_event_boundary, docs_software_architecture_backends_contracts [INFERRED 0.95]
- **Phase 1 Hardware Acceptance Gate** — docs_development_status_hardware_acceptance, docs_phase1_implementation_spec_phase1_done_criteria, docs_ring_buffer_sizing_plan_validation_gate, hardware_schematics_revision_a_prototype_validation, hardware_validation_phase1_ring_buffer_acceptance_checklist [INFERRED 0.95]

## Communities (151 total, 15 thin omitted)

### Community 0 - "ReconnectedCaptureSource"
Cohesion: 0.07
Nodes (35): OpenCaptureReplacement, Open one segment-bound replacement source., Return a fully prepared replacement or raise for a failed attempt., Retry backend opening within the workflow-supplied monotonic deadline., RetryingCaptureReconnect, ClosableSource, FakeClock, FakeControl (+27 more)

### Community 1 - "format_status"
Cohesion: 0.20
Nodes (21): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+13 more)

### Community 2 - "test_host_command_encoder.py"
Cohesion: 0.05
Nodes (53): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command., Build a validated `pulse_control` command. (+45 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (61): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+53 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (54): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, CliConfig, Merged CLI configuration., boot_test() (+46 more)

### Community 5 - "enhanced.py"
Cohesion: 0.05
Nodes (60): Service-owned backend reopen and replaceable-control composition., Read and validate one Debug Helper hello message., read_enhanced_hello(), _require_matching_enhanced_identity(), BackendInputKind, _ReaderFailure, BackendDisconnectedError, BackendInputError (+52 more)

### Community 6 - "workflows/capture.py"
Cohesion: 0.06
Nodes (55): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+47 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (45): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+37 more)

### Community 8 - "settings.py"
Cohesion: 0.05
Nodes (80): CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table(), parse_cli_config() (+72 more)

### Community 9 - "enhanced_snapshot"
Cohesion: 0.20
Nodes (25): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., enhanced_snapshot(), evidence_bytes(), Path, read_jsonl() (+17 more)

### Community 10 - "EnhancedDeviceControl"
Cohesion: 0.18
Nodes (33): EnhancedDeviceControl, Translate semantic control operations to Enhanced protocol commands., enhanced_info(), FakeCaptureSource, FakeMonotonicClock, BackendCapability, BackendEvent, Exception (+25 more)

### Community 11 - "app.py"
Cohesion: 0.06
Nodes (51): FastAPI, FastAPI application factory for the Device Core Service., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload(), CaptureRequest, _compact_json_size() (+43 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.10
Nodes (28): UART bytes captured by the Debug Helper., UartMessage, _frame_body(), NdjsonStreamParser, DeviceMessage, NDJSON stream parsing for serial byte chunks., Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline. (+20 more)

### Community 13 - "metadata.py"
Cohesion: 0.08
Nodes (44): _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata(), _integrity_json() (+36 more)

### Community 14 - "create_app"
Cohesion: 0.12
Nodes (40): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+32 more)

### Community 15 - "persistence.py"
Cohesion: 0.11
Nodes (42): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+34 more)

### Community 16 - "test_validation.py"
Cohesion: 0.11
Nodes (30): GpioIdentifierValidationError, prepare_uart_send_payload(), Encode one public text command and enforce its final UART payload bound., Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., Validate and return an exact 1..64-byte GPIO role or signal identifier., Raised when a public UART-send request has an invalid final payload., Raised when a GPIO role or DUT signal violates the exact identifier contract. (+22 more)

### Community 17 - "SerialCommandTransport"
Cohesion: 0.06
Nodes (58): Return an opened Enhanced command transport., CommandErrorMessage, Rejected or failed command response from the Debug Helper., _classify_serial_write_error(), open_serial_command_transport(), DeviceMessage, Exception, TransportWriteErrorCode (+50 more)

### Community 18 - "runtime.py"
Cohesion: 0.11
Nodes (21): Write a complete UART payload, retrying ordered short writes., BackendUartSendResult, BackendWriteError, Raised when a backend cannot accept a complete UART payload., Complete backend acceptance of one UART payload., Backend-neutral port for complete UART payload transmission., Submit every payload byte or raise a backend write error., UartSender (+13 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (62): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+54 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.10
Nodes (47): _append_line(), Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission. (+39 more)

### Community 21 - "log_replay.py"
Cohesion: 0.11
Nodes (32): _BoundedNewest, _decode_uart_event(), _existing_paths(), _non_negative_int(), _normal_record(), _oversized_record(), Path, Bounded replay of persisted native UART evidence. (+24 more)

### Community 22 - "startup.py"
Cohesion: 0.12
Nodes (15): apply_startup_hardware_config(), load_startup_hardware_config(), GpioRoleName, Path, Protocol, Device Core Service startup configuration helpers., Runtime surface needed to apply startup hardware configuration., Return current runtime status. (+7 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (39): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+31 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "comparison.py"
Cohesion: 0.11
Nodes (34): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary() (+26 more)

### Community 26 - "SessionStore"
Cohesion: 0.11
Nodes (29): SessionDetail, Create filesystem-backed debug sessions., Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists., Return bounded schema-aware detail for one stored session., Apply the configured count limit and return its current status. (+21 more)

### Community 27 - "DeviceActionResult"
Cohesion: 0.06
Nodes (18): Protocol, SessionDetail, Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Apply startup hardware control mappings., Runtime surface needed by the current service API. (+10 more)

### Community 28 - "SessionPaths"
Cohesion: 0.13
Nodes (36): Filesystem paths for the required Phase 1 session files., SessionPaths, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file() (+28 more)

### Community 29 - "SessionListPage"
Cohesion: 0.11
Nodes (16): Return one bounded newest-first session page., _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail() (+8 more)

### Community 30 - "backends/__init__.py"
Cohesion: 0.07
Nodes (34): Basic generic USB-to-UART connection, receive, and send adapter., BackendCapabilityError, BackendEventSource, BackendInfo, integrity_for_backend(), BackendEvent, Backend-neutral identity, timing, event, and receive-source contracts., Return the initial UART-loss observation state for a backend mode. (+26 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.07
Nodes (35): EnhancedCaptureEventSource, EnhancedNdjsonEventStream, EnhancedUartSender, Translate complete UART payloads to Enhanced protocol commands., Interim synchronous adapter for the existing Enhanced serial transport., Advance a workflow ingestion cursor past already-normalized events., Close the owned message source when it exposes a close operation., Parse Enhanced NDJSON chunks and expose only normalized evidence events. (+27 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "DeviceCoreClient"
Cohesion: 0.06
Nodes (35): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+27 more)

### Community 34 - "evidence.py"
Cohesion: 0.10
Nodes (28): test_capture_summary_serializes_bounded_first_error_evidence(), buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error() (+20 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "BackendSnapshot"
Cohesion: 0.08
Nodes (31): _backend_snapshot(), _snapshot(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), test_status_returns_connected_gpio_mapping_state(), BasicBackendConnection, BackendCapability, Return capabilities remaining after host policy is applied., Close the underlying serial port. (+23 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.16
Nodes (28): GpioModeRegistry, GpioModeRejection, Rejected GPIO channel mode request., Track accepted and rejected GPIO mode configuration per control channel., GPIO role configuration state used by this runtime., fixed_clock(), datetime, parametrize (+20 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.07
Nodes (24): Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError, SessionWorkflow (+16 more)

### Community 39 - "validation.py"
Cohesion: 0.12
Nodes (24): _is_unicode_whitespace(), GpioControlChannel, ValueError, Shared validation for public Device Core input contracts., Validate and preserve an exact serial-port identifier., Validate and preserve an exact DUT schematic signal identifier., Return a known physical GPIO control channel., Return a supported GPIO electrical mode. (+16 more)

### Community 40 - "GpioControlChannelState"
Cohesion: 0.11
Nodes (16): _format_utc_timestamp(), GpioControlChannelState, datetime, GpioControlChannel, GpioModeRequestSource, GpioRoleName, Return current states for all physical control channels., Record a firmware-accepted GPIO control channel mode. (+8 more)

### Community 41 - "parser.py"
Cohesion: 0.13
Nodes (32): Host-to-device protocol command encoding., FrameTooLargeError, HostCommandFrameTooLargeError, InvalidUtf8Error, MalformedMessageError, ProtocolValidationError, ProtocolVersionError, Typed failures at Enhanced wire-protocol boundaries. (+24 more)

### Community 42 - "store.py"
Cohesion: 0.06
Nodes (48): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+40 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.09
Nodes (29): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+21 more)

### Community 44 - "test_enhanced_serial.py"
Cohesion: 0.03
Nodes (107): Event, BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, _compact_json_frame_of_size(), FakeAsyncFrameWriter, FakeAsyncSerialReader, make_adapter() (+99 more)

### Community 45 - "CommandTransport"
Cohesion: 0.18
Nodes (8): AsyncCommandTransport, CommandTransport, DeviceMessage, Protocol, Transport capable of sending one host command and returning its response., Send one encoded command and return one parsed device response., Asynchronous one-at-a-time host command exchange., Send one complete command and return its parsed response.

### Community 46 - "EnhancedMessageSource"
Cohesion: 0.33
Nodes (4): EnhancedMessageSource, Protocol, Synchronous source of parsed Enhanced wire-protocol messages., Read the next parsed message or raise on transport timeout.

### Community 47 - "parse_hardware_gpio_config"
Cohesion: 0.16
Nodes (23): HardwareControlMapping, parse_hardware_gpio_config(), Configured mapping from a DUTchMate control channel to a DUT role., Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level() (+15 more)

### Community 48 - "ServiceApiError"
Cohesion: 0.18
Nodes (15): Raised when the local Device Core Service returns an error response., ServiceApiError, _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response. (+7 more)

### Community 49 - "BasicBackendEventSource"
Cohesion: 0.11
Nodes (12): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return the complete Basic identity/policy/provenance snapshot., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner. (+4 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "helpers.py"
Cohesion: 0.11
Nodes (21): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), BaselineRuntime, _capture(), Path (+13 more)

### Community 52 - "fixed_id"
Cohesion: 0.25
Nodes (20): fixed_id(), MonkeyPatch, Path, test_complete_native_session_is_terminal_and_one_way(), test_create_native_session_does_not_publish_metadata_when_reserve_write_fails(), test_create_native_session_writes_active_schema_v1_and_terminal_reserve(), test_create_session_defaults_optional_metadata_to_none_and_false(), test_create_session_fails_if_generated_session_id_already_exists() (+12 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "gpio_config/config.py"
Cohesion: 0.17
Nodes (18): GpioConfigError, load_hardware_gpio_config(), _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, Path (+10 more)

### Community 55 - "DeviceCoreSessionStorage"
Cohesion: 0.14
Nodes (10): DeviceCoreSessionStorage, Protocol, Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record., Capture and bounded-query storage operations required by the runtime., Protocol, Perturbation evidence operations required by UART send., Append an admitted pre-dispatch attempt. (+2 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.17
Nodes (27): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events() (+19 more)

### Community 57 - "SessionHandle"
Cohesion: 0.05
Nodes (36): Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session. (+28 more)

### Community 58 - "CaptureRecorder"
Cohesion: 0.05
Nodes (61): CaptureRecorder, CaptureRecordResult, CaptureWorkflow, _normalized_control_timestamp(), BackendEvent, CommandedBootMode, Exception, SessionWorkflow (+53 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.08
Nodes (62): _latest_terminal_native(), _validate_session_command(), EvidenceTypeCount, FirstErrorReference, LegacySessionListItem, NativeSessionListItem, Compact summary of a debug session for workflow/API responses., Compact first-error location used by bounded session list items. (+54 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.20
Nodes (22): DUTchMate Device Core Service package., build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), MonkeyPatch, Path, ScriptedEnhancedSerial (+14 more)

### Community 63 - "enhanced_serial_io.py"
Cohesion: 0.18
Nodes (12): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener(), _ThreadedSerialFrameWriter (+4 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "DeviceControl"
Cohesion: 0.20
Nodes (7): DeviceControl, ControlState, Protocol, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time., Apply one configured channel's active or idle state and return device time.

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.21
Nodes (19): CommandSuccessMessage, Successful command response from the Debug Helper., DeviceActionRunner, Run reset/boot commands only when required GPIO roles are configured., FakeTransport, parametrize, test_action_result_rejects_mismatched_accepted_fields(), test_boot_mode_requires_configured_boot_role() (+11 more)

### Community 70 - "_StreamWriter"
Cohesion: 0.15
Nodes (9): Protocol, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Open one pyserial-asyncio stream pair., _StreamReader, _StreamTransport (+1 more)

### Community 71 - "InputValidationError"
Cohesion: 0.18
Nodes (18): GpioConfigurator, GpioModeRequestSource, GPIO mode configuration workflow., Configure GPIO modes through firmware and update accepted host state., Send `configure_gpio_mode` and record the firmware result., InputValidationError, Raised when an application input violates a Device Core contract., FakeTransport (+10 more)

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

### Community 80 - "test_send.py"
Cohesion: 0.20
Nodes (10): _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., MonkeyPatch, test_format_forced_send_reports_attempt_and_evidence_pair(), test_send_client_failure_reports_unknown_acceptance_warning(), test_send_client_forwards_text_flags_without_raw_encoding() (+2 more)

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
Cohesion: 0.07
Nodes (21): Return host-monotonic provenance established at source creation., Return timestamp provenance once the source origin is established., Session-local connection segment and its timestamp provenance., SegmentContext, Return device-timer provenance for this compatibility source., Establish timestamp provenance while retaining the first evidence event., Return timestamp provenance once later event support establishes it., BackendEvent (+13 more)

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

### Community 89 - "Q: How should Enhanced serial command short writes complete or report partial acceptance?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: How should Enhanced serial command short writes complete or report partial acceptance?, Source Nodes

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

### Community 99 - "validate_reset_pulse"
Cohesion: 0.15
Nodes (9): BootMode, Return a valid DUT reset pulse duration in milliseconds., Return a supported DUT boot mode., validate_boot_mode(), validate_reset_pulse(), _format_utc(), datetime, Pulse the DUT reset role after confirming reset GPIO configuration. (+1 more)

### Community 100 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "SessionComparison"
Cohesion: 0.17
Nodes (6): Compare one terminal session with the designated baseline., Compare one terminal session with the designated baseline., Compare stored evidence without requiring a backend connection., Bounded comparison against the explicit project baseline., SessionComparison, Compare one terminal capture or boot test with the current baseline.

### Community 103 - "FakeSerial"
Cohesion: 0.20
Nodes (5): Read and validate the initial Debug Helper hello message., read_startup_hello(), FakeSerial, test_read_startup_hello_rejects_non_hello_message(), test_read_startup_hello_returns_initial_hello()

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "_OwnedStreamReader"
Cohesion: 0.22
Nodes (4): _OwnedStreamReader, BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 106 - "SessionMutationLock"
Cohesion: 0.22
Nodes (6): BaseException, TracebackType, Shared guard that serializes active-session evidence mutations., Acquire the mutation guard., Release the mutation guard., SessionMutationLock

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

### Community 113 - "Q: Where is the shared Enhanced host-command encoding and dispatch boundary?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Where is the shared Enhanced host-command encoding and dispatch boundary?, Source Nodes

### Community 114 - "Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Remove host role and DUT signal metadata from firmware-facing configure_gpio_mode commands while preserving host policy, Source Nodes

### Community 115 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 126 - "build_enhanced_capture_reconnect"
Cohesion: 0.08
Nodes (17): build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), OpenBasicConnection, OpenEnhancedTransport, ControlState, Protocol, Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter. (+9 more)

### Community 128 - "Q: commit and tell me what is next development step in phase-1"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: commit and tell me what is next development step in phase-1, Source Nodes

### Community 129 - "Q: Before that what does Zephyr DUT exactly do and what is its use?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Before that what does Zephyr DUT exactly do and what is its use?, Source Nodes

### Community 130 - "Q: What does DMF stands for"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What does DMF stands for, Source Nodes

### Community 131 - "Q: I am ready to flash the pico."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: I am ready to flash the pico., Source Nodes

### Community 132 - "Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Drive disappears and the tx and rx are connected to the USB-to-UART adapter. The adapter is connected to host., Source Nodes

### Community 133 - "Q: commit and go to next step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: commit and go to next step, Source Nodes

### Community 135 - "Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Trace and enforce exact Enhanced device-to-host NDJSON frame boundaries, Source Nodes

### Community 136 - "Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests."
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Trace hello firmware and device identity validation through the protocol parser, schema, and tests., Source Nodes

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "Q: move to next step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: move to next step, Source Nodes

### Community 140 - "test_create_app_applies_startup_hardware_config_when_runtime_is_connected"
Cohesion: 0.38
Nodes (5): FakeTransport, _hello(), DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status()

### Community 141 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 143 - ".get_session"
Cohesion: 0.40
Nodes (3): SessionDetail, Return bounded schema-aware detail for one session., Return bounded session detail without expanding raw evidence arrays.

### Community 144 - "Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: How should Phase 1 introduce the continuous asynchronous Enhanced serial adapter without competing readers?, Source Nodes

### Community 145 - "Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What is the approved Phase 1 design boundary for the first Enhanced asynchronous serial adapter slice?, Source Nodes

### Community 146 - "modes.py"
Cohesion: 0.29
Nodes (5): GpioConfigurationError, RuntimeError, GPIO role configuration state tracking., Raised when a GPIO-controlled workflow cannot run with current state., Hardware action workflows guarded by GPIO configuration state.

### Community 147 - "validate_gpio_role"
Cohesion: 0.33
Nodes (5): Return the configured channel state for a role, if one exists., Return configured channel state for a role or raise a workflow-facing error., GpioRoleName, Validate and preserve an exact GPIO role identifier., validate_gpio_role()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **197 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+192 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `EnhancedDeviceControl` (5× useful, score=4.88358864) _(code changed — re-verify)_
- `FrameTooLargeError` (2× useful, score=1.990592558)
- `test_host_command_encoder.py` (2× useful, score=1.976344876)
- `HelloMessage` (2× useful, score=1.974557864)
- `test_device_message_parser.py` (2× useful, score=1.974557864)
- `DUTchMate Zephyr DUT Fixture` (2× useful, score=1.914544418)
- `Zephyr DUT Fixture Work` (2× useful, score=1.82978437) _(code changed — re-verify)_

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `ReconnectedCaptureSource`, `enhanced_snapshot`, `EnhancedDeviceControl`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `test_log_replay.py`, `persistence.py`, `UartReceiveEvent`, `comparison.py`, `SessionListPage`, `evidence.py`, `test_basic.py`, `BackendSnapshot`, `store.py`, `helpers.py`, `fixed_id`, `test_device_core_uart_send.py`, `SessionHandle`, `CaptureRecorder`, `retrieval.py`, `test_startup_config.py`, `test_baseline.py`, `test_recovery.py`, `test_retention.py`, `test_reconnect_evidence.py`, `FakeTransport`, `SegmentContext`, `test_comparison.py`, `SessionComparison`, `test_device_core_wait.py`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `ReconnectedCaptureSource`, `enhanced.py`, `workflows/capture.py`, `EnhancedDeviceControl`, `test_create_app_applies_startup_hardware_config_when_runtime_is_connected`, `.get_session`, `test_validation.py`, `runtime.py`, `modes.py`, `UartReceiveEvent`, `comparison.py`, `DeviceActionResult`, `SessionListPage`, `backends/__init__.py`, `BackendSnapshot`, `GpioModeRegistry`, `GpioControlChannelState`, `helpers.py`, `test_device_core_uart_send.py`, `SessionHandle`, `CaptureRecorder`, `retrieval.py`, `test_startup_config.py`, `DeviceControl`, `CommandSuccessMessage`, `InputValidationError`, `WaitPatternResult`, `FakeTransport`, `SegmentContext`, `SessionComparison`, `test_device_core_wait.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `ReconnectedCaptureSource`, `enhanced.py`, `workflows/capture.py`, `enhanced_snapshot`, `EnhancedDeviceControl`, `metadata.py`, `runtime.py`, `SessionStore`, `backends/__init__.py`, `test_enhanced.py`, `BackendSnapshot`, `DeviceCoreRuntime`, `store.py`, `BasicBackendEventSource`, `helpers.py`, `fixed_id`, `SessionHandle`, `CaptureRecorder`, `retrieval.py`, `test_reconnect_evidence.py`, `test_comparison.py`, `SessionMutationLock`, `test_device_core_wait.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 158 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `_append_line()`) actually correct?**
  _`SessionStore` has 158 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_create_app_applies_startup_hardware_config_when_runtime_is_connected()` and `test_rejected_startup_hardware_config_is_visible_in_status()`) actually correct?**
  _`DeviceCoreRuntime` has 73 INFERRED edges - model-reasoned connections that need verification._