# Graph Report - DUTchMate  (2026-09-05)

## Corpus Check
- 308 files · ~228,097 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4563 nodes · 12157 edges · 213 communities (193 shown, 20 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2178 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a059f2c2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_backend_reconnect.py
- format_status
- dutchmate_cli/config.py
- client.py
- dutchmate_cli/main.py
- ContinuousIngestionCoordinator
- UartLine
- main
- settings.py
- backends/__init__.py
- DeviceCoreRuntime
- app.py
- NdjsonStreamParser
- metadata.py
- create_app
- UartLineBuffer
- runtime.py
- transport.py
- cdc_tx_state_harness.c
- parse_device_message
- UartReceiveEvent
- log_replay.py
- .read_event
- service_error_from_exception
- SerialPortCandidate
- store.py
- test_retrieval.py
- DeviceActionResult
- SessionPersistenceError
- test_session_endpoints.py
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- command_executor_harness.c
- evidence.py
- BasicBackendEventSource
- SegmentContext
- GpioModeRegistry
- DeviceCoreRuntimeError
- test_enhanced_async.py
- workflows/capture.py
- parser.py
- session_store/baseline.py
- dutchmate_cli/__init__.py
- test_enhanced_serial.py
- command_decode.c
- BackendInfo
- uart_rx_ring.c
- Service-Owned Continuous Ingestion Design
- test_send.py
- errors.schema.json
- helpers.py
- test_app_lifecycle.py
- logs.py
- Continuous Connection And Integrity Monitoring Design
- BaselineMutationResult
- test_device_core_uart_send.py
- SessionStore
- dmh_ndjson_framer_feed
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- BasicBackendConnection
- Enhanced Asynchronous Serial Adapter Design
- create_server
- CommandSuccessMessage
- test_capture_reconnect.py
- InputValidationError
- test_baseline.py
- EnhancedAsyncHost
- test_retention.py
- usb_connection.c
- CaptureWorkflow
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- gpio_config/config.py
- ._next_timestamp
- fixture_protocol.c
- dutchmate_usb_connection_run
- backend_reconnect.py
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- parse_hardware_gpio_config
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
- uart_tx_state_harness.c
- FakeEnhancedAsyncHost
- AsyncSerialReader
- Coordinated Background Reconnect Design
- ReplaceableDeviceControl
- Software Architecture
- test_dut.py
- BackendSnapshot
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- FakeMonotonicClock
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
- AsyncEnhancedDeviceControl
- Enhanced Async Service Integration Design
- BackendDisconnectedError
- uart_tx.c
- File Responsibility Map
- File Responsibility Map
- enhanced_serial_io.py
- WaitPatternResult
- _AsyncEnhancedAdapter
- apply_startup_hardware_config
- File Map
- File Responsibility Map
- test_log_replay.py
- telemetry.c
- _UnavailableDeviceControl
- test_gpio.py
- BasicSerialPort
- command_runtime.c
- File Responsibility Map
- DeviceActionError
- CaptureWorkflowLifecycle
- BlockingCloseStreamWriter
- test_recovery.py
- BackendCapabilityPolicy
- test_transactions.py
- _run
- test_device_message_examples.py
- uart_send.py
- FakeStreamTransport
- _run
- File Responsibility Map
- test_host_command_encoder.py
- _run
- RP2350 Debug Helper Firmware Design
- ScriptedBasicSerial
- CaptureSessionStorage
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
- test_close_wakes_idle_disconnect_waiter
- .begin_workflow
- _run_hello
- .discard_pending_events
- .end_workflow
- _CandidateCleanupFailure
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
- load_backend_config
- BackendEventSource
- UartSendSessionStorage
- test_main.py
- _BoundedNewest
- project_diagnostic_detail
- .__init__
- Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?
- test_cdc_tx_state_machine
- validate_wait_pattern
- .capture_source_health
- .close_current_source_for_reconnect
- .get_session

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 253 edges
2. `DeviceCoreRuntime` - 137 edges
3. `UartReceiveEvent` - 103 edges
4. `SegmentContext` - 94 edges
5. `create_app()` - 90 edges
6. `ContinuousIngestionCoordinator` - 81 edges
7. `FakeRuntime` - 73 edges
8. `SessionHandle` - 73 edges
9. `parse_device_message()` - 70 edges
10. `BackendSnapshot` - 67 edges

## Surprising Connections (you probably didn't know these)
- `executor_uart_start()` --calls--> `dmh_uart_tx_start()`  [INFERRED]
  tests/hardware/rp2350_debug_helper/command_executor_harness.c → hardware/firmware/rp2350_debug_helper/src/uart_tx_state.c
- `executor_uart_poll()` --calls--> `dmh_uart_tx_poll()`  [INFERRED]
  tests/hardware/rp2350_debug_helper/command_executor_harness.c → hardware/firmware/rp2350_debug_helper/src/uart_tx_state.c
- `Ring Buffer Validation Gate` --semantically_similar_to--> `Ring Buffer Acceptance Checklist`  [INFERRED] [semantically similar]
  docs/ring_buffer_sizing_plan.md → hardware/validation/phase1_ring_buffer.md
- `Safe High-Impedance Behavior` --semantically_similar_to--> `Hardware Safe Startup State`  [INFERRED] [semantically similar]
  docs/gpio_configuration_semantics.md → hardware/schematics/revision_a.md
- `_summary_from_metadata()` --calls--> `_first_error()`  [INFERRED]
  core/src/dutchmate_core/session_store/metadata.py → apps/cli/src/dutchmate_cli/capture.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DUTchMate Backend Pipeline** — readme_basic_backend, readme_enhanced_backend, readme_shared_host_processing_and_session_pipeline [EXTRACTED 1.00]
- **Graphify Operational Pipeline** — _codex_skills_graphify_skill_extraction_pipeline, _codex_skills_graphify_references_update_incremental_re_extraction, _codex_skills_graphify_skill_graph_health_check [EXTRACTED 1.00]
- **Bounded Evidence Integrity Contract** — docs_debug_agent_context_contract_bounded_hardware_evidence, docs_reconnect_session_semantics_incremental_evidence_writes, docs_software_architecture_session_store, docs_ring_buffer_sizing_plan_buffer_integrity_reporting, docs_mcp_integration_plan_bounded_tool_results [INFERRED 0.85]
- **Backend-Independent Evidence Pipeline** — docs_project_context_normalized_evidence_boundary, docs_phase1_implementation_spec_backend_independent_pipeline, docs_software_architecture_normalized_event_boundary, docs_software_architecture_backends_contracts [INFERRED 0.95]
- **Phase 1 Hardware Acceptance Gate** — docs_development_status_hardware_acceptance, docs_phase1_implementation_spec_phase1_done_criteria, docs_ring_buffer_sizing_plan_validation_gate, hardware_schematics_revision_a_prototype_validation, hardware_validation_phase1_ring_buffer_acceptance_checklist [INFERRED 0.95]

## Communities (213 total, 20 thin omitted)

### Community 0 - "test_backend_reconnect.py"
Cohesion: 0.11
Nodes (26): BackendReconnectCoordinator, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt., Stop reconnect activity and join the idle worker exactly once., ClosableSource, FakeSourceOwner, _release_stuck_attempt() (+18 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "dutchmate_cli/config.py"
Cohesion: 0.11
Nodes (35): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+27 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (64): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+56 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.11
Nodes (55): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+47 more)

### Community 5 - "ContinuousIngestionCoordinator"
Cohesion: 0.14
Nodes (44): ContinuousIngestionCoordinator, Continuously drain one source and expose an active-workflow FIFO., buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, MonkeyPatch, parametrize (+36 more)

### Community 6 - "UartLine"
Cohesion: 0.11
Nodes (29): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+21 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (45): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+37 more)

### Community 8 - "settings.py"
Cohesion: 0.13
Nodes (37): main(), Service entrypoint for DUTchMate., Start the Device Core Service., BackendConfig, BackendConfigError, _baudrate(), _boolean(), _finite_number() (+29 more)

### Community 9 - "backends/__init__.py"
Cohesion: 0.13
Nodes (52): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., Stable facade for normalized Device Core backend contracts., Fails if evidence is not normalized in wire order from its first timestamp., test_receive_event_normalizes_fifo_and_establishes_origin(), test_normalizes_buffer_telemetry() (+44 more)

### Community 10 - "DeviceCoreRuntime"
Cohesion: 0.13
Nodes (46): DeviceCoreRuntime, Compose Phase 1 core services behind one service-facing object., GPIO role configuration state used by this runtime., AdvancingMonotonicClock, enhanced_info(), FakeCaptureSource, FakeDeviceControl, BackendCapability (+38 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (52): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., baseline_mutation_payload(), BootModeRequest, BootTestRequest, capture_summary_payload(), CaptureRequest (+44 more)

### Community 12 - "NdjsonStreamParser"
Cohesion: 0.10
Nodes (28): UART bytes captured by the Debug Helper., UartMessage, _frame_body(), NdjsonStreamParser, DeviceMessage, NDJSON stream parsing for serial byte chunks., Buffer serial chunks and parse complete newline-terminated messages., Bytes buffered because they do not yet end in a newline. (+20 more)

### Community 13 - "metadata.py"
Cohesion: 0.09
Nodes (40): _append_resumed_backend_segment(), _backend_segment_json(), _capability_policy_json(), _contiguous_native_segments(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata(), _integrity_json() (+32 more)

### Community 14 - "create_app"
Cohesion: 0.14
Nodes (38): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, parametrize, test_boot_test_active_uses_conflict_error_contract(), test_boot_test_disconnected_uses_service_unavailable_contract() (+30 more)

### Community 15 - "UartLineBuffer"
Cohesion: 0.10
Nodes (24): OversizedUartLine, Return the trailing partial line, if any, and clear the buffer., Finalize trailing normal or oversized state at segment/session close., Bounded descriptor for one physical line that exceeded the derived limit., Normal lines and bounded oversized-line facts produced by one input., Buffer raw UART bytes until complete newline-terminated lines are available., Raw UART bytes not yet terminated by a newline., Consume UART bytes and return complete lines. Returned line `raw` values… (+16 more)

### Community 16 - "runtime.py"
Cohesion: 0.05
Nodes (65): BootMode, Host-to-device protocol command encoding., Service-facing Device Core runtime composition., GpioIdentifierValidationError, _is_unicode_whitespace(), prepare_uart_send_payload(), GpioControlChannel, ValueError (+57 more)

### Community 17 - "transport.py"
Cohesion: 0.10
Nodes (31): HostCommandFrameTooLargeError, Raised when an encoded host command exceeds its total wire-frame bound., _classify_serial_write_error(), Exception, TransportWriteErrorCode, Exact serial-frame writes shared by Enhanced transport adapters., Write and flush one complete frame with exact accepted-byte errors., write_serial_frame() (+23 more)

### Community 18 - "cdc_tx_state_harness.c"
Cohesion: 0.18
Nodes (23): cdc_callback(), dutchmate_cdc_tx_cancel(), dutchmate_cdc_tx_initialize(), dutchmate_cdc_tx_poll(), dutchmate_cdc_tx_start(), dmh_cdc_tx_cancel(), dmh_cdc_tx_driver_fault(), dmh_cdc_tx_init() (+15 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (63): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+55 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.09
Nodes (45): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission., Return bytes awaiting a line terminator for one segment and channel. (+37 more)

### Community 21 - "log_replay.py"
Cohesion: 0.12
Nodes (46): _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path, Bounded replay of persisted native UART evidence. (+38 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.09
Nodes (38): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+30 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.10
Nodes (36): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+28 more)

### Community 25 - "store.py"
Cohesion: 0.05
Nodes (58): test_recent_logs_payload_removes_oldest_whole_records_to_fit_body_cap(), Return recent UART evidence without requiring a backend connection., Compare stored evidence without requiring a backend connection., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary() (+50 more)

### Community 26 - "test_retrieval.py"
Cohesion: 0.22
Nodes (18): _create_native_session(), parametrize, Path, test_get_session_distinguishes_not_found_unsupported_and_corrupt(), test_latest_session_returns_newest_or_none(), test_legacy_session_detail_returns_only_identity_and_artifact_sizes(), test_list_sessions_applies_positive_limit(), test_list_sessions_ignores_unrelated_files_and_directories() (+10 more)

### Community 27 - "DeviceActionResult"
Cohesion: 0.07
Nodes (18): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Compare one terminal session with the designated baseline., Runtime surface needed by the current service API., Configure a control channel GPIO mode. (+10 more)

### Community 28 - "SessionPersistenceError"
Cohesion: 0.13
Nodes (38): Raised when durable session evidence cannot be read or written., Filesystem paths for the required Phase 1 session files., SessionPaths, SessionPersistenceError, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups() (+30 more)

### Community 29 - "test_session_endpoints.py"
Cohesion: 0.21
Nodes (11): _native_detail(), _native_item(), Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page() (+3 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.17
Nodes (15): SourceFactory, _basic_source(), _enhanced_source(), FakeBackendEventSource, BackendEvent, Exception, parametrize, Shared contract tests for normalized Basic and Enhanced event sources. (+7 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.11
Nodes (27): AsyncEnhancedUartSender, EnhancedNdjsonEventStream, Translate complete UART payloads through an async Enhanced transport., Parse Enhanced NDJSON chunks and expose only normalized evidence events., Return an incomplete Enhanced NDJSON frame buffered by the parser., FrameTooLargeError, Raised before decoding when a device-to-host frame exceeds its bound., FakeAsyncCommandTransport (+19 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "command_executor_harness.c"
Cohesion: 0.07
Nodes (80): dmh_command_executor_cancel_epoch(), dmh_command_executor_poll(), dmh_command_executor_reject(), dmh_command_executor_response(), dmh_command_executor_response_sent(), dmh_command_executor_submit(), map_control_result(), response_encoded() (+72 more)

### Community 34 - "evidence.py"
Cohesion: 0.13
Nodes (22): buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error(), line_limit_exceeded_event_json() (+14 more)

### Community 35 - "BasicBackendEventSource"
Cohesion: 0.06
Nodes (37): BasicSerialFactory, BasicBackendEventSource, open_basic_backend_connection(), BackendEvent, _pyserial_factory(), Basic generic USB-to-UART connection, receive, and send adapter., Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities. (+29 more)

### Community 36 - "SegmentContext"
Cohesion: 0.10
Nodes (8): EnhancedReconnectHost, Ready async Enhanced host used as source, control, and UART sender., Return the latest timestamp provenance published by the source., Session-local connection segment and its timestamp provenance., SegmentContext, Return timestamp provenance once later event support establishes it., Persist one immutable segment context before recording its events., setter

### Community 37 - "GpioModeRegistry"
Cohesion: 0.07
Nodes (51): _format_utc_timestamp(), GpioControlChannelState, GpioModeRegistry, GpioModeRejection, datetime, GpioControlChannel, GpioModeRequestSource, GpioRoleName (+43 more)

### Community 38 - "DeviceCoreRuntimeError"
Cohesion: 0.07
Nodes (20): apply_capability_policy(), BackendCapability, Filter backend support through the shared host capability policy., Core DUTchMate library., DeviceCoreRuntimeError, BackendCapability, GpioRoleName, RuntimeError (+12 more)

### Community 39 - "test_enhanced_async.py"
Cohesion: 0.18
Nodes (25): open_enhanced_async_host(), Open one ready Enhanced adapter on its permanent owner loop., FakeAsyncEnhancedAdapter, _info(), OpenAdapterFake, BackendEvent, BaseException, DeviceMessage (+17 more)

### Community 40 - "workflows/capture.py"
Cohesion: 0.13
Nodes (28): _close_source(), _project_event_health(), Exception, Service-owned continuous draining for finite capture workflows., Transfer one validated replacement into the stable coordinator., _source_segment(), What the selected backend can report about upstream UART loss., UartIntegrity (+20 more)

### Community 41 - "parser.py"
Cohesion: 0.17
Nodes (30): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol boundaries., Base class for host-device protocol errors. (+22 more)

### Community 42 - "session_store/baseline.py"
Cohesion: 0.12
Nodes (30): Register service exception handlers on an app., register_error_handlers(), BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime (+22 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.08
Nodes (33): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+25 more)

### Community 44 - "test_enhanced_serial.py"
Cohesion: 0.03
Nodes (115): BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, _compact_json_frame_of_size(), FakeAsyncFrameWriter, FakeAsyncSerialReader, make_adapter(), Event (+107 more)

### Community 45 - "command_decode.c"
Cohesion: 0.15
Nodes (29): append_string_byte(), base64_value(), decode_base64(), decode_channel(), decode_configure(), decode_level(), decode_pulse(), decode_state() (+21 more)

### Community 46 - "BackendInfo"
Cohesion: 0.06
Nodes (33): BackendInputKind, BackendInfo, BackendInputError, integrity_for_backend(), BackendMode, Return the initial UART-loss observation state for a backend mode., Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context. (+25 more)

### Community 47 - "uart_rx_ring.c"
Cohesion: 0.22
Nodes (28): append_descriptor(), copy_into_ring(), dmh_uart_rx_ring_claim_overflow(), dmh_uart_rx_ring_init(), dmh_uart_rx_ring_next_observation(), dmh_uart_rx_ring_peek_observation(), dmh_uart_rx_ring_push(), dmh_uart_rx_ring_snapshot() (+20 more)

### Community 48 - "Service-Owned Continuous Ingestion Design"
Cohesion: 0.09
Nodes (21): Active, Architectural Decision, Closing / Closed, Components And Boundaries, Concurrency Invariants, Context, `ContinuousIngestionCoordinator`, Coordinator State Model (+13 more)

### Community 49 - "test_send.py"
Cohesion: 0.22
Nodes (9): _display(), format_uart_send(), CLI formatting for UART-send outcomes., Format a complete standalone or forced in-session UART send., MonkeyPatch, test_format_forced_send_reports_attempt_and_evidence_pair(), test_send_client_forwards_text_flags_without_raw_encoding(), test_send_client_validates_final_payload_before_http() (+1 more)

### Community 50 - "errors.schema.json"
Cohesion: 0.08
Nodes (25): additionalProperties, $comment, minLength, type, enum, type, $id, const (+17 more)

### Community 51 - "helpers.py"
Cohesion: 0.18
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

### Community 55 - "BaselineMutationResult"
Cohesion: 0.05
Nodes (23): Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., DeviceCoreSessionStorage, Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected native session. (+15 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.13
Nodes (31): BackendUartSendResult, Complete backend acceptance of one UART payload., Submit every payload byte or raise a backend write error., RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore (+23 more)

### Community 57 - "SessionStore"
Cohesion: 0.06
Nodes (35): _append_line(), Reference to a created debug session., SessionHandle, CommandedBootMode, SessionDetail, SessionWorkflow, Durably append a forced-send attempt and reserve its result record., Create filesystem-backed debug sessions. (+27 more)

### Community 58 - "dmh_ndjson_framer_feed"
Cohesion: 0.18
Nodes (25): dmh_command_ingress_feed(), dmh_command_ingress_init(), dmh_command_ingress_reset(), dmh_ndjson_framer_feed(), dmh_ndjson_framer_init(), dmh_ndjson_framer_reset(), expect_none(), feed_one() (+17 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.07
Nodes (49): test_capture_summary_serializes_bounded_first_error_evidence(), EvidenceTypeCount, FirstError, FirstErrorReference, LegacySessionListItem, NativeSessionListItem, Reference-bearing view of the first stored failure-pattern match., Compact summary of a debug session for workflow/API responses. (+41 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.25
Nodes (27): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), MonkeyPatch, Path (+19 more)

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
Cohesion: 0.10
Nodes (20): build_basic_capture_reconnect(), Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter., Build coordinated idle and active reopen for one selected Basic backend., Return an opened Basic connection., ReplaceableUartSender, _basic_settings(), FakeBasicSerial (+12 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.07
Nodes (52): DeviceControlError, Backend-neutral identity, timing, event, and receive-source contracts., Raised when a backend rejects or cannot complete a semantic control operation., _control_success_timestamp(), enhanced_message_timestamp_us(), enhanced_segment_context(), normalize_enhanced_hello(), normalize_enhanced_message() (+44 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "InputValidationError"
Cohesion: 0.08
Nodes (32): DeviceControl, ControlState, Protocol, Backend-neutral port for complete UART payload transmission., Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time., Apply one configured channel's active or idle state and return device time. (+24 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.49
Nodes (13): _create_capture(), datetime, MonkeyPatch, Path, _store(), test_atomic_write_failure_preserves_existing_pointer(), test_basic_not_observable_session_is_baseline_eligible(), test_dangling_or_corrupt_pointer_fails_reads_and_mutations() (+5 more)

### Community 73 - "EnhancedAsyncHost"
Cohesion: 0.11
Nodes (7): EnhancedAsyncHost, BackendEvent, ControlState, T, Return the owner-loop thread identity for lifecycle diagnostics., Terminalize the adapter once, then stop and join its owner loop., Own one asyncio loop and expose its Enhanced adapter synchronously.

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 75 - "usb_connection.c"
Cohesion: 0.13
Nodes (3): dmh_hello_encode(), is_safe_firmware_byte(), main()

### Community 76 - "CaptureWorkflow"
Cohesion: 0.06
Nodes (65): CaptureRecorder, CaptureRecordResult, CaptureWorkflow, _normalized_control_timestamp(), BackendEvent, Exception, Result of recording one normalized event into a capture session., Route normalized backend events into UART processing and session storage. (+57 more)

### Community 77 - "Ring Buffer Sizing Plan"
Cohesion: 0.18
Nodes (13): Revision A and Phase 1 Hardware Acceptance, 32 KiB UART RX Ring Buffer, Buffer Integrity Reporting, Drop-Oldest Overflow Policy, RP2040 Memory Budget, Ring Buffer Sizing Plan, Ring Buffer Validation Gate, Ring Buffer Acceptance Checklist (+5 more)

### Community 78 - "DUTchMate Project Context"
Cohesion: 0.17
Nodes (13): Backend-Independent Host Pipeline, Phase 1A Basic Backend, Phase 1B Enhanced Backend, Enhanced NDJSON Protocol Contract, Normalized Backend Contract, AI-Assisted Embedded Debugging, Human and AI Clients, Normalized Evidence Boundary (+5 more)

### Community 79 - "test_reconnect_evidence.py"
Cohesion: 0.44
Nodes (12): _create_active_session(), parametrize, Path, _snapshot_for_segment(), test_disconnect_and_resume_append_segment_lifecycle_evidence(), test_disconnect_quota_rejection_keeps_summary_without_detailed_event(), test_reconnect_quota_rejection_does_not_publish_new_segment(), test_resume_rejects_incompatible_backend_without_writing() (+4 more)

### Community 80 - "gpio_config/config.py"
Cohesion: 0.11
Nodes (25): Apply startup hardware control mappings., load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., test_load_startup_hardware_config_returns_empty_config_when_missing(), GpioConfigError, HardwareGpioConfig, load_hardware_gpio_config() (+17 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "dutchmate_usb_connection_run"
Cohesion: 0.09
Nodes (26): dmh_command_executor_init(), dutchmate_command_runtime_discard_input(), dutchmate_command_runtime_end_epoch(), dutchmate_command_runtime_faulted(), dutchmate_command_runtime_initialize(), dutchmate_command_runtime_start_epoch(), dmh_connection_epoch_init(), dmh_connection_epoch_update() (+18 more)

### Community 84 - "backend_reconnect.py"
Cohesion: 0.10
Nodes (23): backend_snapshot(), _build_async_enhanced_capture_reconnect(), build_enhanced_capture_reconnect(), OpenBasicConnection, OpenCaptureReplacement, OpenEnhancedHost, Event, Protocol (+15 more)

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): _build_harness(), CompletedProcess, Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "parse_hardware_gpio_config"
Cohesion: 0.16
Nodes (23): HardwareControlMapping, parse_hardware_gpio_config(), Configured mapping from a DUTchMate control channel to a DUT role., Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level() (+15 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "test_connection_monitoring.py"
Cohesion: 0.15
Nodes (15): enhanced_replacement_snapshot(), NoopDeviceControl, BackendEvent, BaseException, ControlState, Path, QueueSource, Catch startup health omitting initial identity, segment, or integrity. (+7 more)

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

### Community 99 - "uart_tx_state_harness.c"
Cohesion: 0.29
Nodes (18): dmh_uart_tx_cancel(), dmh_uart_tx_driver_fault(), dmh_uart_tx_init(), dmh_uart_tx_on_interrupt(), dmh_uart_tx_poll(), dmh_uart_tx_start(), finish(), executor_uart_cancel() (+10 more)

### Community 100 - "FakeEnhancedAsyncHost"
Cohesion: 0.11
Nodes (10): _basic_segment(), ConditionBackedBasicSource, FakeEnhancedAsyncHost, _publish_after_barrier(), BackendEvent, BaseException, Synchronous test double for the service-owned async Enhanced host., test_real_coordinator_discards_idle_basic_event_before_capture() (+2 more)

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "ReplaceableDeviceControl"
Cohesion: 0.11
Nodes (23): ControlState, Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., ReplaceableDeviceControl, _enhanced_info(), _enhanced_settings(), FakeClock, FakeControl (+15 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 106 - "BackendSnapshot"
Cohesion: 0.07
Nodes (18): Accept ownership of one validated concrete replacement., BackendSnapshot, Backend identity, effective policy, timing, and integrity for one segment., Return timestamp provenance once the source origin is established., BackendEvent, Map one live connection source onto a new session-local segment zero., Advance a wait cursor on the wrapped source when supported., Close the live source represented by this session-local view. (+10 more)

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

### Community 111 - "FakeMonotonicClock"
Cohesion: 0.17
Nodes (21): Immutable timestamp provenance for one continuous connection segment., Software policy controlling whether backend UART transmission is usable., SegmentTimestamp, UartSendCapabilityPolicy, FakeMonotonicClock, BackendEvent, Exception, FakeMonotonicClock (+13 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.06
Nodes (33): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+25 more)

### Community 114 - "FakeDeviceControl"
Cohesion: 0.25
Nodes (6): FakeDeviceControl, _hello(), ControlState, DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status()

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.10
Nodes (28): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+20 more)

### Community 126 - "SerialFrameSink"
Cohesion: 0.15
Nodes (10): _ThreadedSerialFrameWriter, Protocol, Pyserial-compatible surface for exact host frame writes., Return the number of bytes accepted from data., Wait until accepted output is flushed., SerialFrameSink, Fails if command writes use the event loop or skip partial-write recovery., Fails if a worker-thread write loses exact accepted-byte accounting. (+2 more)

### Community 127 - "AsyncEnhancedDeviceControl"
Cohesion: 0.17
Nodes (8): AsyncEnhancedDeviceControl, ControlState, Translate semantic control operations through an async Enhanced transport., AsyncCommandTransport, DeviceMessage, Protocol, Asynchronous one-at-a-time host command exchange., Send one complete command and return its parsed response.

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "BackendDisconnectedError"
Cohesion: 0.11
Nodes (18): Close the source and join the single ingestion thread., backend_snapshot(), Catches an idle reconnect path that requires a synthetic workflow read., Catches an idle claimant detaching a source owned by an active workflow., Catches changing active reconnect callers to require the idle claim path., Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open. (+10 more)

### Community 130 - "uart_tx.c"
Cohesion: 0.17
Nodes (10): command_uart_cancel(), command_uart_poll(), command_uart_start(), dut_uart_callback(), mark_driver_fault(), dutchmate_uart_tx_cancel(), dutchmate_uart_tx_driver_fault(), dutchmate_uart_tx_handle_interrupt() (+2 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "enhanced_serial_io.py"
Cohesion: 0.12
Nodes (17): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, _OwnedStreamReader, Protocol, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., Return the next bytes or empty bytes for EOF. (+9 more)

### Community 134 - "WaitPatternResult"
Cohesion: 0.22
Nodes (10): _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error(), test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(), test_wait_pattern_endpoint_returns_structured_capability_error(), test_wait_pattern_endpoint_serializes_authoritative_match_reference(), test_wait_pattern_timeout_is_successful_with_null_match_fields(), WaitRuntime (+2 more)

### Community 135 - "_AsyncEnhancedAdapter"
Cohesion: 0.11
Nodes (11): _AsyncEnhancedAdapter, _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, DeviceMessage, Future, Protocol (+3 more)

### Community 136 - "apply_startup_hardware_config"
Cohesion: 0.18
Nodes (9): apply_startup_hardware_config(), GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., Apply startup GPIO mappings if a Debug Helper is already connected., StartupConfigRuntime (+1 more)

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
Cohesion: 0.17
Nodes (7): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port., Return the owned raw serial port for the receive adapter.

### Community 144 - "command_runtime.c"
Cohesion: 0.30
Nodes (14): atomic_val_t, cdc_rx_thread(), command_thread(), dutchmate_command_runtime_response_sent(), dutchmate_command_runtime_take_response(), epoch_matches(), mark_runtime_fault(), publish_response() (+6 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "DeviceActionError"
Cohesion: 0.20
Nodes (7): DeviceActionError, _format_utc(), datetime, RuntimeError, Raised when firmware rejects a hardware action command., Pulse the DUT reset role after confirming reset GPIO configuration., Set DUT boot mode after confirming boot GPIO configuration.

### Community 147 - "CaptureWorkflowLifecycle"
Cohesion: 0.18
Nodes (8): CaptureSourceMonitor, CaptureWorkflowLifecycle, Protocol, Optional current-source health observation boundary., Return one immutable current-source health snapshot., Optional fresh-cursor lifecycle implemented by continuous sources., Activate one new finite-workflow cursor., Release the active cursor and discard its unread events.

### Community 148 - "BlockingCloseStreamWriter"
Cohesion: 0.33
Nodes (3): BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 149 - "test_recovery.py"
Cohesion: 0.35
Nodes (14): _clock(), _create_active_native(), datetime, MonkeyPatch, parametrize, Path, _recovery_clock(), _snapshot() (+6 more)

### Community 150 - "BackendCapabilityPolicy"
Cohesion: 0.25
Nodes (6): Return the current Device Core status., test_status_returns_connected_gpio_mapping_state(), BackendCapabilityPolicy, Host policy snapshot applied to backend-reported capabilities., DeviceCoreStatus, Current service-facing Device Core state.

### Community 151 - "test_transactions.py"
Cohesion: 0.56
Nodes (8): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_keeps_unit_when_expected_metadata_was_written(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 152 - "_run"
Cohesion: 0.32
Nodes (11): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), test_uart_event_accepts_bounded_staging_maximum(), test_uart_event_encodes_binary_and_base64_padding() (+3 more)

### Community 153 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 154 - "uart_send.py"
Cohesion: 0.08
Nodes (25): Send one validated text command to the DUT UART., Write a complete UART payload, retrying ordered short writes., BackendCapabilityError, BackendWriteError, RuntimeError, Raised when an operation is disabled or unsupported by the backend., Raised when a backend cannot accept a complete UART payload., BaseException (+17 more)

### Community 156 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, response_harness(), _run(), test_error_response_preserves_utf8_and_escapes_json() (+2 more)

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "test_host_command_encoder.py"
Cohesion: 0.05
Nodes (53): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command., Build a validated `pulse_control` command. (+45 more)

### Community 159 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), telemetry_harness(), test_buffer_overflow_matches_canonical_v1_frame() (+2 more)

### Community 160 - "RP2350 Debug Helper Firmware Design"
Cohesion: 0.20
Nodes (9): Authority And Scope, Component Boundaries, Concurrency And Interrupt Ownership, Existing Contract Alignment, Failure Semantics, RP2350 Debug Helper Firmware Design, Safe-State Lifecycle, Test Boundary And Milestone Evidence (+1 more)

### Community 162 - "CaptureSessionStorage"
Cohesion: 0.10
Nodes (11): CaptureSessionStorage, Persistence operations required by the capture application service., Persist one accepted normalized control action., Persist one buffer-overflow evidence unit., Persist one buffer-status evidence unit., Persist immutable timestamp provenance for a capture segment., Close the current segment and return the persisted segment count., Append a validated reconnect segment and return its segment ID. (+3 more)

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

### Community 184 - "test_close_wakes_idle_disconnect_waiter"
Cohesion: 0.50
Nodes (3): Wait until an idle source disconnect can be claimed for replacement., Catches close leaving an idle reconnect waiter blocked until its timeout., test_close_wakes_idle_disconnect_waiter()

### Community 186 - "_run_hello"
Cohesion: 0.44
Nodes (8): _build_harness(), CompletedProcess, parametrize, Path, _run_hello(), test_hello_accepts_64_byte_safe_firmware_identifier(), test_hello_matches_complete_v1_identity_and_capability_contract(), test_hello_rejects_unsafe_firmware_identifier()

### Community 189 - "_CandidateCleanupFailure"
Cohesion: 0.29
Nodes (5): _CandidateCleanupFailure, _close_unpublished_candidate(), BaseException, Exception, Keep a rejected candidate's primary failure distinct from close failure.

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
Cohesion: 0.67
Nodes (6): _build_harness(), Path, _run_states(), test_epoch_can_start_when_first_observation_is_asserted(), test_epoch_restarts_after_each_completed_disconnect(), test_epoch_starts_once_per_dtr_assertion_and_ends_on_loss()

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
Cohesion: 0.40
Nodes (4): Build, Current slice, DUTchMate RP2350 Debug Helper Firmware, Revision A mapping

### Community 198 - "test_control_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_control_state_machine()

### Community 199 - "test_uart_tx_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_uart_tx_state_machine()

### Community 200 - "load_backend_config"
Cohesion: 0.29
Nodes (7): load_backend_config(), Any, Path, Load backend/UART configuration from a TOML file., _toml_module(), Path, test_load_backend_config_reads_shared_project_toml()

### Community 201 - "BackendEventSource"
Cohesion: 0.22
Nodes (6): BackendEventSource, BackendEvent, Asynchronous FIFO source of normalized events from one backend connection., Return immutable identity and physical capability information., Return the session-local segment ID assigned to this source., Return the next FIFO event, or ``None`` for an ordinary read timeout.

### Community 202 - "UartSendSessionStorage"
Cohesion: 0.29
Nodes (5): Protocol, Perturbation evidence operations required by UART send., Append an admitted pre-dispatch attempt., Append the matching post-dispatch result., UartSendSessionStorage

### Community 203 - "test_main.py"
Cohesion: 0.33
Nodes (3): Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn()

### Community 204 - "_BoundedNewest"
Cohesion: 0.40
Nodes (3): _BoundedNewest, _T, Retain the newest coordinate-ordered records with bounded memory.

### Community 205 - "project_diagnostic_detail"
Cohesion: 0.40
Nodes (4): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _bounded_error()

### Community 207 - "Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?, Source Nodes

### Community 208 - "test_cdc_tx_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_cdc_tx_state_machine()

### Community 209 - "validate_wait_pattern"
Cohesion: 0.50
Nodes (3): _validate_patterns(), Validate and preserve one case-sensitive literal wait pattern., validate_wait_pattern()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **330 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+325 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `Reconnect and Session Semantics` (4× useful, score=3.428679803)
- `DeviceCoreRuntime` (4× useful, score=3.384540526)
- `BackendEventSource` (4× useful, score=3.333164542)
- `Continuous Ingestion and Async Enhanced Adapter` (3× useful, score=2.537565846) _(code changed — re-verify)_
- `CaptureWorkflow` (3× useful, score=2.498953787)
- `Phase 1 Implementation Spec` (2× useful, score=1.724694819)
- `Firmware RAM Report` (2× useful, score=1.724694819)
- `build_startup_runtime()` (2× useful, score=1.700509624)
- `FrameTooLargeError` (2× useful, score=1.619081237)
- `Development Status` (2× useful, score=1.618485551) _(code changed — re-verify)_

**Known dead ends** — questions that led nowhere; don't re-derive.
- "What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?" -> `NdjsonStreamParser`, `AsyncEnhancedSerialAdapter`

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `backends/__init__.py`, `DeviceCoreRuntime`, `test_log_replay.py`, `UartReceiveEvent`, `test_recovery.py`, `test_transactions.py`, `store.py`, `test_retrieval.py`, `SessionPersistenceError`, `test_session_endpoints.py`, `BasicBackendEventSource`, `SegmentContext`, `workflows/capture.py`, `session_store/baseline.py`, `helpers.py`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `retrieval.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_retention.py`, `CaptureWorkflow`, `test_reconnect_evidence.py`, `test_connection_monitoring.py`, `test_comparison.py`, `FakeEnhancedAsyncHost`, `BackendSnapshot`, `FakeMonotonicClock`, `FakeDeviceControl`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `test_backend_reconnect.py`, `UartLine`, `WaitPatternResult`, `runtime.py`, `DeviceActionError`, `CaptureWorkflowLifecycle`, `UartReceiveEvent`, `BackendCapabilityPolicy`, `store.py`, `uart_send.py`, `DeviceActionResult`, `SegmentContext`, `GpioModeRegistry`, `DeviceCoreRuntimeError`, `workflows/capture.py`, `session_store/baseline.py`, `BackendInfo`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionStore`, `retrieval.py`, `test_startup_config.py`, `CommandSuccessMessage`, `InputValidationError`, `CaptureWorkflow`, `test_connection_monitoring.py`, `BackendSnapshot`, `FakeMonotonicClock`, `FakeDeviceControl`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `test_backend_reconnect.py`, `BackendDisconnectedError`, `_AsyncEnhancedAdapter`, `backends/__init__.py`, `DeviceCoreRuntime`, `metadata.py`, `runtime.py`, `test_recovery.py`, `BackendCapabilityPolicy`, `store.py`, `uart_send.py`, `test_contracts.py`, `CaptureSessionStorage`, `BasicBackendEventSource`, `DeviceCoreRuntimeError`, `test_enhanced_async.py`, `workflows/capture.py`, `BackendInfo`, `helpers.py`, `SessionStore`, `retrieval.py`, `test_startup_config.py`, `CommandSuccessMessage`, `test_capture_reconnect.py`, `InputValidationError`, `EnhancedAsyncHost`, `CaptureWorkflow`, `test_reconnect_evidence.py`, `backend_reconnect.py`, `test_connection_monitoring.py`, `test_comparison.py`, `FakeEnhancedAsyncHost`, `ReplaceableDeviceControl`, `BackendSnapshot`, `FakeMonotonicClock`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 182 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()`) actually correct?**
  _`SessionStore` has 182 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 91 INFERRED edges - model-reasoned connections that need verification._