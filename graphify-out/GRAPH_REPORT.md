# Graph Report - DUTchMate  (2026-09-01)

## Corpus Check
- 237 files · ~200,133 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4078 nodes · 11006 edges · 191 communities (172 shown, 19 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 1871 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4c7d594e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ReconnectedCaptureSource
- format_status
- dutchmate_cli/config.py
- client.py
- dutchmate_cli/main.py
- ContinuousIngestionCoordinator
- UartLine
- main
- settings.py
- UartReceiveEvent
- FakeMonotonicClock
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- validation.py
- test_validation.py
- transport.py
- SegmentContext
- parse_device_message
- UartCaptureProcessor
- log_replay.py
- CaptureEventSource
- service_error_from_exception
- SerialPortCandidate
- comparison.py
- SessionStore
- RuntimeProvider
- SessionPaths
- SessionListPage
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- enhanced.py
- evidence.py
- test_basic.py
- BasicSerialPort
- GpioModeRegistry
- DeviceCoreRuntime
- EnhancedAsyncHost
- UartIntegrity
- parser.py
- session_store/baseline.py
- dutchmate_cli/__init__.py
- FakeAsyncSerialReader
- make_adapter
- AsyncEnhancedSerialAdapter
- gpio_config/config.py
- Service-Owned Continuous Ingestion Design
- BasicBackendEventSource
- errors.schema.json
- helpers.py
- test_app_lifecycle.py
- logs.py
- Continuous Connection And Integrity Monitoring Design
- store.py
- test_device_core_uart_send.py
- SessionHandle
- test_capture_workflows.py
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- backend_reconnect.py
- Enhanced Asynchronous Serial Adapter Design
- create_server
- device_actions.py
- test_capture_reconnect.py
- runtime.py
- test_baseline.py
- BufferStatusEvent
- test_retention.py
- FakeAsyncFrameWriter
- CaptureRecorder
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- parse_hardware_gpio_config
- FakeDeviceControl
- fixture_protocol.c
- test_enhanced_serial.py
- CaptureWorkflow
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- format_wait_pattern
- format_baseline_mutation
- BackendDisconnectedError
- GPIO Configuration Semantics
- Enhanced Asynchronous Serial I/O Design
- Reconnect and Session Semantics
- test_dependencies.py
- test_comparison.py
- DUTchMate
- Debug Agent Context Contract
- MCP Integration Plan
- BlockingCloseSource
- UartLineBuffer
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- Coordinated Background Reconnect Design
- test_backend_reconnect.py
- Software Architecture
- test_dut.py
- BackendInputError
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- test_device_core_wait.py
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
- .start
- Enhanced Async Service Integration Design
- backend_snapshot
- line_buffer.py
- File Responsibility Map
- File Responsibility Map
- enhanced_serial_io.py
- send_uart_command
- FakeEnhancedAsyncHost
- DeviceCoreStatus
- File Map
- File Responsibility Map
- test_log_replay.py
- test_reader_failure_is_repeatable_disconnect
- _UnavailableDeviceControl
- test_gpio.py
- ScriptedBasicSerial
- _request_after_entering
- File Responsibility Map
- HardwareGpioConfig
- CaptureReconnect
- BlockingCloseStreamWriter
- test_transactions.py
- TransportTimeoutError
- TerminationBarrierAdapter
- .get_session
- test_device_message_examples.py
- BackendUartSendResult
- FakeStreamTransport
- _BoundedNewest
- File Responsibility Map
- test_host_command_encoder.py
- .__init__
- validate_session_max_size_mb
- .feed
- project_diagnostic_detail
- .__init__
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
- test_close_wakes_idle_disconnect_waiter
- .begin_workflow
- .capture_source_health
- .discard_pending_events
- .end_workflow
- test_start_rejects_non_hello_first_message
- test_discard_pending_events_advances_only_the_adapter_fifo

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 252 edges
2. `DeviceCoreRuntime` - 137 edges
3. `UartReceiveEvent` - 103 edges
4. `SegmentContext` - 94 edges
5. `create_app()` - 90 edges
6. `ContinuousIngestionCoordinator` - 81 edges
7. `FakeRuntime` - 73 edges
8. `SessionHandle` - 73 edges
9. `parse_device_message()` - 69 edges
10. `BackendSnapshot` - 67 edges

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

## Communities (191 total, 19 thin omitted)

### Community 0 - "ReconnectedCaptureSource"
Cohesion: 0.07
Nodes (31): BackendReconnectCoordinator, _close_unpublished_candidate(), OpenCaptureReplacement, BaseException, Event, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt. (+23 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "dutchmate_cli/config.py"
Cohesion: 0.10
Nodes (38): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+30 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (61): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+53 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.13
Nodes (50): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+42 more)

### Community 5 - "ContinuousIngestionCoordinator"
Cohesion: 0.12
Nodes (51): ContinuousIngestionCoordinator, Continuously drain one source and expose an active-workflow FIFO., buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, MonkeyPatch, parametrize (+43 more)

### Community 6 - "UartLine"
Cohesion: 0.12
Nodes (25): PatternDetector, Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines., _validate_patterns(), One complete UART log line., UartLine (+17 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (43): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+35 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (46): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError, _baudrate() (+38 more)

### Community 9 - "UartReceiveEvent"
Cohesion: 0.16
Nodes (47): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, enhanced_snapshot(), evidence_bytes(), fixed_clock(), fixed_id(), datetime, Path (+39 more)

### Community 10 - "FakeMonotonicClock"
Cohesion: 0.14
Nodes (30): AdvancingMonotonicClock, FakeCaptureSource, FakeMonotonicClock, BackendEvent, Exception, _fixed_session_time(), datetime, MonkeyPatch (+22 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (53): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload() (+45 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.12
Nodes (26): HelloMessage, Typed protocol messages received from the Debug Helper., Debug Helper hello handshake., UART bytes captured by the Debug Helper., UartMessage, NdjsonStreamParser, Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline. (+18 more)

### Community 13 - "metadata.py"
Cohesion: 0.09
Nodes (40): _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata(), _integrity_json() (+32 more)

### Community 14 - "create_app"
Cohesion: 0.10
Nodes (48): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+40 more)

### Community 15 - "validation.py"
Cohesion: 0.08
Nodes (37): BootMode, _format_utc_timestamp(), datetime, GPIO role configuration state tracking., _utc_now(), _is_unicode_whitespace(), GpioControlChannel, GpioModeRequestSource (+29 more)

### Community 16 - "test_validation.py"
Cohesion: 0.10
Nodes (30): Capture new UART evidence until one literal completes or time expires., GpioIdentifierValidationError, prepare_uart_send_payload(), Return a valid Phase 1 wait-pattern timeout in seconds., Validate and preserve one case-sensitive literal wait pattern., Encode one public text command and enforce its final UART payload bound., Validate and return an exact 1..64-byte GPIO role or signal identifier., Raised when a public UART-send request has an invalid final payload. (+22 more)

### Community 17 - "transport.py"
Cohesion: 0.11
Nodes (29): _classify_serial_write_error(), Exception, TransportWriteErrorCode, Exact serial-frame writes shared by Enhanced transport adapters., Write and flush one complete frame with exact accepted-byte errors., write_serial_frame(), RuntimeError, TransportWriteErrorCode (+21 more)

### Community 18 - "SegmentContext"
Cohesion: 0.07
Nodes (41): backend_snapshot(), _snapshot(), enhanced_replacement_snapshot(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit(), BasicBackendConnection, BackendCapability, Basic generic USB-to-UART connection, receive, and send adapter., Return capabilities remaining after host policy is applied. (+33 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (62): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+54 more)

### Community 20 - "UartCaptureProcessor"
Cohesion: 0.09
Nodes (28): PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Backend-independent UART receive processing to log lines and matches., Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event. (+20 more)

### Community 21 - "log_replay.py"
Cohesion: 0.13
Nodes (42): _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path, Bounded replay of persisted native UART evidence. (+34 more)

### Community 22 - "CaptureEventSource"
Cohesion: 0.13
Nodes (13): _close_source(), _project_event_health(), BackendEvent, Exception, Service-owned continuous draining for finite capture workflows., Return the next active-workflow event or an inactivity timeout., Detach and close the consumed disconnected source., Transfer one validated replacement into the stable coordinator. (+5 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (38): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+30 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "comparison.py"
Cohesion: 0.10
Nodes (33): Register service exception handlers on an app., register_error_handlers(), Return bounded recent UART replay for one selected native session., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary() (+25 more)

### Community 26 - "SessionStore"
Cohesion: 0.09
Nodes (31): SessionDetail, Create filesystem-backed debug sessions., Abandon stale native active sessions without mutating other schemas., Perform startup recovery while the store-wide lock is held., Transition one active native session to completed exactly once., Complete one wait session with an authoritative optional match index., Transition one active native session to failed with bounded detail., Transition one stale active native session during startup recovery. (+23 more)

### Community 27 - "RuntimeProvider"
Cohesion: 0.06
Nodes (19): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline. (+11 more)

### Community 28 - "SessionPaths"
Cohesion: 0.13
Nodes (36): Filesystem paths for the required Phase 1 session files., SessionPaths, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file() (+28 more)

### Community 29 - "SessionListPage"
Cohesion: 0.12
Nodes (17): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+9 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (22): BackendEventSource, BackendEvent, Protocol, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout., SourceFactory (+14 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.07
Nodes (38): DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., AsyncEnhancedDeviceControl, AsyncEnhancedUartSender, EnhancedNdjsonEventStream, ControlState, Translate complete UART payloads through an async Enhanced transport., Parse Enhanced NDJSON chunks and expose only normalized evidence events. (+30 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.15
Nodes (21): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if command writes use the event loop or skip partial-write recovery., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive. (+13 more)

### Community 33 - "enhanced.py"
Cohesion: 0.10
Nodes (31): backend_input_error_from_protocol(), _control_success_timestamp(), enhanced_message_timestamp_us(), enhanced_segment_context(), normalize_enhanced_hello(), normalize_enhanced_message(), BackendEvent, DeviceMessage (+23 more)

### Community 34 - "evidence.py"
Cohesion: 0.13
Nodes (22): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), line_limit_exceeded_event_json() (+14 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "BasicSerialPort"
Cohesion: 0.18
Nodes (7): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port., Return the owned raw serial port for the receive adapter.

### Community 37 - "GpioModeRegistry"
Cohesion: 0.08
Nodes (40): GpioControlChannelState, GpioModeRegistry, GpioModeRejection, GpioControlChannel, GpioModeRequestSource, GpioRoleName, Return current states for all physical control channels., Return the configured channel state for a role, if one exists. (+32 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.07
Nodes (23): DeviceCoreRuntime, DeviceCoreRuntimeError, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError, SessionWorkflow, Compose Phase 1 core services behind one service-facing object. (+15 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.05
Nodes (43): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, BackendEvent (+35 more)

### Community 40 - "UartIntegrity"
Cohesion: 0.22
Nodes (21): What the selected backend can report about upstream UART loss., UartIntegrity, CaptureSourceHealth, Immutable current-source connection, integrity, and replacement projection., monitored_runtime(), MutableHealthSource, FakeMonotonicClock, Path (+13 more)

### Community 41 - "parser.py"
Cohesion: 0.18
Nodes (28): InvalidUtf8Error, MalformedMessageError, ProtocolValidationError, ProtocolVersionError, Raised when a UTF-8 protocol frame is not valid JSON., Raised when a bounded frame body is not valid UTF-8., Raised when a JSON object does not match the v1 protocol contract., Raised when a device speaks an unsupported protocol version. (+20 more)

### Community 42 - "session_store/baseline.py"
Cohesion: 0.13
Nodes (30): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+22 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.11
Nodes (26): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+18 more)

### Community 44 - "FakeAsyncSerialReader"
Cohesion: 0.08
Nodes (21): FakeAsyncSerialReader, Fails if terminal input overtakes accepted evidence or changes on replay., Fails if a second hello is accepted as evidence or connection state., Fails if an uncorrelated response is dropped or exposed as evidence., Fails if post-hello input masks a retained parser terminal error., Fails if a timed-out readiness wait interferes with later FIFO admission., Fails if a terminal disconnect leaves readiness callers blocked or changes its…, Fails if a non-blocking evidence poll is rejected as an invalid timeout. (+13 more)

### Community 45 - "make_adapter"
Cohesion: 0.08
Nodes (25): make_adapter(), Fails if shutdown leaves the sole reader blocked or closes it more than once., Fails if pending-frame overflow loses its exact bounded size context., Fails if concurrent starts each own a reader or do not share one hello., Fails if same-batch evidence still terminalizes a valid hello handshake., Fails if segment readiness consumes the first normalized evidence event., Fails if terminal input failures leave readiness callers blocked or change…, Fails if hello resolves before later same-batch input is validated. (+17 more)

### Community 46 - "AsyncEnhancedSerialAdapter"
Cohesion: 0.10
Nodes (16): AsyncEnhancedSerialAdapter, _consume_hello_waiter_exception(), BackendEvent, Future, Return normalized identity after a valid hello., Return the session-local segment ID assigned by the caller., Return timestamp provenance once later event support establishes it., Start the sole reader and wait for its normalized hello. (+8 more)

### Community 47 - "gpio_config/config.py"
Cohesion: 0.17
Nodes (18): GpioConfigError, load_hardware_gpio_config(), _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, Path (+10 more)

### Community 48 - "Service-Owned Continuous Ingestion Design"
Cohesion: 0.09
Nodes (21): Active, Architectural Decision, Closing / Closed, Components And Boundaries, Concurrency Invariants, Context, `ContinuousIngestionCoordinator`, Coordinator State Model (+13 more)

### Community 49 - "BasicBackendEventSource"
Cohesion: 0.12
Nodes (11): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner. (+3 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "helpers.py"
Cohesion: 0.25
Nodes (13): disconnected_status(), _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _append_line(), _capture(), Path (+5 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.10
Nodes (18): DUTchMate Device Core Service package., BlockingCaptureSource, ClosableFakeRuntime, _hardware_config(), NoopDeviceControl, BackendEvent, ControlState, Exception (+10 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "Continuous Connection And Integrity Monitoring Design"
Cohesion: 0.08
Nodes (24): Acceptance Criteria, Architectural Decision, Buffer Overflow, Buffer Status, Concurrency And Ownership Invariants, Context, Continuous Connection And Integrity Monitoring Design, Coordinator State And Event Projection (+16 more)

### Community 55 - "store.py"
Cohesion: 0.04
Nodes (45): BaselineRuntime, SessionDetail, test_capture_summary_serializes_bounded_first_error_evidence(), _match(), DeviceCoreSessionStorage, Protocol, Return one authoritative stored detected-pattern record., Designate one eligible session as the project baseline. (+37 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.22
Nodes (27): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events() (+19 more)

### Community 57 - "SessionHandle"
Cohesion: 0.05
Nodes (37): Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session. (+29 more)

### Community 58 - "test_capture_workflows.py"
Cohesion: 0.13
Nodes (33): EnhancedCaptureFixtureRecorder, FakeCaptureEventSource, FakeMonotonicClock, fixed_clock(), fixed_id(), LifecycleCaptureEventSource, BackendEvent, datetime (+25 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.09
Nodes (46): _validate_session_command(), EvidenceTypeCount, FirstErrorReference, NativeSessionListItem, Raised when durable session evidence cannot be read or written., Compact first-error location used by bounded session list items., Bounded native lifecycle projection for one session list item., Logical size and optional record count for one session artifact. (+38 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.25
Nodes (27): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), MonkeyPatch, Path (+19 more)

### Community 63 - "persistence.py"
Cohesion: 0.13
Nodes (35): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+27 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.11
Nodes (17): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+9 more)

### Community 66 - "backend_reconnect.py"
Cohesion: 0.07
Nodes (21): _CandidateCleanupFailure, EnhancedReconnectHost, OpenBasicConnection, OpenEnhancedHost, Exception, Protocol, Service-owned backend reopen and replaceable-control composition., Keep a rejected candidate's primary failure distinct from close failure. (+13 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "device_actions.py"
Cohesion: 0.09
Nodes (27): DeviceActionError, DeviceActionResult, DeviceActionRunner, _format_utc(), datetime, RuntimeError, Hardware action workflows guarded by GPIO configuration state., Raised when firmware rejects a hardware action command. (+19 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "runtime.py"
Cohesion: 0.08
Nodes (34): Publish a newly connected backend control adapter., DeviceControl, ControlState, Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time., Apply one configured channel's active or idle state and return device time., CommandSuccessMessage (+26 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.21
Nodes (26): _create_capture(), datetime, MonkeyPatch, Path, _store(), test_atomic_write_failure_preserves_existing_pointer(), test_basic_not_observable_session_is_baseline_eligible(), test_dangling_or_corrupt_pointer_fails_reads_and_mutations() (+18 more)

### Community 73 - "BufferStatusEvent"
Cohesion: 0.19
Nodes (21): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., test_normalizes_buffer_telemetry(), MonkeyPatch, Path, test_append_buffer_overflow_can_write_nonzero_segment() (+13 more)

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 75 - "FakeAsyncFrameWriter"
Cohesion: 0.10
Nodes (19): FakeAsyncFrameWriter, Fails if same-batch response success masks invalid input or drops its prefix., Fails if post-transmission cancellation leaves an orphan response path., Fails if command routing consumes or reorders interleaved UART evidence., Fails if a response overtakes earlier evidence blocked outside the FIFO., Fails if a second uncorrelated command is written before the first resolves., Fails if async routing replaces write accounting or its repeatable terminal., Fails if caller cancellation leaves an uncorrelated response path alive. (+11 more)

### Community 76 - "CaptureRecorder"
Cohesion: 0.08
Nodes (16): CaptureRecorder, _normalized_control_timestamp(), BackendEvent, Route normalized backend events into UART processing and session storage., Handle for the session this recorder writes to., Session identifier this recorder writes to., Whether storage has already ended this recorder's native session., Observe terminalization performed by a coordinated external evidence writer. (+8 more)

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

### Community 81 - "FakeDeviceControl"
Cohesion: 0.20
Nodes (17): enhanced_info(), FakeDeviceControl, BackendCapability, ControlState, DeviceMessage, test_capture_uart_requires_message_source(), Path, test_apply_hardware_config_requires_connection() (+9 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "test_enhanced_serial.py"
Cohesion: 0.12
Nodes (18): _close_after_entering(), CloseBlockingAsyncSerialReader, _compact_json_frame_of_size(), Async Enhanced serial reader lifecycle tests., Fails if a full FIFO drops/reorders evidence or lets its sole reader advance., Fails if close strands hello or exposes a different terminal object., Fails if cancellation turns resource-close start into false completion., Fails if an invalid host frame reaches the serial writer. (+10 more)

### Community 84 - "CaptureWorkflow"
Cohesion: 0.10
Nodes (13): Return timestamp provenance once the source origin is established., CaptureRecordResult, CaptureWorkflow, CommandedBootMode, Exception, SessionWorkflow, Create one capture session., Record parsed transport messages until one fixed workflow deadline. (+5 more)

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

### Community 89 - "BackendDisconnectedError"
Cohesion: 0.14
Nodes (16): NoopDeviceControl, BackendEvent, BaseException, ControlState, Path, QueueSource, Catch startup health omitting initial identity, segment, or integrity., Catches replacement health omitting identity, integrity, or segment projection. (+8 more)

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
Cohesion: 0.14
Nodes (10): BlockingCloseSource, BlockingFailingCloseSource, EventReleasedByCloseSource, FailingCloseSource, BackendEvent, BaseException, test_close_while_workflow_active_is_safe_for_finally_cleanup(), test_concurrent_close_calls_share_exact_cleanup_error_and_close_once() (+2 more)

### Community 99 - "UartLineBuffer"
Cohesion: 0.18
Nodes (16): Buffer raw UART bytes until complete newline-terminated lines are available., Raw UART bytes not yet terminated by a newline., UartLineBuffer, test_byte_after_limit_discards_only_derived_copy_and_counts_until_lf(), test_exact_limit_line_is_emitted_normally(), test_feed_complete_line(), test_feed_multiple_lines(), test_feed_requires_bytes() (+8 more)

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.25
Nodes (6): _basic_segment(), ConditionBackedBasicSource, _publish_after_barrier(), test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator, ThreadEvent

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "test_backend_reconnect.py"
Cohesion: 0.12
Nodes (36): _build_async_enhanced_capture_reconnect(), build_basic_capture_reconnect(), build_enhanced_capture_reconnect(), ControlState, Keep runtime control ports stable while Enhanced transports are replaced., Keep the runtime UART-send port stable across backend replacement., Build coordinated idle and active reopen for one selected Basic backend., Build coordinated Enhanced reopen through the async host boundary. (+28 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 106 - "BackendInputError"
Cohesion: 0.09
Nodes (13): BackendInputKind, _ReaderFailure, BackendInputError, BackendMode, RuntimeError, Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context., BackendEvent (+5 more)

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
Cohesion: 0.39
Nodes (14): FakeMonotonicClock, parametrize, Path, Catch capability admission before newer connected monitor health is adopted., _runtime(), _store(), test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(), test_wait_pattern_excludes_oversized_lines_and_persists_default_matches() (+6 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.06
Nodes (35): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+27 more)

### Community 114 - "FakeDeviceControl"
Cohesion: 0.25
Nodes (6): FakeDeviceControl, _hello(), ControlState, DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status()

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.10
Nodes (28): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+20 more)

### Community 126 - "SerialFrameSink"
Cohesion: 0.18
Nodes (8): _ThreadedSerialFrameWriter, Protocol, Pyserial-compatible surface for exact host frame writes., Return the number of bytes accepted from data., Wait until accepted output is flushed., SerialFrameSink, Fails if a worker-thread write loses exact accepted-byte accounting., test_threaded_writer_preserves_partial_acceptance_error()

### Community 127 - ".start"
Cohesion: 0.37
Nodes (11): Create a capture session and return a recorder for it., Path, read_jsonl(), Path, test_finalize_persists_unterminated_oversized_line_descriptor(), test_record_buffer_overflow_writes_hardware_event(), test_record_buffer_status_writes_hardware_event(), test_record_event_rejects_unsupported_value() (+3 more)

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "backend_snapshot"
Cohesion: 0.15
Nodes (10): backend_snapshot(), Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open., segment(), test_failed_idle_replacement_publication_closes_candidate(), test_idle_replacement_commits_snapshot_and_next_connection_generation(), test_replacement_segment_failure_closes_candidate_without_publishing() (+2 more)

### Community 130 - "line_buffer.py"
Cohesion: 0.15
Nodes (9): OversizedUartLine, Line buffering for decoded DUT UART bytes., Return the trailing partial line, if any, and clear the buffer., Finalize trailing normal or oversized state at segment/session close., Bounded descriptor for one physical line that exceeded the derived limit., Normal lines and bounded oversized-line facts produced by one input., Consume UART bytes and return complete lines. Returned line `raw` values…, Consume bytes and return normal lines plus bounded overflow facts. (+1 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "enhanced_serial_io.py"
Cohesion: 0.12
Nodes (17): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, _OwnedStreamReader, Protocol, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., Return the next bytes or empty bytes for EOF. (+9 more)

### Community 134 - "send_uart_command"
Cohesion: 0.19
Nodes (12): Send one validated text command through the Device Core Service., send_uart_command(), _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., MonkeyPatch, test_format_forced_send_reports_attempt_and_evidence_pair() (+4 more)

### Community 135 - "FakeEnhancedAsyncHost"
Cohesion: 0.18
Nodes (4): FakeEnhancedAsyncHost, BackendEvent, BaseException, Synchronous test double for the service-owned async Enhanced host.

### Community 136 - "DeviceCoreStatus"
Cohesion: 0.12
Nodes (11): Return the current Device Core status., GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., StartupConfigRuntime, Core DUTchMate library. (+3 more)

### Community 137 - "File Map"
Cohesion: 0.20
Nodes (9): Enhanced Asynchronous Serial Adapter Implementation Plan, File Map, Global Constraints, Task 1: Expose Retained Parser Failure, Task 2: Start One Reader And Validate Hello, Task 3: Publish Normalized Events With Provenance, Task 4: Serialize And Dispatch Command Requests, Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown (+1 more)

### Community 138 - "File Responsibility Map"
Cohesion: 0.25
Nodes (7): Enhanced Asynchronous Serial I/O Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Extract The Exact Serial Frame Writer, Task 2: Add Concrete Async Stream Reader And Writer Wrappers, Task 3: Open And Start One Production Async Enhanced Adapter, Task 4: Reconcile The Exact Code Baseline

### Community 139 - "test_log_replay.py"
Cohesion: 0.50
Nodes (7): _native_store(), parametrize, Path, test_recent_logs_prefers_active_then_latest_terminal_native(), test_recent_logs_rejects_invalid_line_limit(), test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(), test_recent_logs_replays_complete_partial_and_oversized_records()

### Community 140 - "test_reader_failure_is_repeatable_disconnect"
Cohesion: 0.18
Nodes (10): Exception, parametrize, Fails if invalid values can create ambiguous reader or queue bounds., Fails if EOF/read failure is raw, transient, or loses its original cause., Fails if a non-positive or non-finite command timeout reaches the writer., Fails if invalid waits are passed to asyncio instead of rejected at the…, test_constructor_rejects_invalid_bounds(), test_reader_failure_is_repeatable_disconnect() (+2 more)

### Community 141 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 144 - "_request_after_entering"
Cohesion: 0.22
Nodes (11): Event, Fails if pre-transmission cancellation poisons the shared connection., Fails if close strands a consumer or closes its owned reader twice., Fails if close strands waiters, changes errors, or transmits queued work., Fails if close cannot release a transmitted request blocked in the writer., _receive_after_entering(), _request_after_entering(), test_cancel_while_waiting_for_command_lock_keeps_connection() (+3 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "HardwareGpioConfig"
Cohesion: 0.17
Nodes (10): Apply startup hardware control mappings., apply_startup_hardware_config(), load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., Apply startup GPIO mappings if a Debug Helper is already connected., test_apply_startup_hardware_config_skips_disconnected_runtime(), test_load_startup_hardware_config_returns_empty_config_when_missing() (+2 more)

### Community 147 - "CaptureReconnect"
Cohesion: 0.13
Nodes (11): CaptureReconnect, CaptureSourceMonitor, CaptureWorkflowLifecycle, Protocol, Optional current-source health observation boundary., Return one immutable current-source health snapshot., Optional fresh-cursor lifecycle implemented by continuous sources., Activate one new finite-workflow cursor. (+3 more)

### Community 148 - "BlockingCloseStreamWriter"
Cohesion: 0.33
Nodes (3): BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 149 - "test_transactions.py"
Cohesion: 0.57
Nodes (7): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 150 - "TransportTimeoutError"
Cohesion: 0.20
Nodes (10): Raised when the Debug Helper does not provide a complete message in time., TransportTimeoutError, Fails if response timeout permits reuse of an uncorrelated command stream., Fails if hello timeout leaks the reader or permits a later restart., Fails if a timed-out response leaves the reader or connection reusable., Fails if a missing hello leaks the reader or exposes asyncio timeout errors., test_command_timeout_closes_connection(), test_hello_timeout_is_transport_timeout_then_disconnect() (+2 more)

### Community 151 - "TerminationBarrierAdapter"
Cohesion: 0.20
Nodes (5): BlockingAsyncFrameWriter, Pause cleanup after request code has selected its terminal outcome., Fails if cancelling the response future races terminal cause selection., TerminationBarrierAdapter, test_cancellation_selects_terminal_before_response_can_be_orphaned()

### Community 152 - ".get_session"
Cohesion: 0.40
Nodes (3): SessionDetail, Return bounded schema-aware detail for one session., Return bounded session detail without expanding raw evidence arrays.

### Community 153 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 154 - "BackendUartSendResult"
Cohesion: 0.08
Nodes (24): Publish a newly connected UART-send adapter., BackendUartSendResult, BackendWriteError, Raised when a backend cannot accept a complete UART payload., Complete backend acceptance of one UART payload., Backend-neutral port for complete UART payload transmission., Submit every payload byte or raise a backend write error., UartSender (+16 more)

### Community 156 - "_BoundedNewest"
Cohesion: 0.40
Nodes (3): _BoundedNewest, _T, Retain the newest coordinate-ordered records with bounded memory.

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "test_host_command_encoder.py"
Cohesion: 0.06
Nodes (54): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command. (+46 more)

### Community 160 - "validate_session_max_size_mb"
Cohesion: 0.40
Nodes (6): Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., session_evidence_budget_bytes(), validate_session_max_size_mb(), test_session_max_size_accepts_positive_mib_values(), test_session_max_size_rejects_non_positive_integers()

### Community 161 - ".feed"
Cohesion: 0.40
Nodes (4): _frame_body(), DeviceMessage, Consume a serial byte chunk and return parsed complete messages., Return one exact JSON object body after removing one optional CR.

### Community 162 - "project_diagnostic_detail"
Cohesion: 0.40
Nodes (4): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _bounded_error()

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

### Community 184 - "test_close_wakes_idle_disconnect_waiter"
Cohesion: 0.50
Nodes (3): Wait until an idle source disconnect can be claimed for replacement., Catches close leaving an idle reconnect waiter blocked until its timeout., test_close_wakes_idle_disconnect_waiter()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **311 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+306 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `EnhancedDeviceControl` (7× useful, score=6.327597127) _(code changed — re-verify)_
- `Reconnect and Session Semantics` (4× useful, score=3.847314065)
- `DeviceCoreRuntime` (4× useful, score=3.797785478) _(code changed — re-verify)_
- `BackendEventSource` (4× useful, score=3.7401366)
- `Continuous Ingestion and Async Enhanced Adapter` (3× useful, score=2.847397054) _(code changed — re-verify)_
- `CaptureWorkflow` (3× useful, score=2.804070547) _(code changed — re-verify)_
- `SerialCommandTransport` (3× useful, score=2.737769252) _(code changed — re-verify)_
- `NdjsonStreamParser` (3× useful, score=2.735739733)
- `Phase 1 Implementation Spec` (2× useful, score=1.935276262)
- `Firmware RAM Report` (2× useful, score=1.935276262)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SegmentContext` connect `SegmentContext` to `backend_snapshot`, `FakeEnhancedAsyncHost`, `DeviceCoreStatus`, `UartReceiveEvent`, `FakeMonotonicClock`, `metadata.py`, `create_app`, `UartCaptureProcessor`, `CaptureEventSource`, `SessionStore`, `BackendUartSendResult`, `test_contracts.py`, `.__init__`, `enhanced.py`, `DeviceCoreRuntime`, `EnhancedAsyncHost`, `UartIntegrity`, `AsyncEnhancedSerialAdapter`, `BasicBackendEventSource`, `helpers.py`, `store.py`, `SessionHandle`, `test_capture_workflows.py`, `test_startup_config.py`, `backend_reconnect.py`, `test_capture_reconnect.py`, `runtime.py`, `CaptureRecorder`, `test_reconnect_evidence.py`, `CaptureWorkflow`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `test_backend_reconnect.py`, `BackendInputError`, `test_device_core_wait.py`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `SessionStore` connect `SessionStore` to `UartReceiveEvent`, `FakeMonotonicClock`, `test_log_replay.py`, `SegmentContext`, `UartCaptureProcessor`, `test_transactions.py`, `comparison.py`, `SessionListPage`, `test_basic.py`, `UartIntegrity`, `session_store/baseline.py`, `helpers.py`, `test_app_lifecycle.py`, `store.py`, `test_device_core_uart_send.py`, `SessionHandle`, `test_capture_workflows.py`, `retrieval.py`, `test_startup_config.py`, `persistence.py`, `test_capture_reconnect.py`, `test_baseline.py`, `BufferStatusEvent`, `test_retention.py`, `test_reconnect_evidence.py`, `FakeDeviceControl`, `BackendDisconnectedError`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `test_device_core_wait.py`, `FakeDeviceControl`, `test_device_core_lifecycle.py`, `.start`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `UartReceiveEvent` connect `UartReceiveEvent` to `ContinuousIngestionCoordinator`, `FakeMonotonicClock`, `test_log_replay.py`, `SegmentContext`, `UartCaptureProcessor`, `test_transactions.py`, `SessionStore`, `test_contracts.py`, `test_enhanced.py`, `enhanced.py`, `evidence.py`, `test_basic.py`, `EnhancedAsyncHost`, `FakeAsyncSerialReader`, `make_adapter`, `BasicBackendEventSource`, `helpers.py`, `store.py`, `test_device_core_uart_send.py`, `SessionHandle`, `test_capture_workflows.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `FakeAsyncFrameWriter`, `CaptureRecorder`, `test_enhanced_serial.py`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `test_backend_reconnect.py`, `BackendInputError`, `test_device_core_wait.py`, `.start`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 181 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()`) actually correct?**
  _`SessionStore` has 181 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 91 INFERRED edges - model-reasoned connections that need verification._