# Graph Report - DUTchMate  (2026-09-23)

## Corpus Check
- 390 files · ~298,763 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5402 nodes · 13921 edges · 280 communities (260 shown, 20 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 2430 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `34492103`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_backend_reconnect.py
- format_status
- parse_cli_config
- client.py
- dutchmate_cli/main.py
- test_continuous_ingestion.py
- UartLine
- main
- settings.py
- FakeAsyncFrameWriter
- FakeDeviceControl
- app.py
- enhanced.py
- metadata.py
- WaitPatternResult
- CaptureEventSource
- test_validation.py
- transport.py
- cdc_tx_state_harness.c
- parse_device_message
- DeviceCoreRuntime
- log_replay.py
- properties
- service_error_from_exception
- test_devices.py
- comparison.py
- Phase 1B Revision A Prototype Validation Record
- RuntimeProvider
- transactions.py
- parse_hardware_gpio_config
- create_app
- test_enhanced.py
- test_enhanced_serial_io.py
- command_executor_harness.c
- evidence.py
- test_basic.py
- fixed_clock
- GpioModeRegistry
- runtime.py
- EnhancedAsyncHost
- workflows/capture.py
- parser.py
- store.py
- dutchmate_cli/__init__.py
- CI, Packaging, Release, Firmware, and Plugin Distribution Plan
- command_decode.c
- BackendInputError
- uart_rx_ring.c
- Service-Owned Continuous Ingestion Design
- format_uart_send
- errors.schema.json
- gpio_config/config.py
- test_app_lifecycle.py
- logs.py
- Continuous Connection And Integrity Monitoring Design
- validation.py
- test_device_core_uart_send.py
- SessionStore
- test_report_boundary.py
- Incremental Re-Extraction
- sessions.py
- retrieval.py
- test_startup_config.py
- persistence.py
- Phase 1 Implementation Spec
- enum
- BasicSerialPort
- Enhanced Asynchronous Serial Adapter Design
- dutchmate_mcp_server/main.py
- CommandSuccessMessage
- test_capture_reconnect.py
- ContinuousIngestionCoordinator
- test_baseline.py
- _StreamWriter
- test_retention.py
- CaptureRecorder
- Ring Buffer Sizing Plan
- DUTchMate Project Context
- test_reconnect_evidence.py
- smoke_installed_distribution.py
- SessionListPage
- fixture_protocol.c
- dutchmate_usb_connection_run
- evidence_package.py
- test_device_core_lifecycle.py
- test_fixture_protocol.py
- OllamaAdapter
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
- provider_boundary.py
- FakeAsyncSerialReader
- test_real_coordinator_discards_idle_basic_event_before_capture
- AsyncSerialReader
- Coordinated Background Reconnect Design
- backend_reconnect.py
- Software Architecture
- report_schema.py
- BasicBackendEventSource
- _validator
- Phase 1A Basic Hardware-in-the-Loop Validation
- test_device_message_schema.py
- host_to_device.schema.json
- DtrControlledSerial
- dutchmate-core
- DeviceCoreClient
- FakeDeviceControl
- TerminationBarrierAdapter
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
- dutchmate_cli/config.py
- Enhanced Async Service Integration Design
- resolve_backend_settings
- time_us_64
- File Responsibility Map
- File Responsibility Map
- BlockingCloseStreamWriter
- test_protocol_integration.py
- format_wait_pattern
- validate_coding_context
- File Map
- File Responsibility Map
- test_log_replay.py
- telemetry.c
- make_adapter
- test_gpio.py
- test_evidence_package.py
- command_runtime.c
- File Responsibility Map
- main
- DUTchMate Revision A Voltage-Domain GPIO and UART Interface
- mcp.schema.json
- test_recovery.py
- url
- BlockingCloseSource
- _run
- test_enhanced_serial.py
- SessionHandle
- BackendDisconnectedError
- _run
- File Responsibility Map
- test_host_command_encoder.py
- _run
- RP2350 Debug Helper Firmware Design
- properties
- apply_startup_hardware_config
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
- _UnavailableDeviceControl
- connection_epoch.c
- _run_hello
- discovery.py
- _BoundedNewest
- ReplaceableCaptureSource
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
- test_aggregator_entrypoint.py
- verify_index_artifacts.py
- GpioIdentifierValidationError
- dmh_output_drain_batch
- server.py
- DUTchMate Licensing
- service_client.py
- Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?
- test_cdc_tx_state_machine
- create_server
- streamableHttpServer
- test_release_validation.py
- properties
- collect_stack_probe.py
- test_dut.py
- $defs
- dmh_hello_encode
- McpLogLevel
- Q: Which RP2350 firmware boundaries need hardware-independent automated coverage and reproducible build instructions?
- Q: what is next
- Q: ok we can do this, tell me what to do
- Q: I have the schematic and layout file for Eagle CAD, where you want me to add. I have the fully assembled board with me that I use it with Pico 2.
- Q: Review the supplied Eagle schematic only against Revision A Pico 2/RP2350A requirements and safe-state contracts
- Q: ok lets move to next step than
- Q: Trace Enhanced RP2350 UART receive events from async serial parsing through continuous ingestion to active session persistence, especially per-event processing, locking, flushing, and filesystem writes that could limit throughput
- test_output_drain_batch_policy
- test_uart_rx_adapter_error_policy
- test_agent_plugin.py
- _decimal_define
- BasicBackendConnection
- test_debug_cli.py
- SegmentContext
- 4. Four debugger-to-DUT control outputs
- 5. Four DUT-to-debugger event inputs
- ScriptedBasicSerial
- enhanced_serial_io.py
- env
- test_service_client.py
- test_distribution_metadata.py
- stdioServer
- run_load_profile.py
- headers
- Phase 1B Enhanced Workflow HIL Evidence
- test_workflows.py
- DeviceCoreSessionStorage
- test_device_message_examples.py
- Q: What are the things remaining from development side
- Q: Review DUTchMate CI Packaging Plugin Implementation Plan and integrate it into the development plan
- Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step
- Q: Revise CI packaging release firmware versioning and plugin distribution plan
- Q: Assess direct Debug Agent Python API launch and console-script ownership migration requirements
- plugin.json
- UartReceiveEvent
- write_firmware_provenance.py
- test_firmware_provenance.py
- dutchmate
- investigate-debug-session/SKILL.md
- operate-dutchmate/SKILL.md
- validate_release_tag
- .__init__
- .__init__
- pull_request_template.md
- 12. Design decisions and rationale
- 7. Power and sequencing
- default_cli_config
- HardwareGpioConfig
- 11. Suggested firmware model
- 2. System requirements
- 6. UART interface
- 10. Debugger MCU resource estimate
- rev-a/README.md
- backend_snapshot
- FakeEnhancedAsyncHost
- test_reader_failure_is_repeatable_disconnect
- _request_after_entering
- .close
- test_transactions.py
- .feed
- project_diagnostic_detail
- test_start_timeout_closes_the_reader_and_normalizes_the_failure

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 277 edges
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
- `Ring Buffer Validation Gate` --semantically_similar_to--> `Ring Buffer Acceptance Checklist`  [INFERRED] [semantically similar]
  docs/ring_buffer_sizing_plan.md → hardware/validation/phase1_ring_buffer.md
- `_summary_from_metadata()` --calls--> `_first_error()`  [INFERRED]
  core/src/dutchmate_core/session_store/metadata.py → apps/cli/src/dutchmate_cli/capture.py
- `CliConfig` --uses--> `BackendConfig`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py
- `parse_cli_config()` --uses--> `BackendConfigError`  [INFERRED]
  apps/cli/src/dutchmate_cli/config.py → core/src/dutchmate_core/backends/settings.py
- `format_devices()` --uses--> `SerialPortCandidate`  [INFERRED]
  apps/cli/src/dutchmate_cli/devices.py → core/src/dutchmate_core/device_connection/discovery.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DUTchMate Backend Pipeline** — readme_basic_backend, readme_enhanced_backend, readme_shared_host_processing_and_session_pipeline [EXTRACTED 1.00]
- **Graphify Operational Pipeline** — _codex_skills_graphify_skill_extraction_pipeline, _codex_skills_graphify_references_update_incremental_re_extraction, _codex_skills_graphify_skill_graph_health_check [EXTRACTED 1.00]
- **Bounded Evidence Integrity Contract** — docs_debug_agent_context_contract_bounded_hardware_evidence, docs_reconnect_session_semantics_incremental_evidence_writes, docs_software_architecture_session_store, docs_ring_buffer_sizing_plan_buffer_integrity_reporting, docs_mcp_integration_plan_bounded_tool_results [INFERRED 0.85]
- **Backend-Independent Evidence Pipeline** — docs_project_context_normalized_evidence_boundary, docs_phase1_implementation_spec_backend_independent_pipeline, docs_software_architecture_normalized_event_boundary, docs_software_architecture_backends_contracts [INFERRED 0.95]

## Communities (280 total, 20 thin omitted)

### Community 0 - "test_backend_reconnect.py"
Cohesion: 0.10
Nodes (25): BackendReconnectCoordinator, Serialize idle and active reconnect attempts for one stable source owner., Start the single non-daemon idle reconnect worker., Own one bounded active-workflow reconnect attempt., ClosableSource, FakeClock, FakeSourceOwner, _release_stuck_attempt() (+17 more)

### Community 1 - "format_status"
Cohesion: 0.16
Nodes (25): _as_mapping(), _display(), _format_capabilities(), _format_connection(), _format_control_channel(), _format_control_channels(), _format_device(), _format_integrity() (+17 more)

### Community 2 - "parse_cli_config"
Cohesion: 0.18
Nodes (19): CliConfig, load_cli_config(), parse_cli_config(), Path, Merged CLI configuration., Load CLI configuration from TOML, returning defaults when missing., Parse a raw TOML mapping into validated CLI configuration., parametrize (+11 more)

### Community 3 - "client.py"
Cohesion: 0.06
Nodes (67): capture_uart(), clear_session_baseline(), configure_gpio_mode(), fetch_recent_logs(), fetch_status(), get_debug_session(), list_debug_sessions(), mark_session_baseline() (+59 more)

### Community 4 - "dutchmate_cli/main.py"
Cohesion: 0.10
Nodes (58): RuntimeError, Raised when the CLI cannot complete a Device Core Service request., Raised when the local Device Core Service cannot be reached., ServiceClientError, ServiceUnavailableError, boot_test(), capture(), clear_baseline_command() (+50 more)

### Community 5 - "test_continuous_ingestion.py"
Cohesion: 0.17
Nodes (31): buffer_overflow_event(), buffer_status_event(), close_coordinator(), ControlledSource, Catches malformed backend input being retried as an idle disconnect., test_active_fifo_preserves_exact_order(), test_active_telemetry_updates_health_and_enters_fifo_once(), test_active_workflow_continues_after_source_timeout() (+23 more)

### Community 6 - "UartLine"
Cohesion: 0.05
Nodes (53): UartExcerpt, _UartSelector, PatternDetector, PatternMatch, Pattern detection for completed UART log lines., A configured pattern found in one UART log line., Find configured text patterns in completed UART log lines., Configured patterns in scan order. (+45 more)

### Community 7 - "main"
Cohesion: 0.09
Nodes (49): is_process_running(), LifecycleError, Path, Protocol, RuntimeError, Local Device Core Service process lifecycle helpers., Stop the background Device Core Service process recorded in the PID file., Return whether a process ID currently exists. (+41 more)

### Community 8 - "settings.py"
Cohesion: 0.16
Nodes (24): BackendConfigError, _baudrate(), _boolean(), _finite_number(), _fixed_integer(), _fixed_string(), _optional_baudrate(), _optional_table() (+16 more)

### Community 9 - "FakeAsyncFrameWriter"
Cohesion: 0.08
Nodes (23): FakeAsyncFrameWriter, Fails if same-batch response success masks invalid input or drops its prefix., Fails if post-transmission cancellation leaves an orphan response path., Fails if response timeout permits reuse of an uncorrelated command stream., Fails if command routing consumes or reorders interleaved UART evidence., Fails if a response overtakes earlier evidence blocked outside the FIFO., Fails if a second uncorrelated command is written before the first resolves., Fails if async routing replaces write accounting or its repeatable terminal. (+15 more)

### Community 10 - "FakeDeviceControl"
Cohesion: 0.10
Nodes (53): AdvancingMonotonicClock, enhanced_info(), FakeCaptureSource, FakeDeviceControl, FakeMonotonicClock, BackendCapability, BackendEvent, ControlState (+45 more)

### Community 11 - "app.py"
Cohesion: 0.06
Nodes (49): _close_runtime(), FastAPI, FastAPI application factory for the Device Core Service., Service entrypoint for DUTchMate., baseline_mutation_payload(), BootModeRequest, BootTestRequest, CaptureRequest (+41 more)

### Community 12 - "enhanced.py"
Cohesion: 0.07
Nodes (45): enhanced_message_timestamp_us(), enhanced_segment_context(), normalize_enhanced_hello(), normalize_enhanced_message(), BackendEvent, DeviceMessage, Enhanced v1 protocol adapters and normalized event translation., Translate one Enhanced hello message into backend-neutral identity. (+37 more)

### Community 13 - "metadata.py"
Cohesion: 0.09
Nodes (34): _backend_segment_json(), _capability_policy_json(), _format_session_id_timestamp(), _format_utc_timestamp(), _initial_metadata(), _integrity_json(), _line_processing_json(), _metadata_segment() (+26 more)

### Community 14 - "WaitPatternResult"
Cohesion: 0.16
Nodes (15): capture_summary_payload(), Serialize a completed capture session summary., Serialize one successful matched or unmatched wait-pattern outcome., wait_pattern_payload(), test_capture_summary_serializes_quota_truncation_context(), _match(), parametrize, test_wait_pattern_endpoint_preserves_capture_active_error() (+7 more)

### Community 15 - "CaptureEventSource"
Cohesion: 0.08
Nodes (17): Accept ownership of one validated concrete replacement., _close_source(), Exception, Transfer one validated replacement into the stable coordinator., Return the latest timestamp provenance published by the source., _source_segment(), Return timestamp provenance once the source origin is established., Map one live connection source onto a new session-local segment zero. (+9 more)

### Community 16 - "test_validation.py"
Cohesion: 0.13
Nodes (24): prepare_uart_send_payload(), Return a valid Phase 1 wait-pattern timeout in seconds., Validate and preserve one case-sensitive literal wait pattern., Encode one public text command and enforce its final UART payload bound., Return a positive per-session evidence budget in MiB units., Convert a validated per-session MiB setting to exact evidence bytes., session_evidence_budget_bytes(), validate_session_max_size_mb() (+16 more)

### Community 17 - "transport.py"
Cohesion: 0.10
Nodes (29): _classify_serial_write_error(), Exception, TransportWriteErrorCode, Exact serial-frame writes shared by Enhanced transport adapters., Write and flush one complete frame with exact accepted-byte errors., write_serial_frame(), RuntimeError, TransportWriteErrorCode (+21 more)

### Community 18 - "cdc_tx_state_harness.c"
Cohesion: 0.34
Nodes (17): dmh_cdc_tx_cancel(), dmh_cdc_tx_driver_fault(), dmh_cdc_tx_init(), dmh_cdc_tx_on_writable(), dmh_cdc_tx_poll(), dmh_cdc_tx_start(), finish(), expect_result() (+9 more)

### Community 19 - "parse_device_message"
Cohesion: 0.07
Nodes (63): parse_device_message(), DeviceMessage, Parse one NDJSON device-to-host protocol line. This parser currently supports…, _command_error_line(), _hello_line(), parametrize, test_command_error_detail_accepts_and_preserves_exact_utf8_value(), test_command_error_detail_rejects_non_string_value() (+55 more)

### Community 20 - "DeviceCoreRuntime"
Cohesion: 0.06
Nodes (43): Core DUTchMate library., DeviceCoreRuntime, DeviceCoreRuntimeError, DeviceCoreStatus, BackendCapability, GpioModeRequestSource, GpioRoleName, RuntimeError (+35 more)

### Community 21 - "log_replay.py"
Cohesion: 0.12
Nodes (49): _decode_uart_event(), _existing_paths(), _latest_terminal_native(), _non_negative_int(), _normal_record(), _oversized_record(), Path, Bounded replay of persisted native UART evidence. (+41 more)

### Community 22 - "properties"
Cohesion: 0.04
Nodes (46): name, additionalProperties, type, additionalProperties, properties, type, description, type (+38 more)

### Community 23 - "service_error_from_exception"
Cohesion: 0.10
Nodes (36): _baseline_context(), _comparison_context(), _gpio_configuration_context(), _gpio_identifier_service_error(), _json_response(), Exception, FastAPI, HTTP error mapping for the Device Core Service. (+28 more)

### Community 24 - "test_devices.py"
Cohesion: 0.18
Nodes (16): DeviceSelectionError, format_devices(), _format_metadata(), RuntimeError, Terminal formatting for serial device discovery., Raised when the CLI cannot choose one Debug Helper serial port., Format discovered serial ports for CLI output., Resolve the serial port used by `dutchmate start`. (+8 more)

### Community 25 - "comparison.py"
Cohesion: 0.07
Nodes (45): BaselineComparisonSummary, BaselineComparisonUnavailable, load_baseline_context(), _pointer_changed(), Explicit project-baseline context for a bounded Debug Agent evidence package., Bounded comparison facts without repeating UART line text., A valid baseline exists, but the subject cannot be compared yet., Use only the validated project pointer; never pick a baseline by recency. (+37 more)

### Community 26 - "Phase 1B Revision A Prototype Validation Record"
Cohesion: 0.05
Nodes (42): 2026-09-15 Source Mapping And Configured Rejection Audit, Active Enhanced UART Idle Path At 1.8 V, Active-Low Control `/OE` Follow-Up, CDC Command-Ingress Diagnosis And Corrected Image, Control High Impedance During Debugger Reset, Corrected paired-probe TX cycle: receive-pin disturbances captured, Corrected-probe baseline timeout, Correction Of Capture-Timing Interpretations (+34 more)

### Community 27 - "RuntimeProvider"
Cohesion: 0.07
Nodes (17): Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected session., Compare one terminal session with the designated baseline., Apply startup hardware control mappings., Runtime surface needed by the current service API. (+9 more)

### Community 28 - "transactions.py"
Cohesion: 0.13
Nodes (34): _append_offsets(), begin_evidence_transaction(), _cleanup(), _cleanup_orphan_backups(), _digest_bytes(), _digest_file(), _error(), evidence_transaction() (+26 more)

### Community 29 - "parse_hardware_gpio_config"
Cohesion: 0.18
Nodes (21): parse_hardware_gpio_config(), Parse and validate `[hardware.control.*]` configuration., parametrize, test_parse_custom_role_mapping(), test_parse_empty_config_leaves_all_controls_unconfigured(), test_parse_valid_boot_mapping_with_idle_level(), test_parse_valid_hardware_control_mapping(), test_rejects_duplicate_channel_assignments() (+13 more)

### Community 30 - "create_app"
Cohesion: 0.10
Nodes (44): create_app(), Path, Create the Device Core Service application., connected_status(), disconnected_status(), _enhanced_integrity(), FakeRuntime, SessionDetail (+36 more)

### Community 31 - "test_enhanced.py"
Cohesion: 0.06
Nodes (41): DeviceControlError, Raised when a backend rejects or cannot complete a semantic control operation., AsyncEnhancedDeviceControl, AsyncEnhancedUartSender, _control_success_timestamp(), EnhancedNdjsonEventStream, ControlState, Translate complete UART payloads through an async Enhanced transport. (+33 more)

### Community 32 - "test_enhanced_serial_io.py"
Cohesion: 0.16
Nodes (21): FakeStreamReader, FakeStreamWriter, Concrete Enhanced async serial I/O boundary tests., Fails if startup, ownership, or exact command dispatch uses the wrong path., Fails if the Enhanced UART setting reaches the host CDC line coding., Fails if opener errors are replaced or close an unreturned stream., Fails if transport inspection leaks or cleanup replaces its primary error., Fails if adapter validation after open leaves the owned stream alive. (+13 more)

### Community 33 - "command_executor_harness.c"
Cohesion: 0.06
Nodes (98): dmh_command_executor_cancel_epoch(), dmh_command_executor_poll(), dmh_command_executor_reject(), dmh_command_executor_response(), dmh_command_executor_response_sent(), dmh_command_executor_submit(), map_control_result(), response_encoded() (+90 more)

### Community 34 - "evidence.py"
Cohesion: 0.11
Nodes (26): test_capture_summary_serializes_bounded_first_error_evidence(), buffer_overflow_event_json(), buffer_status_event_json(), _bytes_to_b64(), control_action_event_json(), detected_pattern_at(), detected_pattern_records(), first_error() (+18 more)

### Community 35 - "test_basic.py"
Cohesion: 0.14
Nodes (22): BasicSerialFactory, open_basic_backend_connection(), _pyserial_factory(), Open a Basic backend as raw 8-N-1 serial without reading a hello., FakeRawSerial, Exception, parametrize, Path (+14 more)

### Community 36 - "fixed_clock"
Cohesion: 0.14
Nodes (50): BufferOverflowEvent, BufferStatusEvent, Observed Enhanced-backend UART receive-buffer loss., Enhanced-backend UART receive-buffer telemetry., test_enhanced_source_preserves_telemetry_order(), test_normalizes_buffer_telemetry(), enhanced_snapshot(), evidence_bytes() (+42 more)

### Community 37 - "GpioModeRegistry"
Cohesion: 0.07
Nodes (50): _format_utc_timestamp(), GpioControlChannelState, GpioModeRegistry, GpioModeRejection, datetime, GpioControlChannel, GpioModeRequestSource, GpioRoleName (+42 more)

### Community 38 - "runtime.py"
Cohesion: 0.04
Nodes (58): Write a complete UART payload, retrying ordered short writes., Return the complete Basic identity/policy/provenance snapshot., BackendCapabilityError, BackendEventSource, BackendWriteError, DeviceControl, integrity_for_backend(), BackendEvent (+50 more)

### Community 39 - "EnhancedAsyncHost"
Cohesion: 0.05
Nodes (43): _AsyncEnhancedAdapter, EnhancedAsyncHost, open_enhanced_async_host(), _open_host_on_owner_loop(), OpenAsyncEnhancedAdapter, _OpenedHost, Any, BackendEvent (+35 more)

### Community 40 - "workflows/capture.py"
Cohesion: 0.15
Nodes (23): _project_event_health(), Service-owned continuous draining for finite capture workflows., CaptureSourceHealth, _normalized_control_timestamp(), Backend-independent capture workflow coordination., Immutable current-source connection, integrity, and replacement projection., Persist one successful boot-test reset within its active segment., Return one immutable current-source health snapshot. (+15 more)

### Community 41 - "parser.py"
Cohesion: 0.13
Nodes (35): InvalidUtf8Error, MalformedMessageError, ProtocolError, ProtocolValidationError, ProtocolVersionError, ValueError, Typed failures at Enhanced wire-protocol boundaries., Base class for host-device protocol errors. (+27 more)

### Community 42 - "store.py"
Cohesion: 0.05
Nodes (55): Designate one eligible session as the project baseline., Clear the baseline only when it names the requested session., Register service exception handlers on an app., register_error_handlers(), BaselineOperation, Designate a stored session without requiring a backend connection., Clear a named designation without requiring a backend connection., clear_baseline() (+47 more)

### Community 43 - "dutchmate_cli/__init__.py"
Cohesion: 0.11
Nodes (26): _display(), _first_error(), _flag(), format_boot_test_result(), format_capture_result(), _format_capture_summary(), _line_processing(), _loss_status() (+18 more)

### Community 44 - "CI, Packaging, Release, Firmware, and Plugin Distribution Plan"
Cohesion: 0.10
Nodes (20): Architectural Invariants, CI, Packaging, Release, Firmware, and Plugin Distribution Plan, Clean-Artifact Acceptance, Coding-Agent Plugin, Console-script migration gate, Current distribution graph, Debug Helper firmware, Deferred Debug Agent Distribution (+12 more)

### Community 45 - "command_decode.c"
Cohesion: 0.09
Nodes (54): append_string_byte(), base64_value(), decode_base64(), decode_channel(), decode_configure(), decode_level(), decode_pulse(), decode_state() (+46 more)

### Community 46 - "BackendInputError"
Cohesion: 0.07
Nodes (28): BackendInputKind, BackendInputError, BackendMode, Raised when a backend emits malformed or otherwise invalid input., Return the same classified failure with workflow-owned context., backend_input_error_from_protocol(), Preserve bounded Enhanced protocol classification across the adapter., AsyncEnhancedSerialAdapter (+20 more)

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

### Community 51 - "gpio_config/config.py"
Cohesion: 0.22
Nodes (15): GpioConfigError, HardwareControlMapping, _optional_string(), _optional_voltage(), _parse_control_mapping(), Any, GpioRoleName, ValueError (+7 more)

### Community 52 - "test_app_lifecycle.py"
Cohesion: 0.10
Nodes (18): DUTchMate Device Core Service package., BlockingCaptureSource, ClosableFakeRuntime, _hardware_config(), NoopDeviceControl, BackendEvent, ControlState, Exception (+10 more)

### Community 53 - "logs.py"
Cohesion: 0.24
Nodes (11): _display(), _display_text(), format_recent_logs(), _merged_records(), CLI formatting for bounded recent UART replay., Format replayed lines with CLI-only segment/channel separators., _sort_int(), _warnings() (+3 more)

### Community 54 - "Continuous Connection And Integrity Monitoring Design"
Cohesion: 0.08
Nodes (24): Acceptance Criteria, Architectural Decision, Buffer Overflow, Buffer Status, Concurrency And Ownership Invariants, Context, Continuous Connection And Integrity Monitoring Design, Coordinator State And Event Projection (+16 more)

### Community 55 - "validation.py"
Cohesion: 0.08
Nodes (37): GpioConfigurator, GpioModeRequestSource, GPIO mode configuration workflow., Configure GPIO modes through firmware and update accepted host state., Send `configure_gpio_mode` and record the firmware result., GpioConfigurationError, RuntimeError, Raised when a GPIO-controlled workflow cannot run with current state. (+29 more)

### Community 56 - "test_device_core_uart_send.py"
Cohesion: 0.17
Nodes (29): BackendUartSendResult, Complete backend acceptance of one UART payload., Submit every payload byte or raise a backend write error., RuntimeError, Canonical UART-send failure with optional audit context., UartSendError, FakeSender, _fixed_time() (+21 more)

### Community 57 - "SessionStore"
Cohesion: 0.06
Nodes (39): SessionDetail, Create filesystem-backed debug sessions., Return the outcome of the most recent retention pass., Abandon stale native active sessions without mutating other schemas., Perform startup recovery while the store-wide lock is held., Transition one active native session to completed exactly once., Complete one wait session with an authoritative optional match index., Load one authoritative reference-bearing detected-pattern record. (+31 more)

### Community 58 - "test_report_boundary.py"
Cohesion: 0.29
Nodes (21): ProviderSelection, FixtureAdapter, asyncio, parametrize, Path, _request(), _response(), test_adapter_credential_is_absent_from_manifest_and_payload() (+13 more)

### Community 59 - "Incremental Re-Extraction"
Cohesion: 0.10
Nodes (21): Folder Watcher, URL Ingestion, Extraction Confidence Rubric, Deterministic Node IDs, Semantic Extraction Specification, Cross-Repository Graph Merge, CLAUDE.md Integration, Post-Commit Auto-Rebuild (+13 more)

### Community 60 - "sessions.py"
Cohesion: 0.21
Nodes (18): _as_mapping(), _display(), _format_artifacts(), _format_first_error(), _format_list_item(), format_session_detail(), format_session_list(), _nested_display() (+10 more)

### Community 61 - "retrieval.py"
Cohesion: 0.08
Nodes (47): _native_detail(), _native_item(), EvidenceTypeCount, FirstErrorReference, LegacySessionListItem, NativeSessionListItem, Compact summary of a debug session for workflow/API responses., Compact first-error location used by bounded session list items. (+39 more)

### Community 62 - "test_startup_config.py"
Cohesion: 0.25
Nodes (28): build_startup_runtime(), Build the service runtime for one explicitly selected backend., AdvancingClock, backend_settings(), _enhanced_info(), _enhanced_segment(), MonkeyPatch, Path (+20 more)

### Community 63 - "persistence.py"
Cohesion: 0.13
Nodes (35): append_bytes(), append_serialized(), create_directory(), _error(), evidence_file_bytes(), _fsync_directory(), OSError, Path (+27 more)

### Community 64 - "Phase 1 Implementation Spec"
Cohesion: 0.12
Nodes (18): Atomic Protocol Change Workflow, Developer Guide, Package Boundaries, uv Workspace, Repository Validation Workflow, Continuous Ingestion and Async Enhanced Adapter, Development Status, Enhanced Protocol Migration (+10 more)

### Community 65 - "enum"
Cohesion: 0.10
Nodes (19): enum, type, $defs, capability, timestamp_us, $id, oneOf, $schema (+11 more)

### Community 66 - "BasicSerialPort"
Cohesion: 0.18
Nodes (7): BasicSerialPort, Protocol, Small raw pyserial surface owned by the Basic backend., Read up to ``size`` raw UART bytes., Write raw UART bytes., Close the serial port., Return the owned raw serial port for the receive adapter.

### Community 67 - "Enhanced Asynchronous Serial Adapter Design"
Cohesion: 0.11
Nodes (17): Acceptance Criteria, Architectural Decision, Big-Bang Async Migration, Command Serialization And Writes, Enhanced Asynchronous Serial Adapter Design, Event Queue And Backpressure, Failure And Cancellation Semantics, First Implementation Slice (+9 more)

### Community 68 - "dutchmate_mcp_server/main.py"
Cohesion: 0.23
Nodes (10): main(), _parser(), ArgumentParser, MCP server entrypoint for DUTchMate., Start the DUTchMate MCP server over stdio., CaptureFixture, MonkeyPatch, test_main_explicit_service_url_overrides_environment() (+2 more)

### Community 69 - "CommandSuccessMessage"
Cohesion: 0.10
Nodes (29): BootMode, CommandSuccessMessage, Successful command response from the Debug Helper., Return a valid DUT reset pulse duration in milliseconds., Return a supported DUT boot mode., validate_boot_mode(), validate_reset_pulse(), DeviceActionRunner (+21 more)

### Community 70 - "test_capture_reconnect.py"
Cohesion: 0.21
Nodes (19): _evidence_bytes(), FakeMonotonicClock, BackendEvent, Exception, Path, _read_jsonl(), _required_segment(), _run_one_reconnect() (+11 more)

### Community 71 - "ContinuousIngestionCoordinator"
Cohesion: 0.09
Nodes (20): ContinuousIngestionCoordinator, BackendEvent, Return one immutable health snapshot for the installed source., Establish a fresh cursor for one finite workflow., Return to idle draining and discard unread workflow events., Return the next active-workflow event or an inactivity timeout., Retain active events because workflow activation owns cursor freshness., Wait until an idle source disconnect can be claimed for replacement. (+12 more)

### Community 72 - "test_baseline.py"
Cohesion: 0.49
Nodes (13): _create_capture(), datetime, MonkeyPatch, Path, _store(), test_atomic_write_failure_preserves_existing_pointer(), test_basic_not_observable_session_is_baseline_eligible(), test_dangling_or_corrupt_pointer_fails_reads_and_mutations() (+5 more)

### Community 73 - "_StreamWriter"
Cohesion: 0.12
Nodes (12): _DtrControl, Protocol, setter, Return the next bytes or empty bytes for EOF., Return transport-owned connection information., Begin closing the stream transport., Wait until the stream transport is closed., Return the current DTR state. (+4 more)

### Community 74 - "test_retention.py"
Cohesion: 0.49
Nodes (13): _create_capture(), _native_store(), datetime, MonkeyPatch, Path, test_corrupt_pointer_and_unknown_schema_suspend_retention(), test_corrupt_session_evidence_suspends_retention(), test_legacy_sessions_count_toward_limit_but_remain_protected() (+5 more)

### Community 76 - "CaptureRecorder"
Cohesion: 0.05
Nodes (72): CaptureRecorder, CaptureRecordResult, CaptureWorkflow, BackendEvent, CommandedBootMode, Exception, SessionWorkflow, Create one capture session. (+64 more)

### Community 77 - "Ring Buffer Sizing Plan"
Cohesion: 0.18
Nodes (13): Revision A and Phase 1 Hardware Acceptance, 32 KiB UART RX Ring Buffer, Buffer Integrity Reporting, Drop-Oldest Overflow Policy, RP2040 Memory Budget, Ring Buffer Sizing Plan, Ring Buffer Validation Gate, Ring Buffer Acceptance Checklist (+5 more)

### Community 78 - "DUTchMate Project Context"
Cohesion: 0.17
Nodes (13): Backend-Independent Host Pipeline, Phase 1A Basic Backend, Phase 1B Enhanced Backend, Enhanced NDJSON Protocol Contract, Normalized Backend Contract, AI-Assisted Embedded Debugging, Human and AI Clients, Normalized Evidence Boundary (+5 more)

### Community 79 - "test_reconnect_evidence.py"
Cohesion: 0.44
Nodes (12): _create_active_session(), parametrize, Path, _snapshot_for_segment(), test_disconnect_and_resume_append_segment_lifecycle_evidence(), test_disconnect_quota_rejection_keeps_summary_without_detailed_event(), test_reconnect_quota_rejection_does_not_publish_new_segment(), test_resume_rejects_incompatible_backend_without_writing() (+4 more)

### Community 80 - "smoke_installed_distribution.py"
Cohesion: 0.24
Nodes (18): Message, _assert_apache_license(), _assert_release_metadata(), _install_tool(), main(), _parser(), ArgumentParser, CompletedProcess (+10 more)

### Community 81 - "SessionListPage"
Cohesion: 0.11
Nodes (23): _enhanced_segment(), _enhanced_timestamp(), BaselineRuntime, _capture(), Path, SessionDetail, _store(), test_baseline_endpoint_maps_state_schema_and_pointer_faults() (+15 more)

### Community 82 - "fixture_protocol.c"
Cohesion: 0.19
Nodes (12): dmf_sleep_fn, dmf_write_fn, command_equals(), dmf_fixture_emit_boot(), dmf_fixture_handle_command(), dmf_fixture_init(), emit_sequence(), write_data() (+4 more)

### Community 83 - "dutchmate_usb_connection_run"
Cohesion: 0.06
Nodes (42): dutchmate_cdc_tx_initialize(), dmh_command_executor_init(), command_uart_cancel(), dutchmate_command_runtime_discard_input(), dutchmate_command_runtime_end_epoch(), dutchmate_command_runtime_faulted(), dutchmate_command_runtime_initialize(), dutchmate_command_runtime_start_epoch() (+34 more)

### Community 84 - "evidence_package.py"
Cohesion: 0.10
Nodes (33): Deterministic, bounded excerpts from one validated native session., _evidence_fault(), _integer(), _jsonl_objects(), Exception, Path, Validated, stable native-session evidence reads for the Debug Agent., _read_artifact() (+25 more)

### Community 85 - "test_device_core_lifecycle.py"
Cohesion: 0.11
Nodes (26): BlockingCloseCaptureSource, ClosableReconnect, LifecycleCaptureSource, BaseException, FakeMonotonicClock, parametrize, Path, Catch a timed-out reconnect dropping the facade needed for final shutdown. (+18 more)

### Community 86 - "test_fixture_protocol.py"
Cohesion: 0.31
Nodes (16): _build_harness(), CompletedProcess, Path, _run_command(), test_binary_emits_invalid_utf8_bytes_without_encoding(), test_burst_is_bounded_numbered_and_self_checking(), test_info_reports_fixture_identity_and_build(), test_init_failure_boot_emits_stable_first_error() (+8 more)

### Community 87 - "OllamaAdapter"
Cohesion: 0.17
Nodes (16): _branch(), OllamaAdapter, AsyncBaseTransport, Local-only Ollama chat adapter for validated Debug Agent requests., Constrain references to the exact evidence coordinates in the frozen request., Use Ollama's non-streaming local chat endpoint without remote redirects., Return parsed model JSON; the shared boundary validates its report schema., _report_schema_for() (+8 more)

### Community 88 - "format_baseline_mutation"
Cohesion: 0.23
Nodes (10): _as_mapping(), _display(), format_baseline_mutation(), Terminal formatting for project baseline mutations., Format one mark or clear result without inferring evidence quality., MonkeyPatch, parametrize, test_baseline_commands_forward_named_session() (+2 more)

### Community 89 - "test_connection_monitoring.py"
Cohesion: 0.15
Nodes (14): NoopDeviceControl, BackendEvent, BaseException, ControlState, Path, QueueSource, Catch startup health omitting initial identity, segment, or integrity., Catches replacement health omitting identity, integrity, or segment projection. (+6 more)

### Community 90 - "GPIO Configuration Semantics"
Cohesion: 0.22
Nodes (9): Control Channel State Model, Commanded Boot Mode State, GPIO Configuration Semantics, Role and DUT Signal Identifier Contract, Runtime GPIO Override Semantics, Safe High-Impedance Behavior, Semantic Control Workflows, GPIO Validation Order (+1 more)

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

### Community 98 - "provider_boundary.py"
Cohesion: 0.15
Nodes (24): _context(), main(), _parser(), ArgumentParser, Path, Host-facing preview and digest-approved Debug Agent analysis., EvidenceLimits, AnalysisManifest (+16 more)

### Community 99 - "FakeAsyncSerialReader"
Cohesion: 0.08
Nodes (21): FakeAsyncSerialReader, Fails if an uncorrelated response is dropped or exposed as evidence., Fails if an orphan response discards valid evidence preceding it., Fails if hello resolves before all same-batch event semantics are valid., Fails if hello resolves before later same-batch input is validated., Fails if evidence is not normalized in wire order from its first timestamp., Fails if a non-blocking evidence poll is rejected as an invalid timeout., Fails if discarding queued evidence masks a retained terminal error. (+13 more)

### Community 100 - "test_real_coordinator_discards_idle_basic_event_before_capture"
Cohesion: 0.21
Nodes (7): _basic_segment(), ConditionBackedBasicSource, _publish_after_barrier(), BackendEvent, test_real_coordinator_discards_idle_basic_event_before_capture(), WorkflowBarrierCoordinator, ThreadEvent

### Community 101 - "AsyncSerialReader"
Cohesion: 0.18
Nodes (8): AsyncFrameWriter, AsyncSerialReader, Protocol, Async byte reader owned by one Enhanced adapter., Return the next serial byte chunk, or empty bytes for EOF., Close the owned serial resource., Async Enhanced command-frame writer., Write and flush one complete host command frame.

### Community 102 - "Coordinated Background Reconnect Design"
Cohesion: 0.10
Nodes (19): Acceptance Criteria, Active-Workflow Disconnect, Add A Service-Owned Reconnect Coordinator, Atomic Replacement Publication, Considered Approaches, Context, Coordinated Background Reconnect Design, Documentation And Validation (+11 more)

### Community 103 - "backend_reconnect.py"
Cohesion: 0.09
Nodes (34): _build_async_enhanced_capture_reconnect(), build_enhanced_capture_reconnect(), OpenEnhancedHost, ControlState, Service-owned backend reopen and replaceable-control composition., Keep runtime control ports stable while Enhanced transports are replaced., Publish a newly connected backend control adapter., Keep the runtime UART-send port stable across backend replacement. (+26 more)

### Community 104 - "Software Architecture"
Cohesion: 0.43
Nodes (7): Backend Contract Foundation, Device Connection Module, Log Processing Module, Software Architecture, Thin Delivery Adapters, UART Capture Module, Workflow Orchestration Modules

### Community 105 - "report_schema.py"
Cohesion: 0.17
Nodes (29): AnalysisRequest, Versioned, bounded request assembled without provider calls., CodingContext, CodingContextLimits, _path(), _text(), SessionEvidence, _entries() (+21 more)

### Community 106 - "BasicBackendEventSource"
Cohesion: 0.12
Nodes (11): BasicBackendEventSource, BackendEvent, Normalize raw Basic serial chunks through one FIFO reader thread., Return immutable Basic backend identity and capabilities., Return the session-local segment ID assigned to this source., Return host-monotonic provenance established at source creation., Return the next FIFO event, or ``None`` for an ordinary timeout., Blocking compatibility adapter used by the current capture runner. (+3 more)

### Community 107 - "_validator"
Cohesion: 0.38
Nodes (10): Draft202012Validator, parametrize, Path, test_every_checked_in_host_command_example_matches_the_schema(), test_gpio_schema_accepts_safe_electrical_combinations(), test_gpio_schema_rejects_host_only_metadata(), test_gpio_schema_rejects_unsafe_electrical_combinations(), test_schema_accepts_generic_control_actions() (+2 more)

### Community 108 - "Phase 1A Basic Hardware-in-the-Loop Validation"
Cohesion: 0.07
Nodes (27): Boot modes, Build, Create a Zephyr 4.4 workspace, DUTchMate Zephyr DUT Fixture, Flash, HIL provenance, Local protocol verification, Supported baseline (+19 more)

### Community 109 - "test_device_message_schema.py"
Cohesion: 0.39
Nodes (8): _hello(), Draft202012Validator, parametrize, Path, test_every_checked_in_device_message_example_matches_the_schema(), test_schema_accepts_phase1_enhanced_capability(), test_schema_rejects_legacy_uart_capture_capability(), _validator()

### Community 110 - "host_to_device.schema.json"
Cohesion: 0.40
Nodes (4): $id, oneOf, $schema, title

### Community 111 - "DtrControlledSerial"
Cohesion: 0.13
Nodes (9): AttachedSerialTransport, DtrControlledSerial, MonkeyPatch, setter, Fails if restart can hide DTR low from the firmware epoch poller., Fails if graceful shutdown can leave the firmware epoch active., test_owned_stream_reader_holds_dtr_low_before_closing(), test_production_opener_closes_serial_if_reader_attachment_fails() (+1 more)

### Community 112 - "dutchmate-core"
Cohesion: 0.47
Nodes (6): dutchmate, dutchmate-cli, dutchmate-core, dutchmate-debug-agent, dutchmate-mcp-server, dutchmate-service

### Community 113 - "DeviceCoreClient"
Cohesion: 0.17
Nodes (5): DeviceCoreClient, BaseException, TracebackType, Close the owned HTTP connection pool., Call bounded Device Core endpoints without owning hardware or sessions.

### Community 114 - "FakeDeviceControl"
Cohesion: 0.25
Nodes (6): FakeDeviceControl, _hello(), ControlState, DeviceMessage, test_create_app_applies_startup_hardware_config_when_runtime_is_connected(), test_rejected_startup_hardware_config_is_visible_in_status()

### Community 115 - "TerminationBarrierAdapter"
Cohesion: 0.13
Nodes (9): BlockingAsyncFrameWriter, _close_after_entering(), CloseBlockingAsyncSerialReader, Pause cleanup after request code has selected its terminal outcome., Fails if cancellation turns resource-close start into false completion., Fails if cancelling the response future races terminal cause selection., TerminationBarrierAdapter, test_cancellation_selects_terminal_before_response_can_be_orphaned() (+1 more)

### Community 126 - "SerialFrameSink"
Cohesion: 0.17
Nodes (10): _ThreadedSerialFrameWriter, Protocol, Pyserial-compatible surface for exact host frame writes., Return the number of bytes accepted from data., Wait until accepted output is flushed., SerialFrameSink, Fails if command writes use the event loop or skip partial-write recovery., Fails if a worker-thread write loses exact accepted-byte accounting. (+2 more)

### Community 127 - "dutchmate_cli/config.py"
Cohesion: 0.21
Nodes (16): CliConfigError, DaemonConfig, _optional_port(), _optional_positive_int(), _optional_str(), _optional_table(), _parse_daemon_config(), _parse_sessions_config() (+8 more)

### Community 128 - "Enhanced Async Service Integration Design"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Architectural Decision, Command And Event Data Flow, Core Async Semantic Consumers, Enhanced Async Service Integration Design, Failure And Shutdown Semantics, Purpose, Runtime And FastAPI Lifecycle (+6 more)

### Community 129 - "resolve_backend_settings"
Cohesion: 0.27
Nodes (13): BackendConfig, Apply explicit overrides and backend-specific defaults., Optional project backend selection loaded from TOML., resolve_backend_settings(), parametrize, test_backend_mode_is_required_without_cli_or_config_value(), test_basic_backend_requires_explicit_or_configured_port(), test_enhanced_backend_rejects_non_protocol_baudrate() (+5 more)

### Community 130 - "time_us_64"
Cohesion: 0.18
Nodes (20): cdc_callback(), dutchmate_cdc_tx_cancel(), dutchmate_cdc_tx_poll(), dutchmate_cdc_tx_start(), command_uart_start(), dutchmate_command_runtime_on_cdc_rx_ready(), dut_uart_callback(), mark_driver_fault() (+12 more)

### Community 131 - "File Responsibility Map"
Cohesion: 0.18
Nodes (10): Coordinated Background Reconnect Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Non-Consuming Enhanced Segment Readiness, Task 2: Carry And Adopt Versioned Validated Connection Health, Task 3: Make Ingestion The Idle-Reconnect Commit Point, Task 4: Add The Idle/Active Reconnect State Engine, Task 5: Build Basic And Async Enhanced Candidates (+2 more)

### Community 132 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Enhanced Async Service Integration Implementation Plan, File Responsibility Map, Global Constraints, Task 1: Add Async Enhanced Semantic Consumers, Task 2: Add Atomic Adapter FIFO Discard, Task 3: Implement The Service-Owned Enhanced Async Host, Task 4: Select The Async Host In Enhanced Startup, Task 5: Add Runtime And FastAPI Lifecycle Ownership (+1 more)

### Community 133 - "BlockingCloseStreamWriter"
Cohesion: 0.15
Nodes (5): BlockingCloseStreamWriter, FakeStreamTransport, OrderedCloseStreamWriter, Fails if paired stream closure is duplicated or not awaited by all callers., test_owned_stream_reader_delegates_reads_and_shares_close_completion()

### Community 134 - "test_protocol_integration.py"
Cohesion: 0.20
Nodes (10): _client_factory(), parametrize, Request, Response, test_modern_stream_client_cancellation_stops_the_tool_call(), test_modern_stream_client_discovers_lists_and_calls_tools(), test_modern_stream_client_rejects_unsupported_protocol_version(), test_modern_stream_rejects_unadvertised_capabilities() (+2 more)

### Community 135 - "format_wait_pattern"
Cohesion: 0.25
Nodes (9): _display(), format_wait_pattern(), _mapping(), CLI formatting for finite literal wait-pattern outcomes., Format a matched or ordinary unmatched wait outcome., MonkeyPatch, test_format_wait_pattern_prints_match_excerpt_and_provenance(), test_format_wait_pattern_prints_no_match_as_successful_outcome() (+1 more)

### Community 136 - "validate_coding_context"
Cohesion: 0.17
Nodes (27): BuildContext, ChangedFile, _commit(), ContextExcerpt, _diff_hunks(), DiffHunk, _excerpt(), _mapping() (+19 more)

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

### Community 141 - "make_adapter"
Cohesion: 0.08
Nodes (25): make_adapter(), Fails if terminal input overtakes accepted evidence or changes on replay., Fails if a second hello is accepted as evidence or connection state., Fails if hello timeout leaks the reader or permits a later restart., Fails if close strands hello or exposes a different terminal object., Fails if concurrent starts each own a reader or do not share one hello., Fails if post-hello input masks a retained parser terminal error., Fails if segment readiness consumes the first normalized evidence event. (+17 more)

### Community 142 - "test_gpio.py"
Cohesion: 0.23
Nodes (10): _display(), format_gpio_mode_result(), Terminal formatting for GPIO control commands., Format a successful GPIO mode configuration response., MonkeyPatch, parametrize, test_format_gpio_mode_result_renders_accepted_mapping(), test_gpio_mode_command_configures_channel() (+2 more)

### Community 143 - "test_evidence_package.py"
Cohesion: 0.25
Nodes (24): build_analysis_request(), Combine native evidence with optional validated caller context., build_session_evidence(), Assemble bounded, priority-selected evidence without changing stored facts., _append_lines(), _native_session(), MonkeyPatch, Path (+16 more)

### Community 144 - "command_runtime.c"
Cohesion: 0.13
Nodes (17): atomic_val_t, cdc_rx_thread(), command_thread(), command_uart_poll(), dutchmate_command_runtime_response_sent(), dutchmate_command_runtime_take_response(), epoch_matches(), mark_runtime_fault() (+9 more)

### Community 145 - "File Responsibility Map"
Cohesion: 0.20
Nodes (9): Continuous Connection Monitoring Implementation Plan, File Responsibility Map, Global Constraints, Requirement Coverage Check, Task 1: Publish Current-Source Connection Health, Task 2: Project Enhanced Integrity Without Double Delivery, Task 3: Reconcile Runtime State Before Observation And Admission, Task 4: Prove Existing Service Status Boundary End To End (+1 more)

### Community 146 - "main"
Cohesion: 0.13
Nodes (12): main(), Start the Device Core Service., Any, Path, test_service_main_passes_config_to_app_and_host_port_to_uvicorn(), load_backend_config(), Any, Path (+4 more)

### Community 147 - "DUTchMate Revision A Voltage-Domain GPIO and UART Interface"
Cohesion: 0.17
Nodes (11): 13. Known limitations, 14. Prototype validation checklist, 15. Revision A provisional BOM, 16. Source documents, 17. Revision A Recommendation, 1. Purpose, 3.1 Net naming and hardware-to-software mapping, 3. Selected architecture (+3 more)

### Community 148 - "mcp.schema.json"
Cohesion: 0.20
Nodes (9): mcpServers, additionalProperties, description, $id, $schema, required, $schema, title (+1 more)

### Community 149 - "test_recovery.py"
Cohesion: 0.38
Nodes (13): _clock(), _create_active_native(), datetime, MonkeyPatch, parametrize, Path, _recovery_clock(), test_recovery_abandons_stale_active_native_session() (+5 more)

### Community 150 - "url"
Cohesion: 0.24
Nodes (10): $ref, headers, type, url, properties, properties, const, description (+2 more)

### Community 151 - "BlockingCloseSource"
Cohesion: 0.13
Nodes (11): BlockingCloseSource, BlockingFailingCloseSource, EventReleasedByCloseSource, FailingCloseSource, BackendEvent, BaseException, test_close_while_workflow_active_is_safe_for_finally_cleanup(), test_concurrent_close_calls_share_exact_cleanup_error_and_close_once() (+3 more)

### Community 152 - "_run"
Cohesion: 0.32
Nodes (11): CompletedProcess, fixture, parametrize, Path, TempPathFactory, _run(), test_uart_event_accepts_bounded_staging_maximum(), test_uart_event_encodes_binary_and_base64_padding() (+3 more)

### Community 153 - "test_enhanced_serial.py"
Cohesion: 0.10
Nodes (20): _compact_json_frame_of_size(), Async Enhanced serial reader lifecycle tests., Fails if shutdown leaves the sole reader blocked or closes it more than once., Fails if a full FIFO drops/reorders evidence or lets its sole reader advance., Fails if pending-frame overflow loses its exact bounded size context., Fails if an invalid host frame reaches the serial writer., Fails if the initial device frame is accepted without a hello handshake., Fails if same-batch evidence still terminalizes a valid hello handshake. (+12 more)

### Community 154 - "SessionHandle"
Cohesion: 0.04
Nodes (42): _append_line(), Reference to a created debug session., SessionHandle, CommandedBootMode, SessionWorkflow, Persist derived records finalized at segment or session close., Append one accepted normalized control action atomically., Durably append a forced-send attempt and reserve its result record. (+34 more)

### Community 155 - "BackendDisconnectedError"
Cohesion: 0.11
Nodes (18): Close the source and join the single ingestion thread., Catches an idle reconnect path that requires a synthetic workflow read., Catches an idle claimant detaching a source owned by an active workflow., Catches changing active reconnect callers to require the idle claim path., test_active_terminal_consumption_permits_legacy_reconnect_detach(), test_active_workflow_cannot_claim_idle_disconnect(), test_close_while_ingestion_waits_for_replacement_stops_thread(), test_idle_disconnect_claim_detaches_without_workflow_read() (+10 more)

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

### Community 161 - "properties"
Cohesion: 0.22
Nodes (9): items, type, description, pattern, type, type, args, cwd (+1 more)

### Community 162 - "apply_startup_hardware_config"
Cohesion: 0.18
Nodes (9): apply_startup_hardware_config(), GpioRoleName, Protocol, Runtime surface needed to apply startup hardware configuration., Return current runtime status., Apply configured hardware control mappings., Apply startup GPIO mappings if a Debug Helper is already connected., StartupConfigRuntime (+1 more)

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

### Community 184 - "_UnavailableDeviceControl"
Cohesion: 0.36
Nodes (3): ControlState, NoReturn, _UnavailableDeviceControl

### Community 185 - "connection_epoch.c"
Cohesion: 0.40
Nodes (3): dmh_connection_epoch_init(), dmh_connection_epoch_update(), main()

### Community 186 - "_run_hello"
Cohesion: 0.44
Nodes (8): _build_harness(), CompletedProcess, parametrize, Path, _run_hello(), test_hello_accepts_64_byte_safe_firmware_identifier(), test_hello_matches_complete_v1_identity_and_capability_contract(), test_hello_rejects_unsafe_firmware_identifier()

### Community 187 - "discovery.py"
Cohesion: 0.20
Nodes (16): ComportsProvider, _candidate_from_port(), _has_dutchmate_text_hint(), list_dutchmate_candidates(), list_serial_ports(), ListPortInfo, Protocol, _pyserial_comports_provider() (+8 more)

### Community 188 - "_BoundedNewest"
Cohesion: 0.40
Nodes (3): _BoundedNewest, _T, Retain the newest coordinate-ordered records with bounded memory.

### Community 189 - "ReplaceableCaptureSource"
Cohesion: 0.15
Nodes (10): OpenCaptureReplacement, Event, Protocol, Open one segment-bound replacement source., Return a fully prepared replacement or raise for a failed attempt., Stable capture facade that exclusively owns concrete backend sources., Wait for an idle disconnected source that can be claimed., Detach and close the consumed source before reconnect opening. (+2 more)

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

### Community 201 - "verify_index_artifacts.py"
Cohesion: 0.31
Nodes (9): _artifact_identity(), collect_artifacts(), fetch_releases(), main(), Path, Verify that a package index exposes the exact locally accepted artifacts., Require each local filename and SHA-256 digest on the remote index., Read project identities from wheel/sdist metadata and hash each artifact. (+1 more)

### Community 202 - "GpioIdentifierValidationError"
Cohesion: 0.17
Nodes (12): _request_gpio_identifier_error(), GpioIdentifierValidationError, Validate and return an exact 1..64-byte GPIO role or signal identifier., Validate and preserve an exact DUT schematic signal identifier., Raised when a GPIO role or DUT signal violates the exact identifier contract., validate_gpio_dut_signal(), validate_gpio_identifier(), IdentifierValidationReason (+4 more)

### Community 203 - "dmh_output_drain_batch"
Cohesion: 0.33
Nodes (7): dmh_output_drain_one_fn, dmh_output_drain_batch(), drain_one(), main(), test_drains_until_idle(), test_error_stops_batch(), test_full_batch_keeps_draining()

### Community 204 - "server.py"
Cohesion: 0.31
Nodes (8): _execute(), ValueError, Stateless MCP server composition for the stdio delivery adapter., _tool_result(), _validation_error_payload(), CallToolResult, ClientFactory, ClientOperation

### Community 205 - "DUTchMate Licensing"
Cohesion: 0.22
Nodes (7): Contributing to DUTchMate, Developer Certificate of Origin, Validation, Contributions and third-party material, Documentation attribution, DUTchMate Licensing, Hardware design exception

### Community 206 - "service_client.py"
Cohesion: 0.11
Nodes (18): DeviceCoreClientError, DeviceCoreProtocolError, DeviceCoreServiceError, DeviceCoreUnavailableError, _json_object(), AsyncBaseTransport, NoReturn, Response (+10 more)

### Community 207 - "Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What code boundary owns complete CDC frame writes for hello, responses, and evidence?, Source Nodes

### Community 208 - "test_cdc_tx_state_machine"
Cohesion: 0.60
Nodes (4): _build_harness(), parametrize, Path, test_cdc_tx_state_machine()

### Community 209 - "create_server"
Cohesion: 0.20
Nodes (17): create_server(), Run the server over stdio; no other MCP transport is exposed., Create one stateless MCP server with fixed protocol-facing metadata., run_stdio(), _client_factory(), Request, Response, test_create_server_configures_finite_private_cache_hints() (+9 more)

### Community 210 - "streamableHttpServer"
Cohesion: 0.29
Nodes (8): type, url, streamableHttpServer, required, additionalProperties, required, title, type

### Community 211 - "test_release_validation.py"
Cohesion: 0.36
Nodes (7): _load_script(), parametrize, Path, Release tag and uploaded-artifact validation contracts., test_release_tag_matches_every_distribution_version(), test_release_tag_rejects_unsupported_shapes(), test_uploaded_release_requires_every_local_artifact_digest()

### Community 212 - "properties"
Cohesion: 0.25
Nodes (8): $ref, additionalProperties, type, properties, mcpServers, $schema, const, description

### Community 213 - "collect_stack_probe.py"
Cohesion: 0.27
Nodes (10): collect(), main(), Read a frozen post-epoch Zephyr stack report over the normal USB CDC port., read_hello(), main(), _open_port(), probe(), Any (+2 more)

### Community 214 - "test_dut.py"
Cohesion: 0.20
Nodes (13): _display(), format_boot_mode_result(), format_reset_result(), Terminal formatting for DUT action commands., Format a successful DUT boot-mode response., Format a successful DUT reset response., MonkeyPatch, test_dut_boot_mode_command_reports_service_error() (+5 more)

### Community 215 - "$defs"
Cohesion: 0.25
Nodes (8): $defs, server, sseServer, oneOf, title, additionalProperties, title, type

### Community 216 - "dmh_hello_encode"
Cohesion: 0.38
Nodes (4): bounded_string_length(), dmh_hello_encode(), is_safe_firmware_byte(), main()

### Community 217 - "McpLogLevel"
Cohesion: 0.16
Nodes (18): launch_mcp(), McpLaunchError, McpLogLevel, NoReturn, RuntimeError, Process launcher for the separately packaged MCP stdio adapter., Log levels accepted by the MCP server entrypoint., Raised when the MCP server process cannot be launched. (+10 more)

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

### Community 227 - "test_agent_plugin.py"
Cohesion: 0.39
Nodes (7): _frontmatter(), _json(), Path, Portable coding-agent plugin packaging contracts., test_plugin_skills_have_valid_frontmatter(), test_portable_plugin_manifest_and_stdio_mcp_registration(), test_repo_marketplace_exposes_the_portable_plugin()

### Community 228 - "_decimal_define"
Cohesion: 0.67
Nodes (3): _decimal_define(), Path, test_cdc_tx_fifo_holds_one_maximum_evidence_frame()

### Community 229 - "BasicBackendConnection"
Cohesion: 0.11
Nodes (18): build_basic_capture_reconnect(), OpenBasicConnection, Build coordinated idle and active reopen for one selected Basic backend., Open one raw Basic connection from resolved settings., Return an opened Basic connection., _basic_settings(), FakeBasicSerial, test_basic_active_candidate_uses_coordinator_and_replaces_sender() (+10 more)

### Community 230 - "test_debug_cli.py"
Cohesion: 0.37
Nodes (13): Optional Debug Agent application; no provider is enabled by default., _args(), CaptureFixture, MonkeyPatch, parametrize, Path, _session(), test_cli_analyze_requires_reviewed_digest_before_provider_call() (+5 more)

### Community 231 - "SegmentContext"
Cohesion: 0.08
Nodes (48): _snapshot(), _snapshot(), backend_snapshot(), EnhancedReconnectHost, Ready async Enhanced host used as source, control, and UART sender., _snapshot(), enhanced_replacement_snapshot(), test_status_returns_connected_gpio_mapping_state() (+40 more)

### Community 232 - "4. Four debugger-to-DUT control outputs"
Cohesion: 0.25
Nodes (8): 4.1 Device, 4.2 Logical connection, 4.3 Configured modes and output drive states, 4.4 Reset example, 4.5 Push-pull example, 4.6 Safe startup state, 4.7 Control-channel limitations, 4. Four debugger-to-DUT control outputs

### Community 233 - "5. Four DUT-to-debugger event inputs"
Cohesion: 0.25
Nodes (8): 5.1 Device, 5.2 Logical connection, 5.3 Supported DUT event outputs, 5.4 Event interface enable, 5.5 Event-channel limitations, 5. Four DUT-to-debugger event inputs, Open-drain DUT output, Push-pull DUT output

### Community 235 - "enhanced_serial_io.py"
Cohesion: 0.29
Nodes (8): _close_without_masking_primary(), open_async_enhanced_serial_adapter(), OpenSerialConnection, _OwnedStreamReader, Concrete stream and exact-write I/O for one Enhanced serial connection., Open, hello-validate, and return one production Enhanced adapter., _run_cleanup(), _serial_asyncio_opener()

### Community 236 - "env"
Cohesion: 0.29
Nodes (7): PLUGIN_DATA, PLUGIN_ROOT, propertyNames, type, enum, env, not

### Community 237 - "test_service_client.py"
Cohesion: 0.22
Nodes (10): parametrize, Request, Response, _request_json(), test_client_maps_the_phase2_tool_surface_to_device_core(), test_client_preserves_structured_service_errors(), test_client_rejects_invalid_service_response_contracts(), test_client_rejects_invalid_service_urls() (+2 more)

### Community 238 - "test_distribution_metadata.py"
Cohesion: 0.27
Nodes (8): _project(), Path, Distribution metadata contracts for one synchronized DUTchMate release., test_all_host_distributions_publish_apache_license_and_owner_metadata(), test_all_host_distributions_use_the_workspace_version(), test_console_scripts_have_one_authoritative_owner(), test_first_party_dependencies_use_exact_host_version_constraints(), test_workspace_root_remains_unlicensed_as_one_distribution()

### Community 239 - "stdioServer"
Cohesion: 0.33
Nodes (6): command, stdioServer, additionalProperties, required, title, type

### Community 241 - "headers"
Cohesion: 0.33
Nodes (6): type, headers, additionalProperties, additionalProperties, title, type

### Community 242 - "Phase 1B Enhanced Workflow HIL Evidence"
Cohesion: 0.40
Nodes (4): Basic and Enhanced downstream evidence structure, Configured boot-mode workflow, Controlled USB reconnect, Phase 1B Enhanced Workflow HIL Evidence

### Community 243 - "test_workflows.py"
Cohesion: 0.50
Nodes (7): _assert_actions_are_commit_pinned(), Delivery workflow configuration contracts., test_firmware_ci_has_three_builds_and_pinned_inputs(), test_firmware_ci_uses_the_pinned_sdk_size_tool_without_path_lookup(), test_python_ci_has_the_required_jobs_and_pinned_actions(), test_release_build_and_publish_authority_are_separated(), _workflow()

### Community 244 - "DeviceCoreSessionStorage"
Cohesion: 0.09
Nodes (13): DeviceCoreSessionStorage, Protocol, SessionDetail, Return one bounded newest-first session page., Return bounded schema-aware detail for one session., Return bounded recent UART replay for one selected native session., Return one authoritative stored detected-pattern record., Designate one eligible session as the project baseline. (+5 more)

### Community 245 - "test_device_message_examples.py"
Cohesion: 0.46
Nodes (7): parse_example(), test_parse_buffer_overflow_example(), test_parse_buffer_status_example(), test_parse_error_response_example(), test_parse_hello_example(), test_parse_success_response_example(), test_parse_uart_event_example()

### Community 246 - "Q: What are the things remaining from development side"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What are the things remaining from development side, Source Nodes

### Community 247 - "Q: Review DUTchMate CI Packaging Plugin Implementation Plan and integrate it into the development plan"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Review DUTchMate CI Packaging Plugin Implementation Plan and integrate it into the development plan, Source Nodes

### Community 248 - "Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Move from deferred Phase 1 hardware work to the next Phase 2 development step, Source Nodes

### Community 249 - "Q: Revise CI packaging release firmware versioning and plugin distribution plan"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Revise CI packaging release firmware versioning and plugin distribution plan, Source Nodes

### Community 250 - "Q: Assess direct Debug Agent Python API launch and console-script ownership migration requirements"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Assess direct Debug Agent Python API launch and console-script ownership migration requirements, Source Nodes

### Community 251 - "plugin.json"
Cohesion: 0.40
Nodes (4): description, name, $schema, version

### Community 252 - "UartReceiveEvent"
Cohesion: 0.09
Nodes (49): Raw UART bytes observed by a backend within one connection segment., UartReceiveEvent, line_limit_exceeded_event_json(), OversizedUartLine, Bounded descriptor for one physical line that exceeded the derived limit., Backend-independent UART receive processing to log lines and matches., Finalize and discard trailing derived state for one connection segment., Completed UART lines and pattern matches produced from one processing step. (+41 more)

### Community 253 - "write_firmware_provenance.py"
Cohesion: 0.50
Nodes (4): main(), _parser(), ArgumentParser, Collect immutable firmware artifacts and write their provenance manifest.

### Community 254 - "test_firmware_provenance.py"
Cohesion: 0.40
Nodes (3): Path, Firmware product-version and artifact-provenance contracts., test_provenance_collector_copies_and_hashes_firmware_artifacts()

### Community 258 - "validate_release_tag"
Cohesion: 0.40
Nodes (5): main(), Path, Validate a host release tag against every synchronized distribution version., Return the release version after validating tag shape and all authorities., validate_release_tag()

### Community 262 - "12. Design decisions and rationale"
Cohesion: 0.33
Nodes (6): 12.1 Why fixed-direction blocks are used, 12.2 Why control and event GPIOs are separate, 12.3 Why the control translator uses independent output enables, 12.4 Why UART uses a dedicated device, 12.5 Why control enable uses an open-drain logic driver, 12. Design decisions and rationale

### Community 263 - "7. Power and sequencing"
Cohesion: 0.33
Nodes (6): 7.1 DUT_VIO, 7.2 DUT_VIO current budget, 7.3 Decoupling, 7.4 Default state, 7.5 DUT removal or missing DUT power, 7. Power and sequencing

### Community 264 - "default_cli_config"
Cohesion: 0.50
Nodes (3): default_cli_config(), fixture, MonkeyPatch

### Community 265 - "HardwareGpioConfig"
Cohesion: 0.18
Nodes (11): load_startup_hardware_config(), Path, Load startup hardware configuration, treating a missing file as empty config., test_load_startup_hardware_config_returns_empty_config_when_missing(), HardwareGpioConfig, load_hardware_gpio_config(), Path, Validated hardware GPIO mappings from project configuration. (+3 more)

### Community 266 - "11. Suggested firmware model"
Cohesion: 0.50
Nodes (4): 11.1 Control-channel configuration, 11.2 User configuration example, 11.3 Configuration validation rules, 11. Suggested firmware model

### Community 267 - "2. System requirements"
Cohesion: 0.50
Nodes (4): 2.1 Debugger domain, 2.2 DUT domain, 2.3 Supported signal types, 2. System requirements

### Community 268 - "6. UART interface"
Cohesion: 0.50
Nodes (4): 6.1 Device, 6.2 Logical connection, 6.3 UART recommendations, 6. UART interface

### Community 269 - "10. Debugger MCU resource estimate"
Cohesion: 0.67
Nodes (3): 10.1 Phase 1 Revision A Raspberry Pi Pico 2 pin assignment, 10.2 Other required Raspberry Pi Pico 2 connections, 10. Debugger MCU resource estimate

### Community 271 - "backend_snapshot"
Cohesion: 0.17
Nodes (10): backend_snapshot(), setter, Catches replacement publishing connected health without its validated identity., Catches a failed replacement segment lookup partially publishing the candidate., Catches rejected idle replacement candidates being left open., segment(), test_failed_idle_replacement_publication_closes_candidate(), test_idle_replacement_commits_snapshot_and_next_connection_generation() (+2 more)

### Community 272 - "FakeEnhancedAsyncHost"
Cohesion: 0.18
Nodes (3): FakeEnhancedAsyncHost, BaseException, Synchronous test double for the service-owned async Enhanced host.

### Community 273 - "test_reader_failure_is_repeatable_disconnect"
Cohesion: 0.18
Nodes (10): Exception, parametrize, Fails if invalid values can create ambiguous reader or queue bounds., Fails if EOF/read failure is raw, transient, or loses its original cause., Fails if a non-positive or non-finite command timeout reaches the writer., Fails if invalid waits are passed to asyncio instead of rejected at the…, test_constructor_rejects_invalid_bounds(), test_reader_failure_is_repeatable_disconnect() (+2 more)

### Community 274 - "_request_after_entering"
Cohesion: 0.22
Nodes (11): Event, Fails if pre-transmission cancellation poisons the shared connection., Fails if close strands a consumer or closes its owned reader twice., Fails if close strands waiters, changes errors, or transmits queued work., Fails if close cannot release a transmitted request blocked in the writer., _receive_after_entering(), _request_after_entering(), test_cancel_while_waiting_for_command_lock_keeps_connection() (+3 more)

### Community 275 - ".close"
Cohesion: 0.22
Nodes (6): _CandidateCleanupFailure, _close_unpublished_candidate(), BaseException, Exception, Keep a rejected candidate's primary failure distinct from close failure., Stop reconnect activity and join the idle worker exactly once.

### Community 276 - "test_transactions.py"
Cohesion: 0.58
Nodes (8): _create_active_session(), MonkeyPatch, Path, test_malformed_transaction_blocks_lifecycle_mutation(), test_startup_rolls_back_prepared_interrupted_transaction(), test_uart_batch_rolls_back_every_file_when_metadata_write_fails(), test_uart_unit_rolls_back_every_file_when_metadata_write_fails(), _transaction_artifacts()

### Community 277 - ".feed"
Cohesion: 0.40
Nodes (4): _frame_body(), DeviceMessage, Consume a serial byte chunk and return parsed complete messages., Return one exact JSON object body after removing one optional CR.

### Community 278 - "project_diagnostic_detail"
Cohesion: 0.40
Nodes (4): project_diagnostic_detail(), Bounded diagnostic projection shared by persistence and delivery adapters., Return a sanitized, non-empty diagnostic and whether it was truncated., _bounded_error()

## Ambiguous Edges - Review These
- `Phase 1A Basic Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements
- `Phase 1B Enhanced Backend` → `Normalized Backend Contract`  [AMBIGUOUS]
  docs/phase1_implementation_spec.md · relation: implements

## Knowledge Gaps
- **543 isolated node(s):** `dutchmate-debug-agent`, `$schema`, `$id`, `title`, `type` (+538 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `Development Status` (5× useful, score=3.744407163) _(code changed — re-verify)_
- `Revision A Prototype Validation Checklist` (5× useful, score=3.434427595) _(code changed — re-verify)_
- `Hardware Safe Startup State` (5× useful, score=3.395630892) _(code changed — re-verify)_
- `Revision A Voltage-Domain GPIO and UART Interface` (4× useful, score=2.848843965) _(code changed — re-verify)_
- `Firmware RAM Report` (4× useful, score=2.821030921)
- `Reconnect and Session Semantics` (4× useful, score=2.312510827)
- `DeviceCoreRuntime` (4× useful, score=2.282740605)
- `BackendEventSource` (4× useful, score=2.248089508)
- `Phase 1 Implementation Spec` (3× useful, score=1.840185766) _(code changed — re-verify)_
- `Continuous Ingestion and Async Enhanced Adapter` (3× useful, score=1.711489212) _(code changed — re-verify)_

**Known dead ends** — questions that led nowhere; don't re-derive.
- "What code boundaries connect bounded CDC command ingress, command execution, and ordered firmware responses with evidence?" -> `NdjsonStreamParser`, `AsyncEnhancedSerialAdapter`

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Phase 1A Basic Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **What is the exact relationship between `Phase 1B Enhanced Backend` and `Normalized Backend Contract`?**
  _Edge tagged AMBIGUOUS (relation: implements) - confidence is low._
- **Why does `SessionStore` connect `SessionStore` to `FakeDeviceControl`, `test_log_replay.py`, `test_evidence_package.py`, `DeviceCoreRuntime`, `test_recovery.py`, `test_transactions.py`, `comparison.py`, `SessionHandle`, `create_app`, `evidence.py`, `test_basic.py`, `fixed_clock`, `workflows/capture.py`, `store.py`, `test_app_lifecycle.py`, `test_device_core_uart_send.py`, `retrieval.py`, `test_startup_config.py`, `persistence.py`, `test_capture_reconnect.py`, `test_baseline.py`, `test_retention.py`, `CaptureRecorder`, `test_reconnect_evidence.py`, `SessionListPage`, `evidence_package.py`, `test_device_core_lifecycle.py`, `test_connection_monitoring.py`, `test_comparison.py`, `provider_boundary.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `SegmentContext`, `FakeDeviceControl`, `UartReceiveEvent`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `SegmentContext` connect `SegmentContext` to `.__init__`, `FakeDeviceControl`, `enhanced.py`, `metadata.py`, `CaptureEventSource`, `test_evidence_package.py`, `backend_snapshot`, `FakeEnhancedAsyncHost`, `DeviceCoreRuntime`, `SessionHandle`, `fixed_clock`, `runtime.py`, `EnhancedAsyncHost`, `workflows/capture.py`, `store.py`, `BackendInputError`, `SessionStore`, `retrieval.py`, `test_startup_config.py`, `test_capture_reconnect.py`, `CaptureRecorder`, `test_reconnect_evidence.py`, `SessionListPage`, `test_device_core_lifecycle.py`, `test_comparison.py`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `backend_reconnect.py`, `BasicBackendEventSource`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `UartReceiveEvent` connect `UartReceiveEvent` to `test_continuous_ingestion.py`, `FakeAsyncFrameWriter`, `FakeDeviceControl`, `test_log_replay.py`, `enhanced.py`, `make_adapter`, `test_evidence_package.py`, `CaptureEventSource`, `test_transactions.py`, `test_enhanced_serial.py`, `SessionHandle`, `BackendDisconnectedError`, `test_enhanced.py`, `evidence.py`, `test_basic.py`, `fixed_clock`, `runtime.py`, `EnhancedAsyncHost`, `workflows/capture.py`, `store.py`, `test_device_core_uart_send.py`, `SessionStore`, `test_startup_config.py`, `test_capture_reconnect.py`, `CaptureRecorder`, `SessionListPage`, `evidence_package.py`, `test_comparison.py`, `FakeAsyncSerialReader`, `test_real_coordinator_discards_idle_basic_event_before_capture`, `backend_reconnect.py`, `SegmentContext`, `BasicBackendEventSource`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 199 inferred relationships involving `SessionStore` (e.g. with `build_analysis_request()` and `load_baseline_context()`) actually correct?**
  _`SessionStore` has 199 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `DeviceCoreRuntime` (e.g. with `test_app_lifespan_closes_runtime_coordinator_and_ingestion_thread()` and `test_first_status_after_idle_replacement_projects_new_telemetry()`) actually correct?**
  _`DeviceCoreRuntime` has 94 INFERRED edges - model-reasoned connections that need verification._