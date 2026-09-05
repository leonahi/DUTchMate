# Graph Report - DUTchMate  (2026-09-05)

## Corpus Check
- 301 files · ~225,792 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4522 nodes · 12052 edges · 202 communities (187 shown, 15 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 2138 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `177ba3b1`
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
- enhanced.py
- metadata.py
- create_app
- modes.py
- validation.py
- transport.py
- BackendInfo
- parse_device_message
- UartReceiveEvent
- log_replay.py
- continuous_ingestion.py
- service_error_from_exception
- SerialPortCandidate
- models.py
- SessionStore
- DeviceActionResult
- SessionPersistenceError
- SessionListPage
- test_contracts.py
- test_enhanced.py
- test_enhanced_serial_io.py
- command_executor_harness.c
- store.py
- test_basic.py
- SegmentContext
- GpioModeRegistry
- DeviceCoreRuntime
- test_enhanced_async.py
- UartIntegrity
- parser.py
- session_store/baseline.py
- dutchmate_cli/__init__.py
- test_enhanced_serial.py
- command_decode.c
- BackendInputError
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
- SessionHandle
- FakeMonotonicClock
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- BasicBackendEventSource
- Enhanced Asynchronous Serial Adapter Design
- create_server
- CommandSuccessMessage
- test_capture_reconnect.py
- contracts.py
- test_baseline.py
- EnhancedAsyncHost
- test_retention.py
- platform_io.c
- CaptureRecorder
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- parse_hardware_gpio_config
- ._next_timestamp
- fixture_protocol.c
- dutchmate_usb_connection_run
- CaptureWorkflow
- Revision A Voltage-Domain GPIO and UART Interface
- test_fixture_protocol.py
- format_wait_pattern
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
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- Coordinated Background Reconnect Design
- startup.py
- Software Architecture
- test_dut.py
- BackendSnapshot
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- backends/__init__.py
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
- fixed_clock
- Enhanced Async Service Integration Design
- BackendDisconnectedError
- uart_rx.c
- File Responsibility Map
- File Responsibility Map
- _StreamWriter
- device_actions.py
- _AsyncEnhancedAdapter
- DeviceCoreStatus
- File Map
- File Responsibility Map
- test_log_replay.py
- telemetry.c
- _UnavailableDeviceControl
- test_gpio.py
- test_capture_workflows.py
- command_runtime.c
- File Responsibility Map
- SessionRecoveryResult
- runtime.py
- BlockingCloseStreamWriter
- test_recovery.py
- enhanced_serial_io.py
- TerminationBarrierAdapter
- _run
- test_device_message_examples.py
- BackendUartSendResult
- FakeStreamTransport
- _run
- File Responsibility Map
- test_host_command_encoder.py
- _run
- RP2350 Debug Helper Firmware Design
- .feed
- SessionMutationLock
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
- test_backend_sources_preserve_fifo_uart_events
- .receive_event

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
- `executor_uart_cancel()` --calls--> `dmh_uart_tx_cancel()`  [INFERRED]
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

## Communities (202 total, 15 thin omitted)

### Community 0 - "test_backend_reconnect.py"
Cohesion: 0.08
Nodes (31): BackendReconnectCoordinator, OpenCaptureReplacement, Event, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt., Stop reconnect activity and join the idle worker exactly once., Open one segment-bound replacement source. (+23 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "dutchmate_cli/config.py"
Cohesion: 0.10
Nodes (38): CliConfig, CliConfigError, DaemonConfig, load_cli_config(), _optional_port(), _optional_positive_int(), _optional_str(), _optional_table() (+30 more)

### Community 3 - "client.py"
Cohesion: 0.07
Nodes (64): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+56 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.14
Nodes (48): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+40 more)

### Community 5 - "ContinuousIngestionCoordinator"
Cohesion: 0.12
Nodes (51): ContinuousIngestionCoordinator, Continuously drain one source and expose an active-workflow FIFO., buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, MonkeyPatch, parametrize (+43 more)

### Community 6 - "workflows/capture.py"
Cohesion: 0.06
Nodes (53): PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order., Return all configured patterns present in one completed UART line., Return pattern matches for a sequence of completed UART lines. (+45 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (43): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+35 more)

### Community 8 - "settings.py"
Cohesion: 0.09
Nodes (46): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), BackendConfig, BackendConfigError, _baudrate() (+38 more)

### Community 9 - "fixed_clock"
Cohesion: 0.14
Nodes (51): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., Fails if evidence is not normalized in wire order from its first timestamp., test_receive_event_normalizes_fifo_and_establishes_origin(), test_normalizes_buffer_telemetry(), enhanced_snapshot() (+43 more)

### Community 10 - "FakeDeviceControl"
Cohesion: 0.13
Nodes (47): AdvancingMonotonicClock, enhanced_info(), FakeCaptureSource, FakeDeviceControl, FakeMonotonicClock, BackendCapability, DeviceMessage, _fixed_session_time() (+39 more)

### Community 11 - "app.py"
Cohesion: 0.05
Nodes (56): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., Register service exception handlers on an app., register_error_handlers(), Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest (+48 more)

### Community 12 - "enhanced.py"
Cohesion: 0.07
Nodes (47): backend_input_error_from_protocol(), enhanced_message_timestamp_us(), normalize_enhanced_hello(), normalize_enhanced_message(), BackendEvent, DeviceMessage, Enhanced v1 protocol adapters and normalized event translation., Translate one Enhanced hello message into backend-neutral identity. (+39 more)

### Community 13 - "metadata.py"
Cohesion: 0.07
Nodes (46): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _append_resumed_backend_segment(), _backend_segment_json(), _bounded_error(), _capability_policy_json(), _contiguous_native_segments() (+38 more)

### Community 14 - "create_app"
Cohesion: 0.13
Nodes (40): create_app(), Path, Create the Device Core Service application., connected_status(), FakeRuntime, SessionDetail, parametrize, test_boot_test_active_uses_conflict_error_contract() (+32 more)

### Community 15 - "modes.py"
Cohesion: 0.11
Nodes (20): _format_utc_timestamp(), datetime, GPIO role configuration state tracking., _utc_now(), GpioModeRequestSource, Configure one GPIO role through firmware and update runtime state., GpioControlChannel, GpioModeRequestSource (+12 more)

### Community 16 - "validation.py"
Cohesion: 0.06
Nodes (54): BootMode, GpioIdentifierValidationError, _is_unicode_whitespace(), prepare_uart_send_payload(), ValueError, Shared validation for public Device Core input contracts., Return a valid Phase 1 capture duration in seconds., Return a valid Phase 1 wait-pattern timeout in seconds. (+46 more)

### Community 17 - "transport.py"
Cohesion: 0.10
Nodes (29): _classify_serial_write_error(), Exception, TransportWriteErrorCode, Exact serial-frame writes shared by Enhanced transport adapters., Write and flush one complete frame with exact accepted-byte errors., write_serial_frame(), RuntimeError, TransportWriteErrorCode (+21 more)

### Community 18 - "BackendInfo"
Cohesion: 0.18
Nodes (6): Return immutable Basic backend identity and capabilities., Return Basic identity without a DUTchMate hello., BackendInfo, Identity and physical capabilities reported by one selected backend., Return immutable identity and physical capability information., Return normalized identity after a valid hello.

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (63): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+55 more)

### Community 20 - "UartReceiveEvent"
Cohesion: 0.10
Nodes (41): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, Finalize and discard trailing derived state for one connection segment., Convert captured UART byte messages into complete lines and pattern matches., Process one normalized UART receive event., Return an independent candidate state for atomic evidence admission., Return bytes awaiting a line terminator for one segment and channel., Flush one segment/channel's trailing partial line, if any. (+33 more)

### Community 21 - "log_replay.py"
Cohesion: 0.16
Nodes (18): _BoundedNewest, _decode_uart_event(), _non_negative_int(), _normal_record(), _oversized_record(), _T, Bounded replay of persisted native UART evidence., Retain the newest coordinate-ordered records with bounded memory. (+10 more)

### Community 22 - "continuous_ingestion.py"
Cohesion: 0.12
Nodes (11): _close_source(), _project_event_health(), BackendEvent, Exception, Service-owned continuous draining for finite capture workflows., Return the next active-workflow event or an inactivity timeout., Detach and close the consumed disconnected source., Transfer one validated replacement into the stable coordinator. (+3 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (37): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+29 more)

### Community 24 - "SerialPortCandidate"
Cohesion: 0.09
Nodes (38): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+30 more)

### Community 25 - "models.py"
Cohesion: 0.08
Nodes (40): Return recent UART evidence without requiring a backend connection., _compare_lines(), _compare_pattern_counts(), compare_session(), _decode_line(), _evidence_summary(), _line_excerpt(), _logs() (+32 more)

### Community 26 - "SessionStore"
Cohesion: 0.10
Nodes (30): SessionDetail, Create filesystem-backed debug sessions., Return the outcome of the most recent retention pass., Load a session's metadata JSON., Load and summarize one session's metadata., Return stored session summaries in newest-first order., Return the newest stored session summary, if one exists., Return bounded schema-aware detail for one stored session. (+22 more)

### Community 27 - "DeviceActionResult"
Cohesion: 0.06
Nodes (19): Protocol, SessionDetail, Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Compare one terminal session with the designated baseline., Runtime surface needed by the current service API. (+11 more)

### Community 28 - "SessionPersistenceError"
Cohesion: 0.13
Nodes (38): Raised when durable session evidence cannot be read or written., Filesystem paths for the required Phase 1 session files., SessionPaths, SessionPersistenceError, _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups() (+30 more)

### Community 29 - "SessionListPage"
Cohesion: 0.11
Nodes (15): Return one bounded newest-first session page., Path, SessionDetail, SessionRuntime, test_default_service_composition_queries_sessions_while_disconnected(), test_get_session_endpoint_serializes_bounded_native_detail(), test_list_sessions_endpoint_serializes_discriminated_page(), test_recent_logs_endpoint_replays_native_uart_and_validates_limit() (+7 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.16
Nodes (14): BackendEventSource, Asynchronous FIFO source of normalized events from one backend connection., Return the session-local segment ID assigned to this source., _basic_source(), _enhanced_source(), FakeBackendEventSource, BackendEvent, Exception (+6 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.06
Nodes (39): _open_host_on_owner_loop(), _OpenedHost, Synchronous service facade for one owner-loop Enhanced async adapter., AsyncEnhancedDeviceControl, AsyncEnhancedUartSender, EnhancedNdjsonEventStream, ControlState, Translate complete UART payloads through an async Enhanced transport. (+31 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (19): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive., Fails if hello classification or startup cleanup is bypassed. (+11 more)

### Community 33 - "command_executor_harness.c"
Cohesion: 0.07
Nodes (83): dmh_command_executor_cancel_epoch(), dmh_command_executor_init(), dmh_command_executor_poll(), dmh_command_executor_reject(), dmh_command_executor_response(), dmh_command_executor_response_sent(), dmh_command_executor_submit(), map_control_result() (+75 more)

### Community 34 - "store.py"
Cohesion: 0.09
Nodes (33): test_capture_summary_serializes_bounded_first_error_evidence(), buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error() (+25 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "SegmentContext"
Cohesion: 0.09
Nodes (11): EnhancedReconnectHost, OpenEnhancedHost, Protocol, Ready async Enhanced host used as source, control, and UART sender., Open one async Enhanced reconnect host., BackendEvent, BaseException, Return host-monotonic provenance established at source creation. (+3 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.08
Nodes (40): GpioControlChannelState, GpioModeRegistry, GpioModeRejection, GpioControlChannel, GpioModeRequestSource, GpioRoleName, Return current states for all physical control channels., Return the configured channel state for a role, if one exists. (+32 more)

### Community 38 - "DeviceCoreRuntime"
Cohesion: 0.08
Nodes (23): apply_capability_policy(), BackendCapability, Filter backend support through the shared host capability policy., Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, BackendCapability, GpioRoleName (+15 more)

### Community 39 - "test_enhanced_async.py"
Cohesion: 0.18
Nodes (25): open_enhanced_async_host(), Open one ready Enhanced adapter on its permanent owner loop., FakeAsyncEnhancedAdapter, _info(), OpenAdapterFake, BackendEvent, BaseException, DeviceMessage (+17 more)

### Community 40 - "UartIntegrity"
Cohesion: 0.18
Nodes (22): Return one immutable health snapshot for the installed source., What the selected backend can report about upstream UART loss., UartIntegrity, CaptureSourceHealth, Immutable current-source connection, integrity, and replacement projection., Return one immutable current-source health snapshot., monitored_runtime(), MutableHealthSource (+14 more)

### Community 41 - "parser.py"
Cohesion: 0.16
Nodes (31): InvalidUtf8Error, MalformedMessageError, ProtocolValidationError, ProtocolVersionError, Typed failures at Enhanced wire-protocol boundaries., Raised when a UTF-8 protocol frame is not valid JSON., Raised when a bounded frame body is not valid UTF-8., Raised when a JSON object does not match the v1 protocol contract. (+23 more)

### Community 42 - "session_store/baseline.py"
Cohesion: 0.13
Nodes (30): BaselineOperation, clear_baseline(), _ineligibility_reason(), mark_baseline(), _persistence_fault(), datetime, Path, SessionDetail (+22 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.11
Nodes (26): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+18 more)

### Community 44 - "test_enhanced_serial.py"
Cohesion: 0.04
Nodes (112): _compact_json_frame_of_size(), FakeAsyncFrameWriter, FakeAsyncSerialReader, make_adapter(), Event, Exception, parametrize, Async Enhanced serial reader lifecycle tests. (+104 more)

### Community 45 - "command_decode.c"
Cohesion: 0.09
Nodes (54): append_string_byte(), base64_value(), decode_base64(), decode_channel(), decode_configure(), decode_level(), decode_pulse(), decode_state() (+46 more)

### Community 46 - "BackendInputError"
Cohesion: 0.08
Nodes (27): BackendInputKind, BackendInputError, BackendMode, Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context., enhanced_segment_context(), _relative_timestamp(), AsyncEnhancedSerialAdapter (+19 more)

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
Cohesion: 0.33
Nodes (11): _enhanced_integrity(), _enhanced_segment(), _enhanced_timestamp(), _tx_policy(), _append_line(), _capture(), Path, _store() (+3 more)

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
Cohesion: 0.06
Nodes (22): BaselineRuntime, SessionDetail, DeviceCoreSessionStorage, Protocol, SessionDetail, Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record. (+14 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.22
Nodes (28): RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FailingAttemptStore, FailingResultStore, FakeSender, _fixed_time(), _hardware_events() (+20 more)

### Community 57 - "SessionHandle"
Cohesion: 0.04
Nodes (39): Reference to a created debug session., SessionHandle, Durably append a forced-send attempt and reserve its result record., Durably resolve one admitted forced-send attempt., Append one buffer overflow event to a session., Append one buffer status telemetry event to a session., Close the current segment and durably admit one disconnect unit., Append one validated reconnect segment and its discontinuity evidence. (+31 more)

### Community 58 - "FakeMonotonicClock"
Cohesion: 0.13
Nodes (12): FakeCaptureEventSource, FakeMonotonicClock, LifecycleCaptureEventSource, BackendEvent, MonkeyPatch, parametrize, test_capture_activates_cursor_after_session_creation_before_callbacks(), test_capture_does_not_activate_cursor_when_session_creation_fails() (+4 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.07
Nodes (75): _native_detail(), _native_item(), _existing_paths(), _latest_terminal_native(), Path, Select one native session and replay its newest bounded UART lines., replay_recent_logs(), _require_native_schema() (+67 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.14
Nodes (34): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), FakeEnhancedAsyncHost, _hello() (+26 more)

### Community 63 - "persistence.py"
Cohesion: 0.11
Nodes (42): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+34 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.10
Nodes (19): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+11 more)

### Community 66 - "BasicBackendEventSource"
Cohesion: 0.05
Nodes (38): build_basic_capture_reconnect(), OpenBasicConnection, Build coordinated idle and active reopen for one selected Basic backend., Open one raw Basic connection from resolved settings., Return an opened Basic connection., _basic_settings(), FakeBasicSerial, test_basic_active_candidate_uses_coordinator_and_replaces_sender() (+30 more)

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "create_server"
Cohesion: 0.19
Nodes (12): main(), MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server., create_server(), Stateless MCP server composition for the stdio delivery adapter., Create one stateless MCP server with fixed protocol-facing metadata., Run the server over stdio; no other MCP transport is exposed., run_stdio() (+4 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.11
Nodes (26): DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., _control_success_timestamp(), CommandSuccessMessage, Successful command response from the Debug Helper., DeviceActionRunner, _format_utc(), datetime (+18 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "contracts.py"
Cohesion: 0.08
Nodes (29): DeviceControl, ControlState, Backend-neutral identity, timing, event, and receive-source contracts., Backend-neutral semantic DUT and GPIO control operations., Configure one physical control channel and return device time., Pulse one configured physical channel and return device time., Apply one configured channel's active or idle state and return device time., GpioConfigurator (+21 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.28
Nodes (17): CommandedBootMode, SessionWorkflow, Create a new session directory and initialize required files., Create one session while the store-wide lock is held., _create_capture(), datetime, MonkeyPatch, Path (+9 more)

### Community 73 - "EnhancedAsyncHost"
Cohesion: 0.13
Nodes (6): EnhancedAsyncHost, ControlState, T, Return the owner-loop thread identity for lifecycle diagnostics., Terminalize the adapter once, then stop and join its owner loop., Own one asyncio loop and expose its Enhanced adapter synchronously.

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 75 - "platform_io.c"
Cohesion: 0.12
Nodes (7): main(), dutchmate_platform_io_force_safe(), dutchmate_platform_io_initialize_safe(), record_first_error(), set_all_inactive(), dutchmate_uart_rx_initialize(), dutchmate_uart_tx_initialize()

### Community 76 - "CaptureRecorder"
Cohesion: 0.09
Nodes (15): CaptureRecorder, _normalized_control_timestamp(), BackendEvent, Route normalized backend events into UART processing and session storage., Session identifier this recorder writes to., Whether storage has already ended this recorder's native session., Observe terminalization performed by a coordinated external evidence writer., Record one normalized backend event into the session. (+7 more)

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
Cohesion: 0.07
Nodes (49): Apply startup hardware control mappings., load_startup_hardware_config(), GpioRoleName, Path, Apply configured hardware control mappings., Load startup hardware configuration, treating a missing file as empty config., GpioConfigError, HardwareControlMapping (+41 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.16
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "dutchmate_usb_connection_run"
Cohesion: 0.13
Nodes (13): dutchmate_command_runtime_end_epoch(), dmh_connection_epoch_init(), dmh_connection_epoch_update(), dmh_hello_encode(), is_safe_firmware_byte(), dmh_telemetry_schedule_stop(), drain_one_evidence(), drain_one_output() (+5 more)

### Community 84 - "CaptureWorkflow"
Cohesion: 0.14
Nodes (8): CaptureRecordResult, CaptureWorkflow, CommandedBootMode, Exception, SessionWorkflow, Create one capture session., Result of recording one normalized event into a capture session., Own the complete lifecycle of one finite capture session.

### Community 85 - "Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (12): Event Channel Translation, Fixed-Direction Signal Paths, Revision A Raspberry Pi Pico Pin Mapping, Revision A Prototype Validation Checklist, Revision A Provisional BOM, Revision A Voltage-Domain GPIO and UART Interface, Selected Translator Architecture, SN74LV4T125 Datasheet (+4 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): _build_harness(), CompletedProcess, Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

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
Cohesion: 0.11
Nodes (12): BlockingCloseSource, BlockingFailingCloseSource, EventReleasedByCloseSource, FailingCloseSource, BackendEvent, BaseException, test_close_while_workflow_active_is_safe_for_finally_cleanup(), test_concurrent_close_calls_share_exact_cleanup_error_and_close_once() (+4 more)

### Community 99 - "uart_tx_state_harness.c"
Cohesion: 0.29
Nodes (18): dmh_uart_tx_cancel(), dmh_uart_tx_driver_fault(), dmh_uart_tx_init(), dmh_uart_tx_on_interrupt(), dmh_uart_tx_poll(), dmh_uart_tx_start(), finish(), executor_uart_poll() (+10 more)

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.14
Nodes (9): _basic_segment(), ConditionBackedBasicSource, _publish_after_barrier(), BackendEvent, BaseException, Exception, test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator (+1 more)

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "startup.py"
Cohesion: 0.13
Nodes (29): backend_snapshot(), _build_async_enhanced_capture_reconnect(), build_enhanced_capture_reconnect(), ControlState, Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., Keep the runtime UART-send port stable across backend replacement., Publish a newly connected UART-send adapter. (+21 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 106 - "BackendSnapshot"
Cohesion: 0.06
Nodes (21): Stable capture facade that exclusively owns concrete backend sources., Wait for an idle disconnected source that can be claimed., Detach and close the consumed source before reconnect opening., Accept ownership of one validated concrete replacement., Terminalize the stable facade and its current concrete source., ReplaceableCaptureSource, Return the complete Basic identity/policy/provenance snapshot., BackendSnapshot (+13 more)

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

### Community 111 - "backends/__init__.py"
Cohesion: 0.16
Nodes (24): BackendCapabilityPolicy, Host policy snapshot applied to backend-reported capabilities., Immutable timestamp provenance for one continuous connection segment., Software policy controlling whether backend UART transmission is usable., SegmentTimestamp, UartSendCapabilityPolicy, Stable facade for normalized Device Core backend contracts., BackendEvent (+16 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.50
Nodes (4): dutchmate-cli, dutchmate-core, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.06
Nodes (33): DeviceCoreClient, DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), BaseException, NoReturn (+25 more)

### Community 114 - "FakeDeviceControl"
Cohesion: 0.36
Nodes (3): FakeDeviceControl, ControlState, DeviceMessage

### Community 115 - "test_device_core_lifecycle.py"
Cohesion: 0.11
Nodes (26): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+18 more)

### Community 126 - "SerialFrameSink"
Cohesion: 0.17
Nodes (10): _ThreadedSerialFrameWriter, Protocol, Pyserial-compatible surface for exact host frame writes., Return the number of bytes accepted from data., Wait until accepted output is flushed., SerialFrameSink, Fails if command writes use the event loop or skip partial-write recovery., Fails if a worker-thread write loses exact accepted-byte accounting. (+2 more)

### Community 127 - "fixed_clock"
Cohesion: 0.35
Nodes (15): Create a capture session and return a recorder for it., fixed_clock(), fixed_id(), datetime, Path, read_jsonl(), Path, test_finalize_persists_unterminated_oversized_line_descriptor() (+7 more)

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "BackendDisconnectedError"
Cohesion: 0.22
Nodes (10): backend_snapshot(), Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open., segment(), test_failed_idle_replacement_publication_closes_candidate(), test_idle_replacement_commits_snapshot_and_next_connection_generation(), test_replacement_segment_failure_closes_candidate_without_publishing() (+2 more)

### Community 130 - "uart_rx.c"
Cohesion: 0.13
Nodes (16): command_uart_cancel(), command_uart_poll(), command_uart_start(), dutchmate_platform_uart_interface_set(), dut_uart_callback(), dutchmate_uart_rx_faulted(), dutchmate_uart_rx_start(), dutchmate_uart_rx_stop() (+8 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "_StreamWriter"
Cohesion: 0.15
Nodes (9): Protocol, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Open one pyserial-asyncio stream pair., _StreamReader, _StreamTransport (+1 more)

### Community 134 - "device_actions.py"
Cohesion: 0.14
Nodes (15): Wait for one literal in new UART evidence., _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error(), test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(), test_wait_pattern_endpoint_returns_structured_capability_error(), test_wait_pattern_endpoint_serializes_authoritative_match_reference(), test_wait_pattern_timeout_is_successful_with_null_match_fields() (+7 more)

### Community 135 - "_AsyncEnhancedAdapter"
Cohesion: 0.11
Nodes (9): _AsyncEnhancedAdapter, OpenAsyncEnhancedAdapter, Any, BackendEvent, DeviceMessage, Future, Protocol, The one async resource the service host owns on its loop. (+1 more)

### Community 136 - "DeviceCoreStatus"
Cohesion: 0.13
Nodes (14): Return the current Device Core status., apply_startup_hardware_config(), Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply startup GPIO mappings if a Debug Helper is already connected., StartupConfigRuntime, disconnected_status() (+6 more)

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
Nodes (19): append_bytes(), append_decimal(), append_literal(), dmh_buffer_overflow_encode(), dmh_buffer_status_encode(), dmh_telemetry_pending_status(), dmh_telemetry_schedule_init(), dmh_telemetry_schedule_stage_status() (+11 more)

### Community 141 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 143 - "test_capture_workflows.py"
Cohesion: 0.22
Nodes (18): EnhancedCaptureFixtureRecorder, Record a finite Enhanced fixture stream and return its summary., Compose Enhanced fixture parsing with the shared capture recorder., run_enhanced_capture_fixture(), _failing_session_callback(), _native_snapshot(), Path, _start_action() (+10 more)

### Community 144 - "command_runtime.c"
Cohesion: 0.22
Nodes (16): atomic_val_t, cdc_rx_thread(), command_thread(), dutchmate_command_runtime_discard_input(), dutchmate_command_runtime_faulted(), dutchmate_command_runtime_response_sent(), dutchmate_command_runtime_start_epoch(), dutchmate_command_runtime_take_response() (+8 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "SessionRecoveryResult"
Cohesion: 0.14
Nodes (10): Sessions abandoned at startup plus non-fatal compatibility diagnostics., One non-fatal startup-recovery observation for a stored session., SessionRecoveryDiagnostic, SessionRecoveryResult, datetime, Path, Directory containing all sessions., Most recent startup-recovery result for this store instance. (+2 more)

### Community 147 - "runtime.py"
Cohesion: 0.10
Nodes (18): integrity_for_backend(), Protocol, Return the initial UART-loss observation state for a backend mode., Backend-neutral port for complete UART payload transmission., Submit every payload byte or raise a backend write error., UartSender, BackendMode, datetime (+10 more)

### Community 148 - "BlockingCloseStreamWriter"
Cohesion: 0.33
Nodes (3): BlockingCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 149 - "test_recovery.py"
Cohesion: 0.38
Nodes (13): _clock(), _create_active_native(), datetime, MonkeyPatch, parametrize, Path, _recovery_clock(), test_recovery_abandons_stale_active_native_session() (+5 more)

### Community 150 - "enhanced_serial_io.py"
Cohesion: 0.29
Nodes (8): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, _OwnedStreamReader, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener()

### Community 151 - "TerminationBarrierAdapter"
Cohesion: 0.15
Nodes (7): BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, Pause cleanup after request code has selected its terminal outcome., Fails if cancellation turns resource-close start into false completion., TerminationBarrierAdapter, test_resource_close_completion_is_shared_across_reader_cancellation_and_close()

### Community 152 - "_run"
Cohesion: 0.32
Nodes (11): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), test_uart_event_accepts_bounded_staging_maximum(), test_uart_event_encodes_binary_and_base64_padding() (+3 more)

### Community 153 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 154 - "BackendUartSendResult"
Cohesion: 0.09
Nodes (19): Write a complete UART payload, retrying ordered short writes., BackendCapabilityError, BackendUartSendResult, BackendWriteError, RuntimeError, Raised when an operation is disabled or unsupported by the backend., Raised when a backend cannot accept a complete UART payload., Complete backend acceptance of one UART payload. (+11 more)

### Community 156 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, response_harness(), _run(), test_error_response_preserves_utf8_and_escapes_json() (+2 more)

### Community 157 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): File Responsibility Map, Global Constraints, Service-Owned Continuous Ingestion Implementation Plan, Startup Composition, Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle, Task 2: Implement Idle Drain And Active Lossless FIFO, Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close, Task 4: Reconnect And Compose Through The Stable Coordinator (+1 more)

### Community 158 - "test_host_command_encoder.py"
Cohesion: 0.06
Nodes (54): configure_gpio_mode_command(), ConfigureGpioModeCommand, _encode_payload(), pulse_control_command(), PulseControlCommand, Host-to-device protocol command encoding., Send raw bytes to the DUT UART RX line., Build a validated `configure_gpio_mode` command. (+46 more)

### Community 159 - "_run"
Cohesion: 0.31
Nodes (10): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), telemetry_harness(), test_buffer_overflow_matches_canonical_v1_frame() (+2 more)

### Community 160 - "RP2350 Debug Helper Firmware Design"
Cohesion: 0.20
Nodes (9): Authority And Scope, Component Boundaries, Concurrency And Interrupt Ownership, Existing Contract Alignment, Failure Semantics, RP2350 Debug Helper Firmware Design, Safe-State Lifecycle, Test Boundary And Milestone Evidence (+1 more)

### Community 161 - ".feed"
Cohesion: 0.40
Nodes (4): _frame_body(), DeviceMessage, Consume a serial byte chunk and return parsed complete messages., Return one exact JSON object body after removing one optional CR.

### Community 162 - "SessionMutationLock"
Cohesion: 0.22
Nodes (6): BaseException, TracebackType, Shared guard that serializes active-session evidence mutations., Acquire the mutation guard., Release the mutation guard., SessionMutationLock

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

### Community 189 - "backend_reconnect.py"
Cohesion: 0.20
Nodes (9): _CandidateCleanupFailure, _close_unpublished_candidate(), BaseException, Exception, Service-owned backend reopen and replaceable-control composition., Keep a rejected candidate's primary failure distinct from close failure., _require_matching_basic_snapshot(), _require_matching_enhanced_identity() (+1 more)

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

### Community 200 - "test_backend_sources_preserve_fifo_uart_events"
Cohesion: 0.67
Nodes (4): SourceFactory, parametrize, test_backend_sources_preserve_fifo_uart_events(), test_backend_sources_raise_disconnect_distinctly()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **327 isolated node(s):** `dutchmate-cli`, `dutchmate-mcp-server`, `dutchmate-service`, `$schema`, `$id` (+322 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `Reconnect and Session Semantics` (4× useful, score=3.430112837)
- `DeviceCoreRuntime` (4× useful, score=3.385955111)
- `BackendEventSource` (4× useful, score=3.334557655)
- `Continuous Ingestion and Async Enhanced Adapter` (3× useful, score=2.538626434) _(code changed — re-verify)_
- `CaptureWorkflow` (3× useful, score=2.499998237)
- `NdjsonStreamParser` (3× useful, score=2.43907719)
- `Phase 1 Implementation Spec` (2× useful, score=1.725415664)
- `Firmware RAM Report` (2× useful, score=1.725415664)
- `build_startup_runtime()` (2× useful, score=1.701220361)
- `AsyncEnhancedSerialAdapter` (2× useful, score=1.667627559)

**Known dead ends** — questions that led nowhere; don't re-derive.
- "What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?" -> `NdjsonStreamParser`, `AsyncEnhancedSerialAdapter`

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `fixed_clock`, `FakeDeviceControl`, `test_log_replay.py`, `test_capture_workflows.py`, `SessionRecoveryResult`, `UartReceiveEvent`, `test_recovery.py`, `models.py`, `SessionPersistenceError`, `SessionListPage`, `store.py`, `test_basic.py`, `SegmentContext`, `UartIntegrity`, `session_store/baseline.py`, `helpers.py`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionHandle`, `FakeMonotonicClock`, `retrieval.py`, `test_startup_config.py`, `persistence.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_retention.py`, `test_reconnect_evidence.py`, `test_connection_monitoring.py`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `BackendSnapshot`, `backends/__init__.py`, `test_device_core_lifecycle.py`, `fixed_clock`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `DeviceCoreRuntime` connect `DeviceCoreRuntime` to `test_backend_reconnect.py`, `workflows/capture.py`, `device_actions.py`, `FakeDeviceControl`, `modes.py`, `validation.py`, `BackendInfo`, `runtime.py`, `UartReceiveEvent`, `models.py`, `BackendUartSendResult`, `DeviceActionResult`, `SessionListPage`, `SegmentContext`, `GpioModeRegistry`, `UartIntegrity`, `session_store/baseline.py`, `BackendInputError`, `test_app_lifecycle.py`, `BaselineMutationResult`, `test_device_core_uart_send.py`, `SessionHandle`, `retrieval.py`, `test_startup_config.py`, `CommandSuccessMessage`, `contracts.py`, `CaptureWorkflow`, `test_connection_monitoring.py`, `BackendSnapshot`, `backends/__init__.py`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `test_backend_reconnect.py`, `BackendDisconnectedError`, `workflows/capture.py`, `_AsyncEnhancedAdapter`, `DeviceCoreStatus`, `fixed_clock`, `FakeDeviceControl`, `enhanced.py`, `metadata.py`, `test_capture_workflows.py`, `runtime.py`, `continuous_ingestion.py`, `models.py`, `SessionStore`, `BackendUartSendResult`, `test_contracts.py`, `test_enhanced.py`, `store.py`, `SessionMutationLock`, `DeviceCoreRuntime`, `test_enhanced_async.py`, `UartIntegrity`, `BackendInputError`, `helpers.py`, `SessionHandle`, `FakeMonotonicClock`, `retrieval.py`, `test_startup_config.py`, `BasicBackendEventSource`, `test_capture_reconnect.py`, `contracts.py`, `EnhancedAsyncHost`, `CaptureRecorder`, `test_reconnect_evidence.py`, `CaptureWorkflow`, `test_connection_monitoring.py`, `test_comparison.py`, `BlockingCloseSource`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `startup.py`, `BackendSnapshot`, `backends/__init__.py`, `test_device_core_lifecycle.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 182 inferred relationships involving `SessionStore` (e.g. with `build_startup_runtime()` and `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()`) actually correct?**
  _`SessionStore` has 182 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 91 INFERRED edges - model-reasoned connections that need verification._