# Development History

> Append-only historical record; not a progress tracker or next-step authority.
> See [Development Status](development_status.md) for the current milestone,
> blockers, ordered queue, and exact next step.

Add future completed-slice and detailed validation records immediately below
this preface so dated records remain newest-first. The migrated blocks below
retain their pre-split text byte-for-byte; the completed-work groups follow
their completion chronology after the detailed validation record.

## MCP v2 Slice 5 — Scoped External Acceptance and Registration — 2026-10-30

- Started clean at pushed Slice 4 `71a43f0` on `mcp/v2-service-client`.
  Completed the [existing scoped acceptance policy](mcp_integration_plan.md#test-and-acceptance-matrix)
  without changing its required/excluded checks. This record accepts the twelve
  v2 tools, independently of earlier nine-tool host/protocol evidence. Changed
  only the developer guide, current status and this history addition. No
  production, test, package, service, Device Core, firmware or hardware change.
- Verified current official documentation before external commands:
  [Inspector CLI](https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md)
  and its [read-only config-file form](https://github.com/modelcontextprotocol/inspector/blob/main/docs/mcp-server-configuration.md),
  [conformance requirements](https://github.com/modelcontextprotocol/conformance#conformance-requirements),
  [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
  and [connection destinations](https://code.visualstudio.com/docs/agent-customization/mcp-servers),
  and [Claude Code local stdio](https://code.claude.com/docs/en/mcp#option-3-add-a-local-stdio-server).
  Official npm metadata reported Inspector 2.13.0 with Node >=22.19.0. Installed
  acceptance tools under `/tmp` with
  `npm install --prefix /tmp/dutchmate-mcp-slice5-tools --no-audit --no-fund node@22.19.0 @modelcontextprotocol/inspector@2.13.0 @modelcontextprotocol/conformance@0.2.0-alpha.11`
  (`npm_config_cache=/tmp/dutchmate-mcp-slice5-npm`, sandbox escalation for
  downloads). The system Node 22.18.0 emitted install-time engine warnings;
  actual acceptance used the downloaded **Node v22.19.0**, verified with
  `--version`. Runner `--version` returned **0.2.0-alpha.11**; Inspector
  `--version` returned **2.13.0**. No global npm or project dependency changed.
- Exact Inspector command (read-only session config avoids launcher-option
  parsing ambiguity):

  ```bash
  /tmp/dutchmate-mcp-slice5-tools/node_modules/node/bin/node /tmp/dutchmate-mcp-slice5-tools/node_modules/@modelcontextprotocol/inspector/clients/launcher/build/index.js --cli --config /tmp/dutchmate-mcp-slice5/inspector.json --server dutchmate --method tools/list --strict
  ```

  The temporary `mcpServers.dutchmate` entry used `type: stdio`, `protocolEra:
  modern`, an absolute installed `dutchmate-mcp` resolved from the workspace's
  `.venv/bin`, `args: ["--service-url", "http://127.0.0.1:0"]` and stripped
  child PATH `/usr/bin:/bin`. No repository-relative module launch, actual
  Device Core access, or machine-specific config was committed. Exit **0**,
  empty stderr (no schema-portability findings), and exactly this returned order:
  `get_status`, `monitor`, `interact`, `send_uart`, `reset_dut`,
  `set_dut_boot_mode`, `get_evidence`, `get_recent_logs`, `list_sessions`,
  `get_session`, `release_connection`, `reacquire_connection`.
  Captured stdout SHA-256:
  `e99782a888c69f17ffa95080aa3daaf760ae045255549f656cd6fb290e5c112f`.
- Conformance used a disposable `/tmp` harness around the unchanged
  `create_server("http://127.0.0.1:0")` and SDK
  `streamable_http_app(stateless_http=True, json_response=True)`, served by
  uvicorn on **127.0.0.1:51527**. Only the runner's explicitly permitted
  loopback test projection was exposed; no product transport, service process,
  hardware, evidence store or fixture tools were added. Exact invocations below
  use these literal executable/script paths:

  ```bash
  N=/tmp/dutchmate-mcp-slice5-tools/node_modules/node/bin/node
  C=/tmp/dutchmate-mcp-slice5-tools/node_modules/@modelcontextprotocol/conformance/dist/index.js
  "$N" "$C" server --url http://127.0.0.1:51527/mcp --requirements 2026-07-28 --output-dir /tmp/dutchmate-mcp-slice5/requirements --verbose
  "$N" "$C" server --url http://127.0.0.1:51527/mcp --spec-version 2026-07-28 --scenario server-stateless --output-dir /tmp/dutchmate-mcp-slice5/stateless --verbose
  "$N" "$C" server --url http://127.0.0.1:51527/mcp --spec-version 2026-07-28 --scenario tools-list --output-dir /tmp/dutchmate-mcp-slice5/tools-list --verbose
  "$N" "$C" server --url http://127.0.0.1:51527/mcp --spec-version 2026-07-28 --scenario caching --output-dir /tmp/dutchmate-mcp-slice5/caching --verbose
  ```

  `--requirements` selects the complete frozen set; separate scoped probes use
  `--spec-version`/`--scenario`, as required by the current official CLI.

  | Run | Actual result and disposition |
  |---|---|
  | Frozen requirements | Exit 1; 50 scenarios, 104 checks passed/61 failed; 13 unscored scenarios, 11 failing. Optional prompts/resources/media/progress/sampling/HTTP/task/MRTR fixtures are outside the approved tools-only stdio gate, not passes. |
  | `server-stateless` | Exit 1; 23 successes, 2 documented exclusions, 5 subscription checks skipped. Only `sep-2575-server-rejects-undeclared-capability` and `sep-2575-missing-capability-http-400` fail: both require the absent synthetic `test_missing_capability` sampling tool. All applicable checks pass. |
  | `tools-list` | Exit 0; all 3 pass: `tools-list`, `tools-name-format`, `wire-schema-valid`. |
  | `caching` | Exit 1; all 4 required checks pass: `sep-2549-tools-list-caching-hints`, `sep-2549-ttl-non-negative`, `sep-2549-cache-scope-valid`, `wire-schema-valid`. Three optional prompt/resource/template cache checks fail with METHOD_NOT_FOUND; resource-read cache skipped. |

  Verified applicable checks in both the frozen run and the scoped reports.
  Behavior matches the plan and historical runner investigation; no policy or
  version was silently changed. Raw outputs and `checks.json` were captured
  only under `/tmp/dutchmate-mcp-slice5` (temporary diagnostics, not permanent
  evidence locations). The projection received SIGTERM after all probes;
  uvicorn shutdown logged and connection refusal confirmed port 51527 closed.
- **VS Code disposition:** installed CLI **1.141.0**, commit
  `2a59476c9bfcb90b3ddc372c36762471b7dfad1c`, arm64. Ran
  `code --user-data-dir /tmp/dutchmate-mcp-slice5/vscode-profile --add-mcp '<JSON>'`,
  with JSON `name: dutchmate-slice5`, `type: stdio`, the same absolute installed
  launcher and unreachable service arguments above. Exit **0**, stdout
  `Added MCP servers: dutchmate-slice5`; parsed the temporary profile's
  `User/mcp.json` and confirmed its `servers` entry. Electron also printed a
  codesign `task_name_for_pid` error; registration persistence was independently
  verified. No user profile or repository host config was edited. Authenticated
  host UI/session was unavailable: startup, exact twelve-tool discovery and
  read-only `get_status` through VS Code were **not performed**, not accepted
  from registration/Inspector evidence. No agent host was started.
- **Claude Code disposition:** absent from PATH and checked local install
  locations; no authenticated Claude Code session was available. Registration,
  discovery and read-only call were **not performed/unavailable**. No inference
  from VS Code, Inspector or Claude API connector support. The plan explicitly
  permits named-host checks only when available; these optional gaps do not
  change the scoped migration disposition or become historical host passes.
- Updated developer registration examples to installed `dutchmate-mcp` with
  machine-independent placeholders and optional service URL/environment; kept
  `dutchmate mcp` as the supported sibling launcher alternative. Distinguished
  VS Code `.vscode/mcp.json`/user-profile `servers` from portable `.mcp.json`
  `mcpServers`, documented current Claude separator syntax, and linked the
  authoritative twelve-tool catalog. Service startup remains explicit and
  separate, logs stderr-only, and no hosted endpoint is documented. No
  superseded temporary working plan was present; the normative MCP mapping/
  acceptance document remains authoritative.
- Fresh repository validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

  | Command suffix | Result |
  |---|---|
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py tests/architecture tests/packaging --tb=short` | 372 passed in 11.35 s; includes installed commands, packaging/metadata, boundaries and Slice 3 actual-service tests |
  | `uv build --all-packages --no-sources --no-create-gitignore --offline --out-dir /tmp/dutchmate-mcp-slice5/dist` | All six wheel/sdist pairs built |
  | `uv run --frozen --offline python scripts/ci/smoke_installed_distribution.py --dist /tmp/dutchmate-mcp-slice5/dist` | Passed, exit 0; actual wheel installations in isolated tool environments, both installed MCP commands and existing metadata/command checks; downloads used sandbox escalation |
  | `uv run --frozen --offline ruff check .` | Passed |
  | `uv run --frozen --offline mypy` | Passed; 103 source files |
  | `uv run --frozen --offline pytest -q --tb=line` | 1,872 passed in 58.24 s |
  | `git diff --check` | Passed |

- Reviewed the complete documentation-only diff, registration JSON examples,
  local links and unchanged twelve-tool/retired-tool boundaries. Prior history,
  dated validation evidence, production/test/package files and hardware gates
  are preserved. No architecture, dependency, source ownership or product
  transport change; no Graphify update was needed. No hardware/HIL, serial
  access, commit or push. MCP v2 migration is complete under the approved
  scoped policy. Phase 1B, Stage 8 and Phase 1 remain incomplete until fresh
  manufactured KiCad Rev-A physical/electrical acceptance; historical EAGLE
  gaps and functional-HIL evidence boundaries remain unchanged.

## MCP v2 Slice 4 — Installed Launch and Boundary Regressions — 2026-10-30

- Implemented only [MCP plan Slice 4](mcp_integration_plan.md#independently-testable-implementation-sequence),
  starting clean at pushed Slice 3 `c119532` on `mcp/v2-service-client`.
  Changes are tests, installed-distribution verification tooling and status/
  history only. No production launcher, MCP, service, Device Core, packaging
  contract, firmware or hardware change was needed.
- Added fourteen installed-process cases in `test_installed_launch.py` for
  absolute `dutchmate mcp` and sibling `dutchmate-mcp`, from temporary working
  directories with `PATH=/usr/bin:/bin`, no `PYTHONPATH` or `VIRTUAL_ENV`.
  Raw JSON-RPC exchanges parse every stdout line instead of allowing an SDK
  transport to discard noise. Modern discovery, exact ordered twelve-tool
  catalog, repeated listing, private 300000 ms cache hints, matching structured/
  text errors, bounded actionable unavailable-service errors, continued protocol
  operation after errors, clean EOF and empty-stdin shutdown pass. Debug logs
  appear on stderr; stdout contains only protocol replies and no trailing output.
- Installed-process URL cases distinguish explicit flag from environment using
  conflicting valid/invalid values: flag overrides `DUTCHMATE_SERVICE_URL`,
  environment overrides the default, invalid scheme/credentials remain rejected
  as bounded tool errors. Existing client URL validation coverage stays passing;
  no normalization rule changed. Exact default `http://127.0.0.1:2040` and all
  five accepted case-normalized log levels are asserted at the entrypoint.
  Installed invalid-log-level and hosted-transport options fail on stderr with
  exit 2 and empty stdout. No service startup or local evidence artifacts occur.
- Strengthened the existing AST architecture suite with a narrow MCP import
  boundary: only HTTP/SDK, standard library support and the existing pure Core
  diagnostic/validation/query contracts are permitted. Hardware backends,
  firmware transport, runtime/service composition, evidence stores, Debug Agent
  and LLM dependencies are excluded. Direct file/dynamic-import/process calls
  and hosted transport launch paths are guarded; the only server `run` transport
  is stdio. Existing exact catalog/retired-tool/field rejection tests remain
  passing; no raw GPIO or compatibility aliases were added.
- Reproduced one verification defect before fixing it: the wheel smoke script
  still expected the retired nine-tool catalog. The new packaging regression
  failed with that mismatch (31 other focused cases passed). Refreshed only
  that verification script to the twelve tools, exercising both installed
  entrypoints, actual unavailable-service errors, modern metadata/cache hints,
  repeated listing and empty EOF without adding the tool bin directory to PATH.
  Added installed-distribution entrypoint/dependency checks and wheel metadata
  assertions for `mcp>=2.0,<3`, `httpx>=0.27` and `dutchmate-core==0.1.0`.
  No production product defect was found or fixed.
- Fresh validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

  | Command suffix | Result |
  |---|---|
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py tests/architecture tests/packaging --tb=short` | 372 passed in 11.32 s |
  | `uv build --all-packages --no-sources --no-create-gitignore --out-dir /tmp/dutchmate-mcp-slice4-dist` | All six wheel/sdist pairs built; initially unavailable offline build backend fetched with sandbox escalation |
  | `uv run --frozen --offline python scripts/ci/smoke_installed_distribution.py --dist /tmp/dutchmate-mcp-slice4-dist` | Passed (exit 0); temporary isolated uv tool environments installed actual built wheels, fetched declared runtime dependencies with sandbox escalation, verified metadata/entrypoints and both MCP stdio commands outside repository/dev PATH; existing debug-package help smoke also passed without starting an agent |
  | `uv run --frozen --offline ruff check .` | Passed |
  | `uv run --frozen --offline mypy` | Passed; 103 source files |
  | `uv run --frozen --offline pytest -q --tb=line` | 1,872 passed in 56.22 s; existing cancellation, EOF, version rejection and Slice 3 actual-service coverage retained |
  | `git diff --check` | Passed |

- Reviewed the complete seven-file diff and local documentation links. Prior
  history and dated validation text, production files/contracts and hardware
  acceptance/checklist remain intact. Only test/verification changes were made;
  no production interfaces, module ownership or dependency direction changed,
  so no architecture document or Graphify update was needed. No hardware/HIL,
  physical serial access, TCP listener, Device Core Service process, commit or
  push was used.
- Recorded Slice 4 complete; overall MCP migration remains incomplete. Stage 8,
  Phase 1B and Phase 1 remain incomplete pending manufactured KiCad Rev-A
  physical/electrical acceptance. Legacy EAGLE functional-HIL policy and
  unresolved historical electrical gaps remain unchanged.

## MCP v2 Slice 3 — Actual Service/Protocol Integration — 2026-10-30

- Implemented only [MCP plan Slice 3](mcp_integration_plan.md#independently-testable-implementation-sequence),
  starting clean at pushed Slice 2 `6497f85` on `mcp/v2-service-client`.
  Added twelve representative actual-service test cases without changing any
  production MCP, service, Device Core, firmware or hardware code/contracts.
  No production Slice 1/2 defect was discovered; no fix or redesign was needed.
- Added test-owned support in `tests/support/mcp_service_fixture.py`: a
  condition-driven normalized RX source, fake physical TX/control, real
  `DeviceCoreRuntime`, `ContinuousEvidenceRecorder`, `SessionStore` and
  `BackendReconnectCoordinator`, plus the actual `create_app(runtime)`.
  Modern SDK in-memory MCP calls use the real `DeviceCoreClient` with injected
  ASGI transport. The observer records actual HTTP status/body before the MCP
  projection and never replaces service validation, serialization or responses.
  The fixture follows existing controlled-source/runtime acceptance patterns
  without importing test modules through unstable test-directory paths.
- All twelve public tools traverse that path. Assertions compare MCP structured
  and text results with the actual ASGI response and independently inspect
  operation IDs/outcomes, cursor/range coordinates, exact base64/match excerpts,
  text transformation, integrity/provenance and actual fake physical dispatch.
  Coverage includes elapsed/matched/normal-timeout operations, profile-default
  CRLF, binary TX/RX including invalid UTF-8, nullable TX/error after lost ACK,
  durable attempt/results, and no silent retry.
- Real evidence/store coverage proves tail attach without historical replay,
  bounded one-record pages and opaque next-cursor round trips, exact raw bytes,
  omission fields, explicit recent-log session selection, v2 list/detail and
  pagination, profile/quality metadata, intentional gap and two segments after
  release/reacquire, and actual HTTP 410 after a terminal cursor cannot continue
  into a new ownership session. The store remains exclusively service/runtime
  infrastructure in the test directory; MCP owns no journal/session truth.
- Actual service errors cover invalid opaque cursor (`invalid_argument`),
  missing role (`not_configured`), absent capability and disabled TX policy
  (`unsupported_capability`), active Interact (`operation_active`), invalid
  release/reacquire state, expired cursor, and backend diagnostics truncated to
  the canonical UTF-8 bound. Detail/truncation/context survive unchanged.
  `invalid_session_state` is an explicitly injected runtime-boundary case:
  the active-session baseline guard in the real store supplies the failure to
  the real route/error handler. The twelve tools do not naturally invoke that
  guard; no baseline tool or artificial production contract was introduced.
- Modern cancellation reaches the real ASGI bounded Interact and Device Core
  cancellation event. The native terminal record retains the same operation ID
  with `cancelled`, while the dispatched TX keeps one successful audit/result;
  a blocked competing send is never dispatched, and a subsequent send succeeds
  after exclusivity releases. Event barriers replace timing guesses. MCP EOF
  cleans up the protocol while service ownership remains connected; ambient
  UART published afterward is still recorded. Fixture teardown closes runtime
  resources. There is no rollback claim or MCP-owned operation state machine.
- Fresh validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

  | Command suffix | Result |
  |---|---|
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests/test_protocol_integration.py -k actual_service --tb=short` | 12 passed in 1.45 s; existing behavior satisfied the new integration cases |
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py --tb=line` | 323 passed in 4.88 s, including unchanged ordered twelve-tool catalog, retired-tool absence, SDK metadata/cache/cancellation/EOF and installed stdio/launcher coverage |
  | `uv run --frozen --offline ruff check .` | Passed |
  | `uv run --frozen --offline mypy` | Passed; 103 source files |
  | `uv run --frozen --offline pytest -q --tb=line` | 1,850 passed in 49.21 s |
  | `git diff --check` | Passed |

- Complete diff and documentation links/preservation checks passed. Four files
  changed: protocol integration tests, the new test-support fixture, status and
  this history addition. Prior history/dated validation evidence and hardware
  acceptance/checklist remain intact. No production imports, module ownership,
  shared ports or dependency direction changed; no architecture document or
  Graphify update was needed for this test-only slice. No real serial hardware,
  physical HIL, TCP listener, second service process, commit or push was used.
- Recorded Slice 3 complete in status; overall MCP migration remains incomplete.
  Stage 8, Phase 1B and Phase 1 remain incomplete pending manufactured KiCad
  Rev-A physical/electrical acceptance. Existing EAGLE functional-HIL policy and
  unresolved historical electrical gaps are unchanged.

## MCP v2 Slice 2 — Public Catalog and Retired-Path Removal — 2026-10-30

- Implemented only [MCP plan Slice 2](mcp_integration_plan.md#independently-testable-implementation-sequence),
  starting clean at pushed Slice 1 `22cbd11` on `mcp/v2-service-client`.
  Registered exactly the twelve documented tools in order, each directly
  invoking its corresponding Slice 1 service-client operation once.
  `set_dut_boot_mode` uses unchanged `POST /dut/boot-mode`; reset, Control,
  evidence, ownership and operation semantics remain authoritative in the
  service/Device Core. Boot validation remains client-composed.
- After migrating every server consumer, removed MCP client/server paths for
  `set_boot_mode`, `capture_uart`, `wait_for_uart_pattern`, `run_boot_test`,
  `send_uart_command`, `get_recent_uart_log`, `get_debug_session` and
  `list_debug_sessions`, plus unused `_timed_workflow` and legacy-validation
  imports. Removed three positive legacy-client tests; updated catalog-dependent
  server/protocol/installed-launch tests. No compatibility aliases or service
  endpoints were added. Retired names/fields remain only in negative MCP tests.
- Preserved MCP 2.x/stdin-stdout transport, identity/discovery and per-request
  metadata, deterministic ordering, private 300,000 ms cache hints, complete
  structured results, cancellation/EOF and launcher source. No raw GPIO/serial,
  LLM/Debug Agent, automatic retries, MCP-owned lifecycle/timing or evidence
  truth was added. No Device Core/service API behavior changed.
- Test-first catalog migration initially produced **124 failed, 7 passed**.
  Basic registration exposed **45 failed, 86 passed**: the installed SDK ignores
  extra arguments and convenience-parses JSON-looking strings (`null`, `true`,
  `{}`, `[]`). That could silently accept retired fields or corrupt valid UART
  text/cursor strings. A narrow `MCPServer` subclass now validates original
  arguments with the SDK-generated Pydantic model (`strict`, extras forbidden)
  and invokes the registered async context-free handler without convenience
  parsing. Public schemas forbid extra properties. Missing/extra-argument
  errors are bounded structured `invalid_argument` results without input dumps;
  local diagnostics use the shared projector. This is argument adaptation only,
  not a second operation or service model.
- Focused tests verify all twelve client-method calls once, exact HTTP mappings,
  Monitor/Interact forms and outcomes/ranges, binary/text payloads and all five
  explicit endings, raw JSON-looking text/cursors, reset/boot, session/evidence
  cursors, release/reacquire projections, negative retired-tool/field calls,
  bounded structured errors and schema/catalog/cache behavior. Modern SDK
  in-memory tests cover argument preservation/rejection on the wire; installed
  real-stdio tests retain discovery, twelve-tool listing, unavailable-service
  errors and clean shutdown without a venv on PATH. HTTP remains mocked here;
  no actual-service/ASGI Slice 3 acceptance is claimed.
- Fresh validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

  | Command suffix | Result |
  |---|---|
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests/test_server.py apps/mcp_server/tests/test_protocol_integration.py --tb=line -r N` | 139 passed in 2.06 s after catalog/raw-argument fixes |
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py --tb=line` | Final focused run: 311 passed in 3.44 s, including additional modern wire regressions |
  | `uv run --frozen --offline ruff check .` | Passed |
  | `uv run --frozen --offline mypy` | Passed; 103 source files |
  | `uv run --frozen --offline pytest -q --tb=line` | 1,838 passed in 48.25 s |
  | `git diff --check` | Passed |

  Net test-count change from 1,709: 123 added server cases + nine modern wire
  cases − three removed legacy-client cases = 129.
- Complete diff, documentation links, source/reference inventory, exact catalog
  and thin-client checks passed. Seven files changed: server/client, their three
  test files, status and this history addition. Prior history and dated status
  evidence are preserved; hardware acceptance/checklist, Device Core, service,
  launcher, firmware and historical hardware evidence remain unchanged. No
  module/ownership/layer-direction change required architecture documentation
  or a Graphify update. No hardware/HIL, commit or push.
- Recorded Slice 2 complete in status. Overall MCP migration remains incomplete;
  Stage 8, Phase 1B and Phase 1 remain incomplete pending manufactured KiCad
  Rev-A physical/electrical validation. Historical EAGLE electrical gaps remain
  unresolved; legacy functional HIL permission is unchanged.

## MCP v2 Slice 1 — Service-Client Mappings and Error Projection — 2026-10-30

- Implemented only [MCP plan Slice 1](mcp_integration_plan.md#independently-testable-implementation-sequence)
  on `mcp/v2-service-client`, starting clean at merged `9c0e0f9` (PR #4).
  Added HTTP client support for all twelve planned operations, including
  MCP-facing `set_dut_boot_mode` calling unchanged `POST /dut/boot-mode`.
  `reset_dut` and underlying service/Device Core Control semantics are unchanged.
- Client request bodies retain exact base64 or text plus explicit line endings,
  duration/conditions modes, optional argument omission and opaque cursor strings.
  Shared core validators enforce bounds before dispatch without importing service
  schemas or transport implementations. Responses, operation outcomes/IDs,
  ranges, provenance, schema compatibility, omission counts and canonical errors
  pass through unchanged. HTTP 410 and bounded error context are preserved.
- Ordinary requests retain the 2-second timeout; Monitor/Interact use accepted
  bounds + 2 seconds transport grace; evidence uses `wait_s` + 2 seconds;
  release/reacquire use bodyless POSTs with the existing CLI's 65-second HTTP
  allowance. No retries, reconnect/polling loops, local lifecycle or evidence
  truth, service startup or hardware ownership were added. HTTP timeouts retain
  unknown-outcome wording, not rollback/non-dispatch guarantees.
- Malformed/non-object responses keep bounded protocol errors. New regression
  cases exposed that noncanonical service diagnostic detail could previously
  leak unbounded/control/invalid-Unicode text. The shared diagnostic projector
  now validates that peer detail already meets the canonical contract; invalid
  detail is rejected with a fixed protocol diagnostic, while valid service
  detail/truncation/context remain exact. This follows the plan's bounded-error
  contract; no API or semantic deviation was required.
- Kept the old public catalog and all registration/launch source unchanged.
  Temporary client consumers retained for Slice 2:

  | Retained client method | Remaining production consumer in `server.py` |
  |---|---|
  | `set_boot_mode` | Existing `set_boot_mode` tool handler; delegates to `set_dut_boot_mode` |
  | `capture_uart` | Existing `capture_uart` tool handler |
  | `wait_for_uart_pattern` | Existing `wait_for_uart_pattern` tool handler |
  | `run_boot_test` | Existing `run_boot_test` tool handler |
  | `send_uart_command` | Existing `send_uart_command` tool handler |
  | `get_recent_uart_log` | Existing `get_recent_uart_log` tool handler; delegates to `get_recent_logs` |
  | `get_debug_session` | Existing `get_debug_session` tool handler; delegates to `get_session` |
  | `list_debug_sessions` | Existing `list_debug_sessions` tool handler; delegates to `list_sessions` |

  Existing client/server/protocol tests also exercise those paths. Their removal
  is deferred until registration and dependent fixtures migrate in Slice 2;
  no service compatibility endpoint was added. Passing the pre-v2 catalog does
  not accept the complete MCP v2 migration.
- TDD evidence: initial client run **121 failed, 20 passed**, with failures on
  missing v2 methods; first implementation **141 passed**. Added direct
  no-implicit-LF coverage and regressions for non-sequence conditions and unsafe
  peer diagnostics: **4 failed, 151 passed** before correction; then **155
  passed in 0.24 s**. Tests cover all twelve routes/bodies/queries, optional
  defaults, path-safe encoded session IDs, explicit endings, finite operation
  and long-poll/mutation timeouts, cursor round trips, outcomes/compatibility,
  capability/policy/lifecycle/schema/backend/persistence errors, HTTP 410,
  unavailable service, malformed responses and single dispatch on failure.
- Fresh validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

  | Command suffix | Result |
  |---|---|
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests/test_service_client.py --tb=line` | 155 passed in 0.24 s |
  | `uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py --tb=line` | Final focused run: 182 passed in 2.40 s, including unchanged nine-tool catalog, modern metadata/cancellation/EOF, real installed stdio launch and CLI tests |
  | `uv run --frozen --offline ruff check .` | Passed |
  | `uv run --frozen --offline mypy` | Passed; 103 source files |
  | `uv run --frozen --offline pytest -q --tb=line` | 1,709 passed in 47.24 s |
  | `git diff --check` | Passed |

- Final diff, documentation links, retained-consumer inventory, unchanged
  registration/service/firmware/hardware and historical evidence preservation
  checks passed. Four files changed: client, its tests, status and this history
  addition. This is a localized client extension with no new module, shared core
  port or architectural ownership change; no architecture document or Graphify
  update was needed. No physical HIL/hardware access, commit or push.
- Recorded Slice 1 complete in status; overall MCP migration remains incomplete.
  Phase 1B, Stage 8 and Phase 1 remain incomplete pending manufactured KiCad
  Rev-A physical/electrical validation. Legacy EAGLE functional HIL permission
  does not close its historical UART electrical gap or accept KiCad hardware.

## MCP v2 Start Prerequisite and Contract Audit — 2026-10-30

- Documentation/design audit only, starting with a clean working tree on
  `main` at `2b7c89a0830c32da5ea9bbc293d8f4b6fc83e243`, matching `origin/main`.
  Independently confirmed pushed `refs/heads/main` with
  `rtk proxy env GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/leonahi/DUTchMate.git refs/heads/main`.
- **MCP start prerequisite disposition: Satisfied** under specification §4.1.
  Evidence for each prerequisite:

  | Prerequisite | Committed evidence and audit conclusion |
  |---|---|
  | Accepted Device Core/service/CLI software baseline | [Stage 8 software acceptance](#stage-8-software-acceptance-and-hardware-availability-audit--2026-10-26), accepted Basic v2 status/HIL, subsequent `6d0c1a8` control-generation and `14e6717` cleanup fixes plus their recorded full gates establish the baseline. `git diff --name-only 14e6717554e76444a6b9bc21dbf257a0e51d1efe..HEAD -- core apps tests uv.lock pyproject.toml` returned no changes. |
  | Available functional Enhanced HIL | [Retained v2 workflow results](../hardware/validation/phase1_enhanced_hil.md#continuous-session-and-boundedhuman-operations) from `20261027T114440Z-7db24eae`, [corrected explicit control-generation path](../hardware/validation/phase1_enhanced_hil.md#startup-and-explicit-ownership-lifecycle-passed) from `20261027T165848Z-b9a62f0b`, and [automatic USB reconnect pass](../hardware/validation/phase1_enhanced_hil.md#automatic-pico-2-usb-reconnect-hil-passed--2026-10-27) from `20261027T180121Z-9ea027ae` jointly support functional readiness. The [reconciliation](../hardware/validation/phase1_enhanced_hil.md#evidence-reconciliation-addendum--2026-10-28) accepts the combined workflow evidence; earlier failed actions/runs remain failed within their recorded scope. |

- Legacy EAGLE use is functional HIL only. No physical HIL rerun was needed.
  Its historical UART electrical/oscilloscope gap remains unresolved; KiCad
  source review remains source verification. Final Stage 8, Phase 1B and Phase 1
  acceptance still requires fresh manufactured KiCad Rev-A physical/electrical
  validation. This audit claims no MCP implementation or new hardware acceptance.
- Rewrote [the MCP integration plan](mcp_integration_plan.md) around actual
  `app.py` endpoints, `schemas.py` serializers, core validators/cursors and
  canonical errors. Defined twelve service-shaped tools, compact unchanged
  service results, explicit text endings/binary TX, operation/range/cursor
  preservation, read-only historical compatibility and release/reacquire.
  Removed capture/wait, schema-v1-only responses, implicit newline, `force`,
  `capture_active` and boot-test behavior as target requirements; retained a
  retirement inventory for obsolete source consumers. Boot validation remains
  client-composed from generic atomic operations.
- Source/dependency reality supports preserving the existing modern foundation:
  locked MCP `2.0.0`, protocol `2026-07-28`, `MCPServer`, tools-only stateless
  stdio, fixed cache policy and working CLI/entrypoint launch. Existing MCP
  tests mock obsolete endpoints, including absent `/dut/boot-test`, so those
  passes are not v2 adapter acceptance. The sequence now starts with v2 HTTP
  client mappings/tests, then catalog retirement, actual service/protocol
  integration, installed launch/boundary regressions and scoped host acceptance.
- Readiness/current task updated only in development status; MCP implementation
  remains not started. No extra normative document was needed: the Phase 1 v2
  specification already defines the required behavior. One focused Graphify
  query (`MCP service client monitor interact evidence`, budget 1600) located
  relevant layers; important findings were verified against actual source/tests.
  No structural change or Graphify update was made.
- Fresh non-physical verification command:
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen --offline pytest -q apps/mcp_server/tests apps/cli/tests/test_mcp.py apps/service/tests/test_monitor_endpoint.py apps/service/tests/test_uart_send_endpoint.py apps/service/tests/test_device_action_endpoints.py apps/service/tests/test_session_endpoints.py apps/service/tests/test_atomic_service_surface.py apps/service/tests/test_status_endpoint.py tests/unit/runtime/test_phase1_cli_acceptance.py --tb=line`:
  **75 passed in 3.31 s**. Covers existing MCP protocol/client/server/stdio,
  launcher and service request/result schemas, v2 sessions and Basic/Enhanced
  CLI acceptance with fake physical ports. This is software verification, not
  fresh physical HIL or acceptance of the proposed MCP catalog.
- Complete diff inspected. Three Markdown files changed; prior history and all
  dated status validation evidence preserved byte-for-byte. Local links/anchors,
  catalog-to-source mappings, obsolete-target checks, evidence-boundary and
  documentation-only scope checks plus `git diff --check` passed. No production
  code, tests, firmware, hardware design or historical validation files changed;
  no full-suite/CAD/physical rerun, hardware access, commit or push.

## Functional Enhanced HIL and MCP Sequencing Policy Updated — 2026-10-30

- Adopted the agreed policy in
  [Phase 1 specification §4.1](phase1_implementation_spec.md#41-software-sequencing-and-hardware-acceptance-boundaries).
  The legacy EAGLE Rev-A board may serve as a functional Enhanced HIL/development
  fixture while manufactured KiCad Rev-A boards are pending. This supersedes
  earlier prospective wording that no further prototype testing was planned;
  all earlier evidence and unresolved electrical gaps retain their scope.
- MCP v2 migration may begin after the required Device Core/service/CLI
  software baseline is accepted and functional Enhanced HIL is available.
  Manufacturing lead time alone does not block it. MCP remains a thin client
  over authoritative service/Device Core behavior. No MCP implementation or
  new baseline acceptance is claimed by this documentation change.
- Retained the separate manufactured KiCad Rev-A physical/electrical gate for
  final Stage 8, Phase 1B and Phase 1 completion. EAGLE functional HIL neither
  closes historical EAGLE UART electrical/oscilloscope gaps nor accepts either
  board electrically/physically; it cannot validate KiCad-specific features.
  KiCad source review remains design-source verification only.
- Reconciled stale current-status branch/uncommitted wording with merged
  `main`/`origin/main` at `f1c61d1` (PR #3; corrections at `a837f4b`). Updated the
  migration plan and MCP reference header to point to the normative policy,
  and replaced the KiCad README's blanket prototype-testing restriction with
  a concise reference. Earlier dated history and validation evidence were not
  rewritten.
- Documentation verification: complete diff inspected; exactly six Markdown
  documentation/specification files changed. Scope/preservation checks confirm
  all other tracked files unchanged, earlier history byte-for-byte intact, and
  dated physical HIL/source/test evidence in status preserved. Local link/anchor
  and policy-consistency checks plus `git diff --check` passed. No production
  code, firmware, hardware design, tests, or historical validation files changed;
  no hardware access, software-suite/CAD rerun, commit or push.

## Legacy EAGLE Validation Gap Retained Without Further Testing — 2026-10-30

- Recorded that the historical EAGLE prototype's UART signal-integrity/
  oscilloscope evidence gap remains unresolved. No further physical validation
  of that prototype is planned; the missing evidence is not marked passed.
- Assigned equivalent UART electrical/oscilloscope evidence to the fresh
  manufactured KiCad Rev-A validation campaign, together with the other
  applicable categories already in the KiCad README. Historical EAGLE physical
  acceptance is not transferred to the corrected board. Phase 1B/Stage 8/Phase 1
  remain incomplete until required current-board physical validation is accepted;
  specifications and acceptance criteria were not changed.
- Documentation only: reconciled development-status sections, added a small
  README evidence-boundary clarification and this dated entry. No hardware was
  accessed and no new physical evidence was created. Earlier history and
  validation records remain unchanged. Scope/hash preservation, local links/
  anchors and `git diff --check` passed; no full-suite rerun or commit.

## KiCad Rev-A Manufactured-Board Validation Sequence Recorded — 2026-10-30

- Recorded the agreed lifecycle after completed KiCad Rev-A schematic/source
  review: PCB layout/routing, DFM, fabrication preparation, Gerber review and
  manufacturing submission are manual hardware-designer work outside the
  coding-agent workflow. No further repository-driven PCB review is planned
  before fabrication, and PCB/DFM is not a repository acceptance gate.
- Recorded that the next formal hardware-validation slice for the new KiCad
  design begins only when manufactured KiCad Rev-A PCBs are physically
  available. It will repeat/adapt the historical Rev-A physical-validation
  categories against the corrected circuit. The category inventory and
  connector/component/pull-up adaptations live in the
  [KiCad README](../hardware/pcb/debug-helper/rev-a/README.md#validation-lifecycle-and-evidence-boundaries).
- This workflow decision replaces earlier prospective agent-task wording about
  PCB/DFM review. Earlier source-review/test results and historical EAGLE
  physical evidence remain intact; none is transferred into acceptance of the
  manufactured KiCad board. Phase 1 criteria/status and the separate legacy
  prototype UART oscilloscope evidence gap were not changed.
- Documentation only: no hardware access, new physical validation, fabricated
  results or premature validation report. Changed only development status,
  this history entry and the KiCad README, preserving the existing working
  tree changes. Scope/hash preservation, documentation links and
  `git diff --check` passed; no software-suite or CAD-check rerun, commit or push.

## Rev-A Manual KiCad Corrections Verified — 2026-10-29

- Reviewed the current working Rev-A KiCad design on
  `hardware/kicad-schematic-review-20261028`, source baseline `e8ce97c`.
  Inspected and snapshotted the existing schematic, PCB, project and symbol
  library diffs before editing. Preserved the operator's manual circuit and
  placement/routing corrections; no commit or push performed.
- Verified actual netlist connections for U3 TMUX2819DSGR: SA=DUT_VIO,
  D=R10 input, SB unused, EN/VDD=+3.3V, SEL/NC/GND/EP=GND, and C16=100 nF.
  TI datasheet pin functions and truth table confirm SA selection with power
  present and powered-off protection without firmware GPIO control. Verified
  R10/R11=47 kΩ, C7=10 nF, GNDA return and GP28/ADC2 mapping.
- Verified R13=10 kΩ to DUT_VIO after RN5A, R14–R17=10 kΩ data pull-downs,
  R6–R9=4.7 kΩ DUT_VIO OE pull-ups, R1–R5/R12=4.7 kΩ enable pull-downs,
  RN3/RN4=180 Ω, channel directions, retained helper signal/OE labels and the
  authoritative single 2×8 J1 mapping. No event pull-ups were added; the
  DUT/developer supplies valid event levels and any required open-drain pull-up.
  U1 remains SN74LV4T125; controls must stay within DUT_VIO, including when
  released into an external pull-up. Older RP2350 A2 modules remain supported.
- Confirmed U2/U5 power/signal/OE types, U7/U8 open-collector/drain types,
  intentional unused pins, Pico 2 identity/metadata and resolved symbol
  references. Added only the missing reusable TMUX description/datasheet
  metadata, keeping its embedded definition synchronized. Existing valid
  symbol graphics and component metadata were retained.
- Initial ERC: 1 error, no warnings, for undeclared external DUT_VIO power.
  Added a standard PWR_FLAG to declare the J1-supplied reference. Final KiCad
  10.0.5 ERC (`sch erc --severity-all --exit-code-violations`): **0 errors,
  1 warning**, exit 5 because warnings are included. The warning connects U3
  SA (bidirectional analog terminal) to the declared external power source;
  that is the intended sense input, not conflicting digital drivers. Reviewed
  the warning without exclusions or severity changes. No other ERC messages
  remain; existing ignored categories are unchanged.
- Read-only source checks: **309 assertions passed**; all **47 electrical
  component values and numbered PCB pad nets** match the schematic. All
  electrical pin/net memberships remain identical to the pre-cleanup netlist.
  Symbol references resolve, project-library pin definitions match their
  embedded copies, and the PCB/project bytes remain as supplied for review.
  Source-check scripts and ERC/netlist exports were kept outside the repository.
- GP28 ADC sensing is not implemented in helper firmware: no ADC channel setup
  or explicit GP28 digital-input-buffer configuration was found in its source,
  overlay or configuration. No firmware change was made or working ADC-mode
  buffer-disable setting claimed. Future sensing must disable that buffer.
- Updated the KiCad README with design authority, source/library ownership,
  circuit/connector requirements and validation boundaries. Added only a
  current-source pointer to the historical EAGLE record; its original details
  and every hardware validation record remain unchanged. Updated current
  status separately; existing prototype acceptance and HIL evidence were not
  reinterpreted as validation of the corrected KiCad board.
- Fresh offline verification using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen --offline pytest -q tests/hardware/rp2350_debug_helper --tb=line`:
  **97 passed in 19.47 s**; full `uv run --frozen --offline pytest -q --tb=line`:
  **1,569 passed in 49.22 s**. Ruff passed; mypy passed/103 source files;
  `uv lock --check --offline` passed/66 packages. Documentation link/scope,
  preservation and `git diff --check` checks passed. No schematic fabrication
  blocker was identified within the agreed correction scope; source checks
  support proceeding to PCB/DFM review, not fabrication or hardware acceptance.

## Rev A 10 kΩ Pull-Up Documentation Blocker Closed — 2026-10-28

- Worked on existing `validation/phase1b-revision-a` at `4c87383`, preserving
  all prior unstaged documentation. Applied the operator-confirmed final
  as-built facts: **10 kΩ axial leaded resistor**, approximately **9.9 kΩ**
  measured, connected through jumper wire exactly as **DUT_VIO (J3 pin 8)
  ↔ 10 kΩ ↔ DUT_UART_TX (J1 pin 4)**. The old **11.88 kΩ** component was
  incorrect and replaced; its recorded readings were not reinterpreted.
- Fresh XML checks of the accepted EAGLE schematic and board confirm
  J1 pin 4/R16 pad 2 on DUT_UART_TX, R16 pad 3/U1.B2 (pin 1) on UART_TX,
  and J3 pin 8 on VCC/DUT_VIO. Together with the operator-confirmed endpoints,
  this establishes the Rev A **before-R16** rework without additional physical
  checks. Future KiCad **after-R16** placement remains outside the repository
  and outside Rev A acceptance evidence.
- Marked physical blocker #1 **Satisfied**. Only prototype UART electrical
  signal-integrity/oscilloscope evidence remains; Phase 1B/Stage 8/Phase 1
  remain incomplete. Added explicit superseding closure notes while retaining
  every earlier physical/HIL/history section byte-for-byte. No unreported
  jumper-contact or pad-to-input meter result was invented.
- Four permitted documentation files only; no hardware access, scope work,
  source/test/firmware or PCB design changes. All changes unstaged/uncommitted.
- Fresh offline gate using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen --offline pytest -q --tb=line`: **1,569 passed in 46.68 s**;
  Ruff passed; mypy passed/103 source files; lock check passed/66 packages.
  XML mapping, closure links/anchors, branch/four-file scope, empty staging and
  `git diff --check` passed. Every prior physical/HIL/history section and dated
  status validation record remains byte-for-byte outside new closure additions;
  all 1,281 other snapshotted files unchanged. Complete diff retained for review;
  no commit or push performed.

## Revision A DUT_VIO Attachment Identified As Jumper Wire — 2026-10-28

- Operator identifies a jumper wire between the resistor supply end and J3
  pin 8. Adapted the requested power-off direct check to the installed
  resistor lead→jumper/contacts→J3 pin 8 path; no numeric result supplied yet.
  Earlier 9.45 kOhm remains J3 pin 8→J1 pin 4, not this direct path.

## Revision A 9.45 kOhm Probe Locations Clarified — 2026-10-28

- In reply to the requested supply-contact check, operator reported **9.45 kOhm**.
  Physical checks were paused to identify the probe locations before treating
  this as a connection result. Operator then explicitly identified the probes
  as **J3 pin 8 and J1 pin 4**, not the resistor supply lead and J3 pin 8.
- Retained 9.45 kOhm as the actual connector-to-connector installed-circuit
  reading. It is not a measured failed supply contact; no fault or explanation
  of its difference from the isolated value is inferred. The four requested
  direct endpoint/node/input results remain missing and blocker #1 stays open.
- Asked only whether two separate supply-contact surfaces can be identified/
  accessed with the resistor installed, keeping power removed. No further
  probing was requested while that identification remains unclear. No powered
  or scope work, firmware, software, test or PCB design change occurred.

## Revision A Lead Baseline And Replacement Connector Locations Reported — 2026-10-28

- Operator reports **shorted probes 0.1 Ohm** and identifies the replacement
  as connected between **DUT_VIO/J3 pin 8** and **DUT_UART_TX/J1 pin 4**.
  The resistor was unplugged at the J3 pin 8 end for a reported **9.90 kOhm**
  reading, retained as an isolated value measurement rather than an endpoint
  connection-resistance result.
- The 22.4 Ohm reading across R16 is distinct from the 0.1 Ohm lead baseline.
  Direct endpoint/node/input readings remain missing. Requested only the next
  supply-end connection check, with the resistor restored, all power removed
  and both probes on the supply-side connection. No endpoint pass or full
  topology closure was inferred; blocker #1 stays open.

## Revision A A/B Definitions And R16 Reading Labels Clarified — 2026-10-28

- Operator clarified/corrected the existing measurements as **A→R16 pad 2
  9.91 kOhm** and **A→R16 pad 3 9.94 kOhm**. The original duplicated
  A→R16 9.94 kOhm report is preserved in its earlier entry and raw-reading
  table; no inferred pad assignment or silent correction was made.
- Operator asked for the A/B definitions again. Restated A as the resistor
  supply lead unplugged for the isolated 9.9 kOhm measurement, and B as the
  other lead intended for DUT TX before R16. Requested power-off direct checks
  one step at a time, starting with shorted probes and A→DUT_VIO.
  No direct endpoint/node/input reading was supplied; blocker #1 stayed open.

## Revision A Replacement Isolation And Partial Resistance Results — 2026-10-28

- Operator explicitly confirmed the replacement's **own supply-side lead was
  unplugged** for the **9.9 kOhm** reading. This confirms the isolated nominal
  10 kOhm value requirement; old 11.88 kOhm remains the replaced incorrect part.
- In reply to power-off installed-connection instructions, operator reported
  **A→B 9.91 kOhm**, **A→R16 UART-TX 9.94 kOhm** twice with identical labels,
  and **R16 pad 2→pad 3 22.4 Ohm**. All readings are retained exactly; the two
  A→R16 entries are not assigned to different pads by inference.
- No shorted-probe or direct A→DUT_VIO, B→J1 pin 4, J1 pin 4→R16 pad 2,
  or R16 pad 3→U1.B2 result was supplied. Requested clarification of readings
  already taken, with further probing paused for the ambiguous labels.
  Blocker #1 remains open pending topology proof; the UART electrical
  signal-integrity blocker remains open. No powered/scope run or source,
  firmware, test or PCB design change occurred.

## Revision A Replacement Meter Display And Probe Access Confirmed — 2026-10-28

- Operator confirmed all three requested R16/receiver probe points accessible
  and replacement display **9.9 kOhm**, stating “DUT_VIO was removed for the
  measurement” and everything else remained the same. The unchanged setup
  retains the previously identified Themisto TH-M100 and removed power sources.
- Asked whether the resistor supply-side lead itself was unplugged or only
  the board supply wire, rather than inferring isolated measurement. Requested
  actual numeric readings for shorted probes, both replacement endpoints,
  DUT-TX-node/R16-pad and R16-pad/U1.B2 connectivity, and across R16.
  No endpoint or R16 result was reported in this reply; blocker #1 remains open.
- Earlier access-limited and 11.88 kOhm records remain unchanged. The former
  access limit is superseded by this report; it is not retrospectively treated
  as a successful topology measurement. No powered/oscilloscope run or source,
  firmware, test or PCB design change occurred.

## Revision A Pull-Up Replacement Report And Final-Check Preparation — 2026-10-28

- On the existing `validation/phase1b-revision-a` branch at `4c87383`, the
  operator explicitly identified the old 11.88 kOhm resistor as incorrect,
  replaced by intended nominal 10 kOhm, measured approximately **9.9 kOhm**
  with all power removed. The old reading remains unchanged and is excluded
  from final-part acceptance evidence.
- Added a separate final-check record for the replacement. No installed
  endpoint, R16 relationship or absence of a bridge was inferred from the
  reported replacement value or expected diagram. Asked whether the previously
  inaccessible R16 pads/receiver net can now be reached safely, and requested
  the replacement measurement's isolation method, meter and displayed reading.
- Preserved all prior unstaged physical/HIL/history sections unchanged.
  Follow-up snapshot covers 1,285 local files, including those existing pending
  records. Final checks remain unestablished; blocker #1 and the UART electrical
  signal-integrity blocker remain open. No scope measurements, product code,
  tests, firmware or PCB design changed. Changes remain unstaged/uncommitted.
- Fresh follow-up documentation checks passed: all pre-follow-up physical/HIL/
  history sections preserved byte-for-byte outside new additions; all 1,281
  other snapshot files unchanged. Branch/four-file scope, empty staging,
  new local links/anchors and `git diff --check` passed. No physical pass is
  inferred; actual endpoint/R16 outcomes remain unestablished.

## Revision A Pull-Up Check Stopped: Value And Access Not Verified — 2026-10-28

- Operator confirmed all power connections removed and reported **11.88 kOhm**
  measured directly across the external resistor after unplugging its
  **DUT-TX-side lead**, using the previously identified Themisto TH-M100.
  This is 18.8% above 10 kOhm; no marking/tolerance, range, calibration or
  independent reference establishes an explanation. The reading is preserved
  exactly and is not accepted as confirmation of nominal 10 kOhm.
- The earlier 0.0 V readings and operator identification of DUT_VIO as supply
  remain applicable. No endpoint-continuity readings were supplied. Operator
  reports no safe access to R16 pads or an alternative receiver-net point.
  R16's presence between the bias node and receiver input was not physically
  established. Source-file mapping was not substituted for that missing result.
- Applied the requested stop rule: blocker #1 remains required/open; no further
  physical checks or oscilloscope/UART signal-integrity work followed. Both
  physical blockers and Phase 1B/Stage 8/Phase 1 incompleteness remain. No
  resistor relocation/replacement, soldering, firmware, product code, tests or
  hardware design changed. Restoration of the temporary disconnected lead has
  not been reported and is not assumed.
- Updated only the four permitted documentation files, unstaged/uncommitted.
  Earlier historical entries remain intact. The preparation software gate
  recorded below remains the only software run for this documentation slice;
  no source/test changes followed it. Fresh documentation checks passed:
  baseline historical sections byte-for-byte outside the additions; all 1,281
  other snapshot files unchanged; exactly four allowed documentation files;
  staging empty; new local links/anchors and `git diff --check` passed.
  Complete diff retained for review.

## Revision A Pull-Up Initial Operator Meter Report — 2026-10-28

- Operator reported both requested DC readings as **0.0 V**: external pull-up
  supply node to GND and DUT_VIO to GND. Meter identified as **Themisto TH-M100**;
  exact measurement time, range and calibration status were not supplied.
- Operator identified DUT_VIO as the pull-up supply and confirmed the external
  resistor is accessible/removable without soldering. R16 UART-TX pads could
  not be accessed. No resistor-value or endpoint-continuity reading was reported.
- Requested an isolated resistor reading and explicit power-disconnection
  confirmation; asked whether U1.B2 or an exposed receiver-net point is safely
  accessible for an alternative R16 check. No alternative access was presumed,
  no hardware change was requested and blocker #1 remained open. The initial
  voltage readings were recorded without inferring resistance, wiring or placement.

## Revision A Pull-Up Check Preparation And Interpretation Correction — 2026-10-28

- Created `validation/phase1b-revision-a` from clean updated main
  `4c87383038377401da785fdf22a5527031e8f97c`, verified against pushed main by
  read-only HTTPS lookup. No commit, staging or push was performed.
- The operator corrected the as-built interpretation: accepted Rev A has an
  external 10 kOhm pull-up from 3.3 V to DUT TX before R16; future KiCad intent
  moves it after R16 and is outside the repository. Added an explicit note
  separating these configurations without rewriting historical measurements
  or treating this declaration as newly measured evidence.
- Source inspection of the preserved EAGLE schematic/board identifies the
  candidate probe nodes: J1 pin 4/R16 pad 2 is DUT_UART_TX; R16 pad 3/U1 pin 1
  (B2) is UART_TX. This establishes source references only. A continuity beep
  cannot establish which side of a nominal 22 Ohm resistor carries the rework;
  the prepared record calls for numeric readings and shorted-probe comparison.
- Requested operator confirmation of disconnected supplies/accessories,
  residual DC voltages, meter identity, physical rail source and accessible
  terminals before resistance checks. No physical readings have been supplied;
  blocker #1 was kept open. The separate UART electrical signal-integrity
  blocker and overall Phase 1B incompleteness are unchanged.
- Preservation snapshot captured 1,285 local validation/evidence/status files.
  Fresh offline preparation gate with
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen --offline pytest -q --tb=line`: **1,569 passed in 47.03 s**;
  Ruff passed; mypy passed/103 files; lock passed/66 packages.
- Preservation and documentation checks passed: original history/validation
  content is byte-for-byte outside new sections; all 1,281 other snapshot files
  unchanged; four permitted documentation files only; staging empty; new local
  links/anchors and `git diff --check` passed. Physical verification remains
  pending and no bench criterion was marked passed. Changes remain unstaged
  and uncommitted. No firmware,
  product software, tests, hardware design, runtime/serial access, oscilloscope
  measurement or physical rework was performed by the agent.

## Phase 1B Evidence Reconciliation Audit — 2026-10-28

- Started with a clean tracked tree at `9ff33c10858d5e040688e895b9d201cae70bcf71`,
  the successful automatic USB reconnect HIL documentation commit. Independent
  HTTPS `git ls-remote` matched the pushed branch; initial sandbox DNS and then
  SSH authentication failed, without changing refs or the baseline.
- Compared implementation-specification §§11/34/35, GPIO semantics and normative
  project-context/architecture boundaries with the Revision A, Enhanced HIL,
  ring-buffer, firmware and retained development records. Added a dated
  item-by-item reconciliation; no acceptance criterion or historical run was
  rewritten. Earlier broad gap lists remain intact as historical dispositions.
- Rechecked source consistency: all 17 table/schematic/board Pico assignments,
  five logic-device references and 14 ordered firmware GPIO assignments plus
  UART0/460800 agree. This does not claim populated-part or physical continuity
  inspection. Snapshot of 1,285 local validation/evidence/status files preceded
  edits and validation.
- Reconciliation found two unresolved acceptance criteria: accepted/as-built
  10 kOhm helper-input correction consistency, and prototype UART electrical
  signal-integrity measurements. Existing digital hot-plug evidence demonstrates
  the temporary bias; it does not establish the current installed after-R16
  configuration or analog waveform margins. No new board, cable matrix or
  repeat of accepted workflows/32 KiB stress was inferred as a requirement.
- Recorded leakage, loaded isolation, settled supply sequencing, voltage-level
  and control-safe-state measurements satisfy their bounded §34 requirements.
  Independent parts/full-BOM inspection, exhaustive continuity, wider cable/
  passive qualification, calibrated absolute leakage, transient matrices, ESD
  characterization and Phase 5 EVENT capture were classified non-blocking.
  No missing qualification measurement was converted into a physical pass.
- Accepted current Enhanced runs jointly support the §34 workflow criteria
  and shared §35 behavioral criteria, including corrected explicit/automatic
  ownership paths. Phase 1A stays accepted; the §35 prerequisite that Phase 1B
  be done remains unmet. Phase 1B/Stage 8/Phase 1 were not marked complete.
- Fresh offline validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen --offline pytest -q --tb=line`: **1,569 passed in 48.31 s**;
  `uv run --frozen --offline ruff check .`: passed;
  `uv run --frozen --offline mypy`: passed/103 source files;
  `uv lock --check --offline`: passed/66 packages.
- Preservation check passed: removing only the newly inserted addenda reproduces
  original history and both physical/HIL records byte-for-byte; all 1,281 other
  snapshotted files are unchanged. Exactly four allowed documentation files
  changed; staging is empty. Reconciliation links/anchors and final
  `git diff --check` passed. No Graphify update was needed for this documentation
  audit. Complete diff retained separately for review.
  No hardware access, service startup, product code, tests, firmware, hardware
  design or normative criteria changed. Four documentation files only; left
  unstaged and uncommitted for review.

## Automatic-Only Enhanced Pico 2 USB Reconnect HIL — 2026-10-27

- Ran from clean `fix/enhanced-terminal-read-cleanup` at
  `14e6717554e76444a6b9bc21dbf257a0e51d1efe`, verified against its freshly
  fetched pushed branch. Scope was startup plus one automatic Pico 2 USB
  reconnect. No product patch, firmware change, manual GPIO configuration,
  release/reacquire, retry or timeout enlargement occurred during HIL.
- Same accepted normal helper/460800 DUT reference pair and retained wiring;
  source UF2 hashes matched the previously identified flashes, without new
  flash/readback. USB `2E8A:000A`, serial `FA63A4D787572B33`, remained at
  `/dev/cu.usbmodem1401`. A separate working directory copied the accepted
  Enhanced config byte-for-byte, kept 5.0 s timeout and Profile digest
  `941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`.
  Original Basic config and all earlier evidence remained untouched.
- Normal pre-start gate using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen pytest -q --tb=line` **1,569 passed in 47.60 s**, finished
  18:00:02.239505 UTC; Ruff passed; mypy passed/103 source files; offline lock
  passed/66 packages; architecture included; diff/clean checks passed. No tests
  or other DUTchMate runtime/store ran while the physical service was active.
- One CLI start at 18:01:19.880597–18:01:21.666191 UTC created sole service
  PID 5775 and session `20261027T180121Z-9ea027ae`. Normal helper identity,
  CTRL1/CTRL0 configuration **1/3, 4/5**, 32-KiB telemetry and single startup
  reset **6/8** passed. Exact NUL + 62-byte normal DUT boot persisted at
  **7, 9..14** before the USB trial; no bounded observation was invoked.
- After passive HTTP/native observation was armed, the operator confirmed
  unplugging/replugging only Pico 2 USB, retaining Pico 1 power and all other
  wiring. Native **100** preserves `unexpected_disconnect`,
  `error=Enhanced serial read failed`; **101** starts reconnect, `timeout_s=5.0`.
  Replacement segment 1 **102** precedes CTRL1 **103/104**, CTRL0 **105/106**,
  then `reconnect_succeeded` **107**. Fresh raw ACKs are **3019850/3032034 us**;
  status exposes those timestamps, configured controls and fresh 18:02:52 UTC
  acceptance metadata. Profile and stable helper identity remain unchanged.
- Resumed telemetry **108** starts at relative timestamp 0. The single immediate
  reset **109/111** returned success/HTTP 200, raw timestamp **3183925 us**.
  Dispatch 18:02:52.280368 UTC was **0.379 ms** after the first connected status
  response. Exact NUL + normal DUT boot resumed at **110, 112..116**.
  Required ordering is **100 → 101 → 102 → 104 → 106 → 107 → 111**.
- Fresh RP2350 origins are **188867368/3001478 us**; same session, two segments,
  one unexpected observation gap. Observer first saw reconnecting/absent node
  18:02:47.764736 UTC; present node 18:02:49.743969 UTC; segment published by
  18:02:52.222481 UTC; connected 18:02:52.279988 UTC. Observed reconnect span
  **4.515240 s**, conservative prior-poll request-to-connected upper bound
  **4.579836 s < 5.0 s**. These are host observation bounds, not contact timing.
- Positive old cleanup is established through the reviewed production path:
  old close must verify retained serial `is_open is False` and released transport
  serial reference before the coordinator opens replacement. The same read error
  may reappear in the close waiter only under those checks. No cleanup fault or
  replacement close symptom occurred; original bounded read-failure evidence
  remains at 100 and in public retrieval. Raw exception identity/cause and
  private close flags are not serialized by HIL; their guarantee is the enforced
  code path plus pre-start installed-transport regressions, recorded explicitly
  in cleanup confirmation artifacts rather than presented as direct flag samples.
- Public session/detail, logs/status APIs and CLI session/logs/status retrieval
  passed. Saved startup cursor retrieved contiguous **6..137 / 132** records in
  two pages, with native/public record-type and exact RX-base64 correspondence.
  No second runtime/store was constructed for reconciliation.
- CLI stop 18:03:20.280053–18:03:20.397463 UTC completed with application
  shutdown complete, no ERROR/traceback, native **completed/service_shutdown**,
  ended 18:03:20 UTC. PID/file/listener/serial ownership were verified absent.
  Final native **0..144 / 145** records reconcile **126 RX bytes / 13 RX records**,
  six successful control pairs, 115 ambient telemetry records (86/29 by segment),
  two closed segments/one gap, no UART sends/bounded operations/pending attempts.
  Raw SHA-256 `9fc5ffce82472defa7adb38f69ed3306894732766fd911956b8541960228fa5d`;
  reported buffer loss zero/high-water at most 62, scoped to helper RX ring.
- All 463 earlier session/config hashes, including failed 303/304 and 739/740,
  remain unchanged. Full local evidence is under
  `.dutchmate/hil/enhanced-usb-reconnect-20261027T175902Z/`: baseline/preflight,
  gate, CLI/API/cursor, passive observer/timing, ordering and cleanup proof,
  service log/shutdown, final native/hash manifest and reconciliation.
- The current Enhanced unexpected USB reconnect criterion passed. The previous
  explicit handoff/control pass is reused; Monitor, Interact, follow, console,
  ring-buffer stress, Revision A measurements, Basic HIL and MCP were not
  repeated. Prior accepted evidence remains applicable within its limits.
  Remaining §34/Revision A parts/continuity/adopted-correction, analog UART/
  cable/passive, leakage/transient/isolation and ESD gaps keep Phase 1B/Stage 8/
  Phase 1 incomplete; Phase 1A remains accepted. Only Enhanced HIL report,
  development status and history changed, unstaged/uncommitted; final diff check
  passed. No prior failed/passing HIL record was rewritten.

## Enhanced Terminal Read Error Versus Physical Cleanup — 2026-10-27

- Created `fix/enhanced-terminal-read-cleanup` from independently fetched latest
  pushed `fix/enhanced-reacquire-control-config` at HIL-documentation commit
  `df8e7a6b45a5a92d8e1a545c04d893c8e87df34d`. The working tree was clean.
  All work remains unstaged/uncommitted. No hardware access, firmware, Revision A
  or MCP work occurred; the physically passed explicit handoff fix was not edited.
- Traced recorder `close_current_source_for_reconnect`, `EnhancedAsyncHost.close`,
  adapter close/drain and concrete `_OwnedStreamReader` into installed Python
  3.10.19 asyncio, pyserial 3.5 and pyserial-asyncio 0.6. A focused Graphify
  `_OwnedStreamReader` explanation was verified against actual source/callers.
  No public port, cross-layer ownership or module responsibility changed, so no
  structural graph refresh or architecture rewrite was needed.
- Installed `SerialTransport._read_ready` passes a serial read exception into
  `_close`; `_call_connection_lost` calls `StreamReaderProtocol.connection_lost`
  before closing its serial resource and clearing the serial reference. Asyncio
  puts that same exception object into both reader state and the close waiter.
  Thus `wait_closed()` raises the already-known read failure even after the
  physical close succeeded. Conversely, protocol waiter success happens before
  resource close and cannot alone establish cleanup certainty if that close
  subsequently fails. `is_closing()` means closing or closed, not confirmed close.
- The preserved HIL log has the read-error/close-waiter traceback and no separate
  connection-lost callback exception. It did not record in-run serial-open or
  released-reference observations, so no retrospective physical-close certainty
  is asserted for that failed run. The installed behavior and hardware-free
  reproduction establish the misclassification mechanism; future closes now
  require positive observations rather than assuming a result from that trace.
- Changed only the concrete Enhanced stream production boundary: retain its
  original serial resource and first observed read exception. A failing close
  waiter is accepted as completed cleanup only when its exception is that exact
  read object, serial `is_open` is precisely false, and transport serial info is
  None. Normal waiter success also requires physical confirmation. A distinct
  exception, open/unknown resource, retained transport reference or failed
  inspection remains a close failure. Existing adapter/host/coordinator paths
  retain `cleanup_unconfirmed`, stop replacement opening and block ownership.
- Original backend terminal error and raw cause are retained; no exception-class
  or message-based suppression was added. The existing shielded shared close
  task remains the sole close operation across concurrent/repeated close calls.
  No reconnect timeout, Basic behavior, Profile reapplication or recorder/
  coordinator arbitration code changed. Reconnect semantics now document the
  concrete confirmation rule and the distinction from primary transport error.
- Added a shared test-only pipe-backed serial resource beneath real installed
  `SerialTransport`, `StreamReaderProtocol` and `StreamWriter`, production adapter,
  service host, runtime, recorder and persistent journal. No fake serial device
  path is opened. Initial RED: **5 failed / 7 passed in 0.40 s**; confirmed
  physical closure still yielded HIL-matching `cleanup_unconfirmed`, while three
  normal-waiter/incomplete-close cases incorrectly returned success.
- Four service cases cover confirmed, genuinely failed, incomplete and unknown
  cleanup. Confirmed cleanup alone permits fresh segment → immutable Profile
  CTRL1/CTRL0 attempts/ACKs → `reconnect_succeeded`, with raw ACKs 2001/2002 and
  a successful reset. The other cases open no replacement, retain the original
  read error/cause, expose `cleanup_unconfirmed`, and retain shutdown failure.
  Repeated runtime shutdown/adapter close executes each serial close once.
- Ten concrete-boundary cases include the same modes, normal-waiter failure,
  same-class/same-message but distinct secondary exception, still-owned transport
  and inspection failure. Guard mutation checks failed as expected: removing
  transport-release proof produced **2 failures/0.06 s**; removing exact error
  identity produced **1 failure/0.05 s**. Both guards were restored.
- Existing stream fakes now model resource closure/release. A broader run exposed
  the old `test_enhanced_failed_open_keeps_primary_error_and_cleanup_certainty`
  and `test_enhanced_transport_inspection_failure_still_confirms_cleanup`
  expectations that protocol waiter success alone confirmed a missing or
  uninspectable resource. Those tests now preserve the primary open error and
  require cleanup uncertainty; the latter was renamed accordingly. This is
  stricter fail-closed behavior; existing Basic expectations were not changed.
- Focused GREEN: **40 passed in 0.49 s**, including all 14 new cases and concrete
  I/O/failed-open regressions. Relevant Enhanced/backends/reconnect/ownership/
  runtime/recorder/GPIO/protocol/service/CLI/architecture gate:
  **925 passed in 17.79 s**. Full final gate using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen pytest -q --tb=line` **1,569 passed in 47.42 s**;
  Ruff passed; mypy passed/103 source files; offline lock passed/66 packages;
  final `git diff --check` passed. No required check remains failing.
- Failed HIL report and all 463 existing session/config file hashes, including
  `20261027T165848Z-b9a62f0b` 303/304 and earlier failed 739/740, remain unchanged.
  Explicit Enhanced handoff/control remains physically passed. The automatic
  USB criterion is still physically unvalidated after this software correction;
  Phase 1A remains accepted and Phase 1B/Stage 8/Phase 1 remain incomplete.

## Focused Enhanced Physical HIL: Explicit Pass, Automatic Cleanup Fault — 2026-10-27

- Worked from clean `fix/enhanced-reacquire-control-config` at
  `6d0c1a87b8867d6ea0741b90a9e6d90cb9fc7ce8`, verified against the freshly
  fetched pushed branch. The reviewed software fix was already committed/pushed;
  no product source or firmware was changed during this HIL. Scope was startup,
  explicit ownership handoff/immediate reset and one automatic Pico 2 USB trial.
- Reused the previously identified normal helper/460800 DUT reference flashes,
  confirmed wiring/GP3 state and accepted physical evidence. Retained UF2 hashes
  matched; no new flash/readback occurred. USB `2E8A:000A`, serial
  `FA63A4D787572B33`, matched `/dev/cu.usbmodem1401`. Separate HIL working
  config copied the prior Enhanced profile byte-for-byte, retained 5.0 s timeout,
  CTRL0/RUN and CTRL1/GP2 mappings, digest
  `941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`.
- Fresh normal software gate, using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`, finished before
  physical startup: `uv run --frozen pytest -q --tb=line`
  **1,555 passed in 46.31 s**; Ruff passed; mypy passed/103 source files;
  offline lock check passed/66 packages; architecture included; diff/clean checks
  passed. No tests or second DUTchMate runtime/store ran while the service lived.
- CLI start at 16:58:47–49 UTC created sole service PID 3559 and native-v2
  session `20261027T165848Z-b9a62f0b`. Startup CTRL1/CTRL0 attempts/results
  **1/3, 4/5** preceded single successful 100 ms reset **6/8**. RX
  **7, 9..13** retained exact NUL plus the 62-byte normal fixture boot marker.
- Explicit release **35/36** at 16:59:10 UTC suspended automatic reconnect.
  Standalone external serial owner PID 3600 held the port at
  16:59:10.732885–16:59:13.272852 UTC, received hello/two statuses, sent no
  DUT UART/control and closed. Service remained released. Reacquire
  **37/38** staged segment 1; fresh CTRL1 **39/40**, CTRL0 **41/42** preceded
  `reacquire_succeeded` **43**. Immediate reset **45/47** succeeded, dispatched
  0.232 ms after the CLI return, without manual reconfiguration. RX
  **46, 48..52** retained the exact normal boot. Origins **399388717** and
  **425196591** us establish fresh per-segment RP2350 provenance.
- The operator then unplugged/replugged only Pico 2 USB while a continuous
  read-only observer was armed to dispatch one reset after connection success.
  At 17:03:25 UTC, **303** records unexpected disconnect (`Enhanced serial read
  failed`); **304** starts reconnect with timeout 5.0 s. Status sampled
  `reconnecting` at 17:03:25.355909 UTC, then `faulted/cleanup_unconfirmed`
  at 17:03:25.415053 UTC. Terminal journal is **failed/backend_input_error**,
  detail `read failed: [Errno 6] Device not configured`. There is no segment 2,
  automatic configuration ACK, reconnect success or post-reconnect reset, and no
  separate native reconnect-failed record. This failed before deadline expiry.
- The retained shutdown traceback shows old-source
  `close_current_source_for_reconnect` through Enhanced host/drain/reader close
  to `writer.wait_closed`, re-raising that pyserial read exception. No root-cause
  fix was attempted. The observer stopped at the first fault and requested CLI
  stop at 17:03:25.419487 UTC, acknowledged 17:03:25.561989 UTC. Application
  shutdown logged the retained exception/failed shutdown; PID/file/listener and
  serial owner were verified absent afterward. Re-enumerated helper identity
  matched; no reopen, reset retry or timeout enlargement followed.
- Final native **0..304 / 305** primary records reconcile **126 raw RX bytes /
  12 RX records**, six successful control pairs, two segments and two gaps;
  no UART sends/bounded operations/unresolved attempts. Raw SHA-256
  `9fc5ffce82472defa7adb38f69ed3306894732766fd911956b8541960228fa5d`.
  Ambient telemetry naturally retained 273 32-KiB status records with zero loss
  counts/high-water at most 62; this is not a stress repeat or electrical-loss
  claim. Scoped integrity, local recording and line processing remain complete.
- Full local artifacts are under
  `.dutchmate/hil/enhanced-control-generation-20261027T165521Z/`, including gate,
  preflight, CLI/API, exact ordering proofs, external owner, USB observer/fault,
  service log, shutdown checks, terminal native hashes and reconciliation.
  A passive cu/unused-tty `lsof` exit-code assumption was corrected using its
  actual sole-PID rows; no physical action was retried for that harness check.
  All 456 earlier session/config hashes, including failed 739/740, are unchanged.
- Reused previous accepted/current Monitor, Interact, follow, console, first-byte,
  telemetry, `accepted_32k`/overflow and bounded Revision A evidence. Explicit
  reacquire/control passed, but the combined acceptance and current unexpected
  reconnect criterion remain open due to the old-source cleanup fault. Phase 1A
  stays accepted; Phase 1B/Stage 8/Phase 1 and the recorded §34/Revision A gaps
  remain incomplete. Only Enhanced HIL report/status/history changed, unstaged
  and uncommitted; final `git diff --check` passed. No MCP or hardware-design work.

## Enhanced Control Generation Review Corrections — 2026-10-27

- Continued the existing unstaged, uncommitted
  `fix/enhanced-reacquire-control-config` branch at base `90c744f`. Limited this
  correction to runtime rollback, rejected-candidate cleanup and regressions.
  No hardware access, firmware, Revision A, MCP or acceptance-criteria changes.
- Profile initialization now uses a private cleanup helper to invalidate GPIO
  acceptance and clear `_commanded_boot_mode` together. Both the known
  `GpioConfigurationError` branch and all other initialization exceptions use
  it before propagating the original failure. A final readiness check after
  the last acknowledged mapping is inside the same rollback boundary.
- Added deterministic boot/CTRL1-success then reset/CTRL0-failure cases for a
  normal helper refusal and an unexpected response, exercising both exception
  branches. They verify raw runtime state, unconfigured GPIO status, retained
  error/detail and control evidence, no lifecycle success and one candidate
  close. Final-ACK deadline expiry separately verifies full rollback even when
  both configuration acknowledgements were successful.
- The coordinator is the sole cleanup owner of a candidate until successful
  handoff. Recorder provenance/state rejection, generic publication failure and
  late closing rejection no longer independently close an unpublished source.
  Automatic publication preserves its primary exception even when cleanup
  fails; the existing cleanup error remains separately retained and blocking.
  Automatic persistence failure stops without retry and retains
  `persistence_fault` when cleanup is confirmed, rather than misclassifying the
  persistence exception itself as uncertain physical cleanup.
- Added four persistence-publication regressions: manual and automatic paths,
  each with successful and failed candidate cleanup. Their invocation counter
  counts every `close()` call, including calls hidden by the fake's idempotent
  close implementation. All assert exactly one call through runtime shutdown,
  original failure identity, no authoritative replacement/no lifecycle success,
  and blocked subsequent reacquire. Failed cleanup retains
  `cleanup_unconfirmed` and its shutdown error. Existing initialization rejection
  cleanup coverage also now checks exact invocation count through shutdown.
- Initial focused RED: **7 failed, 3 teardown errors in 1.98 s**. Both partial
  initialization cases retained `"normal"`; final-ACK expiry retained accepted
  GPIO state; all four publication cases invoked candidate close twice. The
  teardown errors exposed the original cleanup-error retention/classification
  defects. Strengthened the automatic error-identity check and verified it
  failed separately when primary-error preservation was temporarily removed:
  **1 failed in 0.25 s**, cleanup error replacing the persistence exception.
- Focused GREEN: the seven new cases passed in **2.28 s**; final lifecycle file,
  including the original fifteen cases, **22 passed in 4.94 s**. Broader
  ownership/runtime/recorder/Enhanced/protocol/GPIO/service/CLI/architecture gate:
  **911 passed in 18.33 s**.
- Final validation using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen pytest -q --tb=line` **1,555 passed in 46.89 s**;
  `uv run --frozen ruff check .` passed; `uv run --frozen mypy` passed/103 files;
  `uv lock --check --offline` passed/66 packages; `git diff --check` passed.
  Line tracebacks avoid slow source introspection observed while formatting
  the initial failing tests. No test scope or assertions were suppressed.
- Existing reconnect/architecture/GPIO semantics already specify coordinator
  cleanup and truthful acceptance, so these corrections required no further
  edits there. The change is localized; no interfaces, layers or module
  ownership changed and no additional Graphify refresh was needed. Failed
  Enhanced HIL report and native evidence, including 739/740, remain unchanged.
  Phase 1A remains accepted; Phase 1B/Stage 8/Phase 1 remain incomplete. All work
  remains unstaged and uncommitted for another review.

## Enhanced Control Acceptance Across Connection Generations — 2026-10-27

- Created `fix/enhanced-reacquire-control-config` from independently fetched
  latest pushed `stage8-phase1-acceptance`,
  `90c744fe97ed3af2224989a954261bef42797b45`. Work is uncommitted for review.
  No physical serial access, service HIL, firmware, Revision A or MCP work was
  performed. The failed Enhanced HIL report and session were not modified.
- Confirmed source cause: `create_app` applies Profile hardware configuration
  through startup/runtime once; `GpioConfigurator` records accepted modes in a
  process-lived registry. The shared Enhanced reopen path only replaced control
  and sender targets, while the recorder published a new segment/success. It
  neither invalidated nor re-established physical GPIO acceptance. Firmware's
  new epoch correctly starts unconfigured; no firmware defect is asserted.
- Added an epoch-scoped helper surrogate beneath real service/runtime/recorder
  composition. Startup configures both Profile channels; reset works; release
  forgets physical configuration; reacquire opens a fresh helper. First RED
  reproduces the exact HIL result: immediate reset is HTTP 409 `not_configured`,
  detail `CTRL0 is not configured`, despite successful reacquire. The expanded
  initial regression run was **7 failed / 1 passed** with matching stale-status,
  false-success and automatic-reconnect failures before implementation.
- The recorder now stages the durable replacement segment while state stays
  reacquiring/reconnecting. A runtime-installed initializer waits for submitted
  mutations, invalidates old physical acceptance, and replays immutable Profile
  mappings through the same validated/audited configuration method as startup.
  Control attempts belong to the staged segment; acknowledgements alone update
  accepted state with fresh host/device timestamps. Final readiness is checked
  before success is persisted and the source is handed to authoritative RX.
  Candidate input stays buffered in the existing Enhanced owner until successful
  handoff; the early-UART regression verifies durable retention afterward.
- Ordinary actions in a generation do not resend modes. All CTRL0–CTRL3 can
  be driven by Profile mappings; runtime overrides do not become the desired
  source for a replacement epoch. Disconnected/released/reinitializing status
  does not advertise previous-generation configured acceptance. Role and
  DUT-signal metadata remain host-only; protocol and firmware are unchanged.
- Required initialization rejection/timeout preserves the actual control result
  and lifecycle failure, faults the journal/ownership through the existing
  backend-fault path, and publishes no reacquire/reconnect success. The service
  coordinator closes the unpublished candidate. Known rejection retains its
  actual error; close failure retains `cleanup_unconfirmed` and blocks ownership.
  Automatic initialization rejection is not silently retried as another success
  attempt. Startup's existing canonical validation/rejection semantics remain.
- Deadline/cancellation checks run during mutation-lock waits, before each mode
  command and before final success. A separate RED case caught dispatch of the
  next mode after simulated deadline expiry; GREEN stops before that command.
  No reconnect deadline was enlarged. Shutdown while initialization is blocked
  closes the candidate and cannot publish a late lifecycle success.
- A deterministic late-ACK regression reproduced prior-epoch runtime acceptance
  overwriting new state. Initialization now serializes against submitted
  mutations before invalidation, without holding evidence admission while
  waiting/dispatching. Interact's existing exclusive lease remains active during
  observation; its mutation lock now covers actual TX rather than the entire
  observation window. This preserves reconnect continuation and exact single TX.
  The configured-profile Interact regression failed `disconnected` before that
  adjustment and passes `matched` afterward; existing unknown-TX/no-retry cases
  also remain green.
- Focused GREEN: **15 new lifecycle cases passed in 3.02 s**. Targeted
  ownership/runtime/Enhanced/GPIO/protocol/service/CLI/architecture suites:
  **887 passed in 15.34 s**, followed by the final added four-channel case in the
  new-file run. Basic release/reacquire, validation, safe-state, role-resolution
  and exact no-role-metadata wire regressions are included in the gate.
- Full final gate, using `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen pytest -q --tb=short` **1,548 passed in 46.37 s**;
  `uv run --frozen ruff check .` passed; `uv run --frozen mypy` passed/103 files;
  `uv lock --check --offline` passed/66 packages; architecture checks are included
  in pytest. Final `git diff --check` passed. No required check remains failing.
- Updated reconnect and GPIO semantics to distinguish immutable desire from
  current physical acceptance, and architecture documentation for the shared
  segment/initialization/success boundary. No public schema field or persistence
  migration was introduced. A focused Graphify explanation was checked against
  source; `graphify update .` ran once: 5,887 nodes, 15,076 edges, 310 communities,
  with an aggregated visualization. It warned that unchanged
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h` line 69 was only partially
  parsed/no symbols extracted; code relationships used for this fix were checked
  against source/tests. This is a graph extraction limitation, not a hardware
  validation or test failure. Generated graph artifacts remain outside the diff.
- Phase 1A stays accepted. Phase 1B, Stage 8 and overall Phase 1 remain incomplete
  pending fresh physical lifecycle acceptance after this fix and the existing
  normative evidence gaps. Preserved failure 739/740 is not reclassified as a
  success. Only software/tests and authoritative documentation changed; nothing
  is committed or pushed by this slice.

## Enhanced v2 HIL: Stopped on Reacquire/Control Mismatch — 2026-10-27

- Ran from clean `stage8-phase1-acceptance` at latest pushed
  `887768c2e10da1ba8ae9c323474fad86648a7d34`, independently reverified via HTTPS.
  Pending audit documentation was backed up, temporarily restored to HEAD to
  obtain a clean tracked tree, then restored after HIL. No product code changed.
- Operator reported unknown installed images and authorized known-reference
  reflashing before acceptance. Accepted normal helper UF2 SHA-256
  `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819` was copied
  once to the identified RP2350 boot drive at 11:40:25–26 UTC (record below).
  Accepted 460800 DUT UF2
  `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6` was copied
  once at `11:42:20.956161`–`11:42:21.459537` UTC to `/Volumes/RPI-RP2`,
  whose bootloader v3.0 reported model Raspberry Pi RP2/board RPI-RP2. Both
  copies exited 0, then boot volumes disappeared. UF2 structure/families and
  source hashes were verified first. No image readback; transfer/boot-target
  records plus subsequent live hello/boot/INFO are the available provenance.
- Operator confirmed CTRL0→RUN, CTRL1→GP2, DUT_TX→GP0, DUT_RX→GP1, common
  ground, GP3 open and VIO from Pico 2 3V3. This is a trusted declaration, not a
  new voltage measurement. A separate HIL working directory supplied the fixed
  Enhanced 460800 8-N-1/no-flow-control/TX-enabled profile with those mappings
  and unchanged 5.0 s reconnect timeout. Original Basic config stayed unchanged.
  Profile digest `941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`.
- Fresh pre-start gate, using
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
  `uv run --frozen pytest -q --tb=short` **1,533 passed in 43.44 s** (including
  architecture), `uv run --frozen ruff check .` passed,
  `uv run --frozen mypy` passed/103 files, `uv lock --check --offline` passed/66
  packages, diff check and clean tracked status passed. No pytest or second
  DUTchMate runtime/session store ran while the physical service was live.
- Normal CLI start created sole owner PID 46863 and native-v2 session
  **`20261027T114440Z-7db24eae`** at 11:44:40 UTC. Live identity was
  `dutchmate-rp2350`/`development`, expected USB serial `FA63A4D787572B33` at
  `/dev/cu.usbmodem1401`, with `uart_receive`, no legacy receive/EVENT feature.
  Startup control attempts/results 1/3 and 4/5 configured boot/reset.
- Initial audited reset 42/44 persisted reset NUL at RX 43 before the result;
  RX 45..49 retained the complete 62-byte fixture marker. Exact 63 raw bytes
  were verified before any Monitor. INFO Interact `[67,77)` matched its one
  exact `INFO\n`; duration Monitor `[77,80)` elapsed. Follow displayed split
  PARTIAL RX 135/136, detached, and later BINARY RX (including invalid UTF-8)
  remained stored. A harness incorrectly expected different PARTIAL text;
  retained source verified the captured `DMF/1 PARTIAL complete` was correct.
  Original output/correction retained, no send retried.
- Duration Interact `[190,195)` elapsed, condition Interact `[195,202)` timed
  out normally with unrelated UART retained, literal Monitor `[214,219)` matched
  PONG, and condition Monitor `[219,221)` timed out normally. Real CLI console
  with interactive piped stdin sent one PING/LF, displayed PONG and detached
  via SIGINT; later standalone INFO remained recorded. All TX was audited once.
- Operator held RUN low while audited bootloader 556/557 selected CTRL1/GP2,
  then released it; exact 81-byte expected E_INIT_001 boot RX 582..587 was
  retained outside bounded operations. Another confirmed held-reset interval
  allowed audited normal 680/681; release retained exact normal RX 700..704.
  These expected fixture modes are distinct from the later control blocker.
- Release intent/released 733/734 closed segment 0 and exposed a gap. Only while
  Device Core was `released`, standalone serial PID 47481 exclusively opened
  the helper at 11:55:57–59 UTC, received hello/two status frames, sent no
  UART/control command, then closed. One reacquire 735..737 continued the same
  session in segment 1; telemetry resumed at 738. Segment RP2350 source origins
  are 253900607 and 964063386 us; segment-local timing is not comparable across
  the gap. No extra runtime/store was constructed for external ownership.
- **Observed blocker:** post-reacquire status still advertised CTRL0/1 configured
  from the original config, but the single following reset returned HTTP 409
  `not_configured`, `CTRL0 is not configured`. Attempt 739 resolves reset to
  CTRL0/RUN; result 740 records not_configured/null device timestamp. Final
  status still showed both configured. Stopped the acceptance path without
  GPIO reapplication, retry, timeout enlargement, firmware/product fix or
  further Interact. Unexpected USB reconnect was not attempted. Root cause
  and repair were left for a separate focused slice.
- RX 784..789 later retained a separate 63-byte normal boot at 11:57:14 UTC,
  about 44 s after the rejected reset. Its trigger is not established by host
  action evidence and was not credited as success of the rejected reset; it
  demonstrates resumed RX alongside ambient telemetry in segment 1.
- All 774 status records report ring size 32768, dropped totals/overflow 0;
  high-water reached 81 bytes. `none_reported` remains scoped only to reported
  Debug Helper RX-buffer loss, not electrical losslessness. Prior accepted
  deliberate-overflow/32 KiB evidence remains applicable to the exact reflashed
  reference images; no heavy stress or accepted physical measurement repeated.
- CLI list/detail/log/status, service detail/log and saved-cursor retrieval
  passed. Cursor retrieval retained contiguous 42..866 (825 records), including
  the failed control and ownership gap. Final native reconciliation: sequences
  0..866 contiguous, 510 raw bytes/47 RX, eight TX pairs, six control pairs
  (five success/one not_configured), six terminal bounded operations, two closed
  segments and one gap. Raw SHA-256
  `feeaabbc890ece3168090a62b324f10c2ae5845f2eceeccab70d9a88ca3f2e17`.
- Graceful stop returned 11:58:31.098956 UTC; journal is
  completed/service_shutdown, not an acceptance pass. PID 46863/PID file,
  listener and serial ownership were verified absent. All 448 earlier
  session-file hashes and Basic config are unchanged. Full artifacts, snapshots,
  cursor pages, final hashes and service log are retained in
  `.dutchmate/hil/enhanced-phase1b-20261027/`; earlier preflight/preparation
  artifacts remain in their original folder.
- Enhanced report maps every §34 criterion to passed current evidence, reused
  accepted evidence or open/blocking evidence, and retains the separate Revision
  A measurement/design gaps. **Enhanced HIL, Phase 1B, Stage 8 and Phase 1 remain
  incomplete**; Phase 1A remains accepted and its anomaly unchanged. No MCP or
  fix/TDD work started. Only Enhanced report/status/this newest history record
  changed for this run, uncommitted for review; final diff check passed.

## Authorized Enhanced Hardware Preparation: Helper Reference Flash — 2026-10-27

- Operator reported installed images unknown and authorized known-reference
  reflashing before acceptance, then confirmed Pico 1 GP3 open and Pico 2
  BOOTSEL. This preparation is separate from the acceptance run; no product
  code, fixture source, profile, timeout or acceptance criterion was changed.
- Passive boot-drive check identified `/Volumes/RP2350`, bootloader v1.0,
  model/board `Raspberry Pi RP2350` / `RP2350`, and IOUSB
  `RP2350 Boot@00140000`. No service listener was observed. Recomputed normal
  helper UF2 SHA-256 matched
  `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`.
- One guarded transfer copied the 104,448-byte accepted normal helper to that
  drive, `2026-10-27T11:40:25.369806Z`–`11:40:26.267602Z`; `/bin/cp` returned
  0 without stderr. At `11:40:31.920834Z`, the boot volume was gone and helper
  `/dev/cu.usbmodem1401`, `2E8A:000A`, `FA63A4D787572B33` was present again.
  The image was not read back; exact source hash, boot-target identification,
  successful transfer and passive re-enumeration establish available provenance.
  No live hello or UART command was used in this preparation step.
- `flash-helper.json` and `helper-after-flash.json` under the existing Enhanced
  preflight audit folder preserve the write and observations. Pico 1 transfer
  had not occurred at this record; its installed firmware remained unknown.
  No acceptance service/session, runtime/store probe, control or stress run
  started. No new software gate is claimed by this hardware-preparation record.

## Enhanced Phase 1B Evidence Audit: Stopped at Hardware Preflight — 2026-10-27

- Started from clean `stage8-phase1-acceptance` at
  `887768c2e10da1ba8ae9c323474fad86648a7d34`. Local origin ref matched; independent
  read-only HTTPS `git ls-remote` confirmed the same latest pushed branch SHA.
  Sandbox fetch could not write `.git/FETCH_HEAD`; elevated SSH lookup failed
  public-key authentication, then HTTPS lookup succeeded. No checkout/ref change,
  production patch, configuration edit, firmware build/flash, or MCP work occurred.
- Audited specification §§33–35, Stage 8, Enhanced HIL, ring-buffer acceptance,
  and Revision A records before any hardware access. Added an explicit §34
  disposition matrix to the Enhanced report. No criterion is claimed passed by
  current HIL: physical preflight prevented startup. Phase 1A remains accepted;
  Phase 1B, Stage 8, and overall Phase 1 remain incomplete.
- Full software gate used
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short` (**1,533 passed in 42.86 s**, including
  architecture tests), `uv run --frozen ruff check .` (passed),
  `uv run --frozen mypy` (103 files, passed), and
  `uv lock --check --offline` (66 packages, passed). `rtk git diff --check`
  passed before edits and after documentation review. No physical service ran
  during tests or afterward; no separate runtime/session-store probe was used.
- Passive inventory at `2026-10-27T11:27:19.705174Z` (16:57:19 IST) found only
  debug-console/Bluetooth serial entries with no USB identities. Later IOUSB tree
  showed controllers and two hubs, no Pico. No TCP 2040 listener was observed;
  process enumeration was sandbox-denied, so absence of all background processes
  is not asserted. No serial port was opened. Actual connected/flashed helper
  and fixture identities, baud, wiring, VIO, and control mapping were unverified.
- Pure profile resolution confirmed unchanged Basic exact-path FTDI selection,
  115200 8-N-1/no flow control, TX enabled, line ending `none`, driver-default
  DTR/RTS, declared 3.3 V, 5.0 s reconnect timeout, and no reset/boot mappings.
  That profile cannot establish the requested Enhanced path. Operator
  prerequisites are recorded in the Enhanced report; hardware preparation and
  positive identity/wiring verification are required before acceptance startup.
- Operator follow-up confirmed CTRL0→RUN, CTRL1→GP2, DUT_TX→GP0, DUT_RX→GP1,
  common ground, and `DUT_VIO` supplied from Pico 2 3V3. Passive serial and IOUSB
  recheck still found no Pico and no TCP 2040 listener. This is a wiring
  declaration, not a voltage/continuity measurement; flashed images, DUT baud,
  GP3/strap state and installed correction remain unverified. Startup stayed
  stopped; configuration and hardware were not changed.
- After the operator connected USB, passive enumeration at
  `2026-10-27T11:34:50.844840Z` found `/dev/cu.usbmodem1401`, VID:PID
  `2E8A:000A`, serial `FA63A4D787572B33`, location `0-1.4`; IOUSB showed
  `Debug Helper@00140000`. No cu/tty owner or TCP 2040 listener was reported.
  This resolves USB visibility and matches recorded USB identity, not flashed
  firmware provenance. `usb-recheck.json` preserves the passive inventory;
  firmware/DUT baud/strap questions remained pending and startup stayed stopped.
- Operator reported both installed images unknown and authorized reflashing
  known references as preparation before acceptance. At
  `2026-10-27T11:37:23.514031Z`, both retained UF2 hashes matched again;
  block magic/end markers, payload bounds, ordered block/count fields and board
  families verified (helper 104,448 bytes / 204 blocks / `0xe48bff57`, DUT
  34,304 bytes / 67 blocks / `0xe48bff56`). No boot volume was mounted and no
  image was flashed at that point. `flash-preparation.json` preserves the
  selected sources/hashes and authorization; operator was asked for Pico 2
  BOOTSEL first and GP3 confirmation before any write.
- Recomputed normal helper UF2
  `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`, diagnostic
  helper UF2 `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66`,
  Enhanced fixture UF2 `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6`,
  and fixture `.config` hashes match accepted records. All five revised
  boot/backpressure/overflow stack/profile JSON reports and boot/five-cycle
  pull-up Saleae CSV hashes also match. These prove retained artifacts, not
  the currently flashed images. Source comparison from `ae01ce2` found no ring,
  drain, stack-sizing, mapping or protocol-schema change; helper differences
  concern product-version metadata and equivalent bounded hello-string length.
- Retained `accepted_32k` for the measured images/setup: 32,768 raw ring bytes,
  normal static RAM 81,040/532,480, CDC RX minimum 1,248/5,120 bytes free,
  deliberate-overflow accounting 19,418 retained + 23,663 dropped = 43,081,
  six overflow records and surviving checksum. No invalidation was established
  and no heavy stress was repeated. Applicability to actual connected hardware
  is still unverified; current continuous-v2 telemetry/loss projection needs HIL.
  `none_reported` remains scoped to reported helper RX-buffer loss only.
- Reused recorded voltage loopbacks/current, push-pull/open-drain/reset safety,
  loaded static missing-supply isolation, settled sequencing, unloaded hot-plug,
  and later bounded TX-pull-up digital recovery results. Actual gaps include
  populated-part/continuity and adopted correction verification, analog
  UART/cable/series-resistor evidence, calibrated absolute leakage, broader
  transient/isolation coverage, and ESD measurements. No accepted physical
  measurement was repeated. EVENTn remains outside Phase 1 live implementation.
- Preserved all 448 prior session-file hashes plus the unchanged config.
  Passive preflight/profile JSON, artifact hashes, and preservation manifest
  are under `.dutchmate/hil/enhanced-preflight-20261027/`; no native-v2 hardware
  session was created. Only Enhanced report/status/this new history entry
  changed, uncommitted for review. Prior Basic/Enhanced history and evidence
  were preserved; no cause/fix is assigned to the non-blocking Basic anomaly.


## Bounded Overflow Physical Diagnostic: NUL/ff Prefix and INFO Tail — 2026-10-27

- Ran only the requested focused diagnostic on clean `stage8-phase1-acceptance`
  at `4692444f771f33b6d27994e03f2722c268e3f43a`. Initially the local reviewed commit was ahead of the remote;
  waited for the operator's push and independently verified that exact remote
  SHA before physical startup. No code/fixture/configuration changes occurred.
- All software validation finished first: 1,533 pytest tests in 42.52 s, Ruff,
  mypy (103 source files), offline lock (66 packages), diff check. Exact commands
  used `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, `uv lock --check --offline`. Gate ended
  16:20:25.507066 IST; normal CLI start began 16:22:45.444537 IST. No pytest or
  second DUTchMate runtime/session store ran while the service was live.
- FTDI FT231X `0403:6015`, serial `D358SG6A`, expected cu path/USB location,
  no pre-existing owner/listener/PID file. Basic profile unchanged: 115200 8-N-1,
  no flow control, TX explicitly enabled, reconnect timeout 5.0 s, driver-default
  DTR/RTS. User confirmed externally flashed Pico 1/H build
  `basic-ovf-20261027-3cbe8d2ee291`, reviewed Zephyr 4.4.0 / SDK 1.0.1 image.
  UF2 recomputed SHA-256 `c1f0067c910ccf8ae0108eed5362da957dc50e4a9a801a4afce69c0ce4407409`; source snapshot matched the build.
  First exact INFO matched the complete build literal. Agent did not flash it.
- Fresh schema-v2 session **`20261027T105245Z-a78a6741`**, PID 44442. Exactly two INFO Interacts:
  initial matched `[1,6)` (audit 2/3, RX 4, terminal 5), and one following the
  single automatic reconnect `[10,15)` (audit 11/12, RX 13, timeout terminal 14).
  Each audited exact `494e464f0a`/`INFO\n`, one attempt/result, accepted 5 bytes.
  No other UART command, parser clearing, reset, manual reacquire or retry.
- Trial 1 out of maximum three reproduced and stopped. Passive USB/node/status/
  native-connection observers and operator timestamp markers were preserved;
  no serial open probes. Disconnect/start 6/7, fresh segment/success 8/9;
  same ownership session, one durable gap, resumed RX and responsive service.
  First-observed reconnect delta 3.124234834 s, unchanged 5.0 s policy.
- Complete response preserved exactly:
  `DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=1 line_len=90 prefix_hex=0000000000000000000000000000ff0000000000000000ff000000ff00000000 overflow_byte=00 discarded_count=58 suffix_hex=000000ff494e464f\n`.
  `line_len=90`, first overflow `00`, discarded_count=58, counts_overflow absent.
  Prefix is exactly 29 `00` / three `ff`; ff at one-based 15/24/28. All 32 bytes
  and complete hex are recorded in the Basic report. Suffix
  `000000ff494e464f` ends with `494e464f` (**INFO**), showing INFO arrived while
  the assembler was already handling an overlong line. Relevant byte values at
  positions 34–82 are not captured or inferred. This does not show electrical
  waveform or establish a root cause in any host/adapter/wiring/UART/Zephyr/
  fixture layer. No remediation or exoneration is claimed.
- Native final state `completed/service_shutdown`, 303 raw RX bytes, 2 RX
  records, 2 TX pairs, 2 terminal operations, 2 segments, 1 gap, sequences 0..14
  contiguous; decoded RX matches raw. Saved-cursor service retrieval preserves
  6..14, including all reconnect/second-INFO evidence. Native copies, hashes,
  service log, complete decode and cleanup are under
  `.dutchmate/hil/basic-overflow-physical-20261027/`.
  Raw SHA-256 `4c908fc39eaedd8e6a008546d04de3bc27a00dd32d3a6fdf78ddf0f9ec05c948`.
- Graceful CLI stop returned 16:27:52.676969 IST; at
  16:27:54.550083 IST PID/PID file absent, no TCP 2040 listener or FTDI
  cu/tty owner. All 441 earlier session-file hashes and raw config unchanged;
  no SIGKILL, patch, new flash or further diagnostic. Only Basic report/current
  status/this newest history entry changed; older history and reports preserved.
  `git diff --check` passed; documentation remains uncommitted for review.
- **Phase 1A remains Complete/accepted**; this diagnostic is not a full Basic
  acceptance rerun. Stage 8, Phase 1B and overall Phase 1 remain incomplete;
  Enhanced HIL and MCP remain deferred. The anomaly's source remains unresolved.


## Bounded Basic Fixture Overflow Diagnostics Prepared — 2026-10-27

- Started clean on latest-pushed `stage8-phase1-acceptance`,
  `68ae39714fb5ebfd55ec970e2709d29561c822e9` (HTTPS `ls-remote` confirmed).
  Fixture-only enhancement remains uncommitted for review. The requested
  physical reproduction has not started because the user explicitly requires
  review, commit and push before any hardware run. No new physical session,
  serial open, service startup or flash occurred.
- Overlong error lines append exact `line_len`, first-32-byte `prefix_hex`, first
  `overflow_byte`, `discarded_count` including that first overflow byte, and
  chronological last-eight-byte `suffix_hex`. Existing command interpretation
  and error fields are retained; new fields appear only for discard=1.
  Non-overflow errors and successful output remain byte-for-byte compatible.
- Reused the existing command buffer for the prefix and added a fixed 16-byte
  observation struct. No allocation or unbounded capture. LF clears state;
  ignored CR never enters counts/captured bytes; NUL and high bytes stay exact.
  A 32-bit count saturates internally without wrapping: after its representable
  range, numeric counts are omitted with `counts_overflow=1`, while bounded
  byte observations remain valid. No timeout/reset/resynchronization added.
- RED: 7 missing-diagnostic assertions failed, 29 existing cases passed; both
  real C harnesses compiled. GREEN: 36 focused tests passed in 9.73 s. Tests
  exercise the actual UART loop at 32/33 bytes, varied binary overruns, NUL/ff,
  CR handling, LF reset/recovery, 100,000-byte input, unchanged existing errors/
  valid output and seeded count exhaustion through the real private helper.

| Validation | Result |
|---|---|
| `rtk proxy .venv/bin/python -m pytest tests/hardware/zephyr_dut/test_fixture_protocol.py -q --tb=short` | 36 passed in 9.73 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q --tb=short` | 1,533 passed in 43.29 s, including architecture checks |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed, 103 source files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed, 66 packages; lock unchanged |
| `git diff --check` | Passed |

Cross-build passed with Zephyr `v4.4.0` / SDK `1.0.1`, GNU `14.3.0`, west `1.3.0`:

```bash
rtk proxy env \
  ZEPHYR_BASE=/Users/nahitpawar/zephyrproject/zephyr \
  ZEPHYR_SDK_INSTALL_DIR=/Users/nahitpawar/zephyr-sdk-1.0.1 \
  CCACHE_DIR=/tmp/dutchmate-basic-ccache \
  /Users/nahitpawar/zephyrproject/.venv/bin/west build \
  -b rpi_pico -s hardware/firmware/zephyr_dut \
  -d build/dutchmate-zephyr-dut-basic-ovf-3cbe8d2ee291 --pristine -- \
  '-DCONFIG_DUTCHMATE_FIXTURE_BUILD_ID="basic-ovf-20261027-3cbe8d2ee291"' \
  -DDTC_OVERLAY_FILE= -DEXTRA_DTC_OVERLAY_FILE= \
  -DUSER_CACHE_DIR=/tmp/dutchmate-basic-zephyr-cache
```

- Review build ID `basic-ovf-20261027-3cbe8d2ee291`; source inventory SHA-256
  `3cbe8d2ee291b49c8185d6f1ff45996e371d82d63f3c142a57e94fe830e712b1` (sorted relative path/NUL/content/NUL, README excluded).
  UF2 `build/dutchmate-zephyr-dut-basic-ovf-3cbe8d2ee291/zephyr/zephyr.uf2`, 36,352 bytes; SHA-256
  `c1f0067c910ccf8ae0108eed5362da957dc50e4a9a801a4afce69c0ce4407409`. Config SHA-256
  `8a4649450bb737da6289b6e358001626712f61db44c499220ef88bfeb547ceec`. It has not been flashed or physically validated.
- Verified `rpi_pico/rp2040`, UART0 115200/no flow control, both overlay settings
  empty, build ID and new diagnostic formats linked. UF2 block structure and
  decoded binary payload validated. ARM compile-time assertion confirms 16-byte
  added state. No UART/Basic configuration or reconnect timeout changed.
- Updated fixture README, the software-only preparation record, status and this
  newest history entry. All 996 existing `.dutchmate`
  file hashes and 14 earlier UF2 hashes unchanged; prior
  history/physical reports preserved. No DUTchMate production behavior, API,
  persistence, acceptance criterion, hardware code outside this fixture or
  normative status changed. The added fields do not prove electrical waveform
  or root cause. **Phase 1A remains Complete/accepted**; Stage 8, Phase 1B and
  overall Phase 1 incomplete; Enhanced HIL/MCP deferred. Review stops before
  the separately gated focused physical run (at most three reconnect/INFO trials).


## Instrumented Basic Diagnostic: Discard Path Reproduced — 2026-10-27

- Clean latest-pushed `stage8-phase1-acceptance` at
  `69a0980e1c7ced2cfcf053ebdd95e7b8dcc16df4`, independently verified by HTTPS `ls-remote`.
  Ran only the bounded physical command-path diagnostic, not full Basic
  acceptance, Enhanced HIL or MCP. Production/fixture code was not changed.
- Before service startup: 1,527 pytest tests passed in 39.73 s (including
  architecture/fixture tests); Ruff, mypy (103 files), offline lock (66 packages)
  and diff check passed. Commands used prefix
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, `uv lock --check --offline`. Software gate ended
  `10:02:36.512931Z`; normal CLI start began `10:03:53.632431Z`.
  No pytest or second runtime/session store ran during the live service.
- Operator confirmed externally flashed Pico 1/H, normal wiring/power/straps,
  closed terminals; FTDI FT231X `0403:6015`, serial `D358SG6A`, expected cu path,
  115200 8-N-1/no flow control, unchanged reconnect timeout 5.0 s. Build
  `basic-diag-20261027-d406684c5dff`, Zephyr 4.4.0 / SDK 1.0.1;
  UF2 recomputed SHA-256 `7eeead1fc216035eb4163aae768bdd22838988caa944d9f4bc5d3628575f43f3`.
  First physical INFO confirmed the exact build. Source inventory matches
  committed fixture sources; agent did not flash firmware.
- Fresh schema-v2 session **`20261027T100353Z-1d5cd35f`**, PID 41181. Initial INFO
  matched at RX 4, terminal 5, range `[1,6)`. One FTDI-only automatic reconnect
  continued that session: disconnect/start 7/8, fresh segment/success 9/10,
  durable gap, resumed RX 14; observer start-to-success 3.148789542 s, unchanged
  5.0 s policy. Operator unplug/replug markers and poll observations preserved.
- Both INFO operations made one exact `INFO\n` attempt/result, accepted 5 bytes:
  initial 2/3 and post-reconnect 12/13. Post-reconnect operation
  `interact-787a3fea-0c73-4516-a7b2-a46b40ff928f`, range `[11,16)`, timed out
  at terminal 15 after RX 14 emitted exactly:
  `DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=1\n`.
  Stopped at the first trial out of the maximum five, with no retry, extra UART
  command, parser reset/workaround, manual reacquire or patch.
- **Established:** the fixture overlong/discard path was involved in this new
  recurrence; zero-length handler input is not evidence of an empty ingress
  line. **Unknown:** discarded values, timing/origin and root cause. Host audit
  does not prove wire bytes; exact INFO rejection at the handler was not seen.
  Older uninstrumented errors remain unclassified. Ambient host RX 6 at
  `10:14:00Z` contains `00` in the opposite direction to command ingress; this
  byte is preserved without assigning a cause or equating it to parser input.
- Final read-only service status/detail/tail-cursor snapshot and native files
  preserved under `.dutchmate/hil/basic-ingress-diagnostic-20261027/`, including
  operator markers, per-trial samples, stop reason, service log, final native
  copy and hashes. Native counts: 153 raw RX bytes, 3 RX records, 2 TX pairs,
  2 terminal operations, 2 segments, 1 gap, contiguous evidence 0..15; decoded
  RX matches raw bytes. Final state `completed/service_shutdown`; no active or
  unresolved actions. Raw SHA-256 `a6598a256607dbf1ba3ca0ca8462512994db409942e03353d90602166c124ecd`.
- Graceful normal CLI stop returned `10:15:35.223675Z`; at
  `10:15:52.109926Z` PID/PID file absent, no TCP 2040 listener or FTDI cu/tty
  owner. No SIGKILL or external serial consumer. All 434 earlier session-file
  hashes and raw configuration bytes unchanged. Only the Basic diagnostic
  record, current status and this new history entry changed; prior history and
  acceptance evidence retained. Documentation/evidence checks and
  `git diff --check` passed. Changes are uncommitted for review.
- **Phase 1A remains Complete/accepted.** The anomaly remains unresolved and
  non-blocking, with this recurrence narrowed to the discard path. Stage 8,
  Phase 1B and overall Phase 1 remain incomplete; Enhanced HIL and MCP deferred.


## Basic Fixture Command-Byte Diagnostics — 2026-10-27

- Started with clean `stage8-phase1-acceptance` at
  `6c908f79f1a0a4e636a45cbd70576666e2ad5cac`. SSH fetch failed authentication;
  a read-only HTTPS `ls-remote` independently confirmed that exact pushed branch
  tip. Changes are fixture/test/documentation only and uncommitted for review.
- Unknown-command responses retain the single-line DMF prefix and
  `E_COMMAND_001` meaning, appending
  `command_len=<decimal> command_hex=<lowercase hex> discard=<0|1>`.
  Hex encoding uses the handler's explicit length, including leading/embedded/
  trailing NUL and high bytes; it does not use a C-string view or truncate the
  command. Encoding streams through the existing writer without allocation.
- The UART assembler is unchanged except for passing its current discard flag
  to the handler. CR remains ignored, LF dispatches, idle retains the prefix,
  exactly 32 bytes fit, and a 33rd non-CR/non-LF byte clears length and discards
  through LF. Overflow therefore reports `command_len=0 command_hex= discard=1`,
  faithfully describing the existing empty handler input rather than inventing
  discarded bytes. Ordinary empty lines report `discard=0`; SILENT still mutes
  errors. Successful commands and boot output remain byte-for-byte compatible.
- Raw-line `rx_len`/`rx_hex` capture was not added: ignored CRs/overlong tails can
  be unbounded, and exact raw retention would need complexity or truncation.
  README distinguishes full interpreted command bytes from raw ingress and
  electrical wire evidence. This observes the Pico firmware/UART processing
  path, not the FTDI TX → Pico RX waveform or bytes lost before polling. A logic
  analyzer may still help later; `E_COMMAND_001` remains unresolved/unclassified
  until reproduced with useful ingress evidence. No cause or fix is claimed.
- Added a host harness around the actual firmware `main.c` using stdin/stdout
  UART and deterministic GPIO/clock stubs; the parser itself is not mocked or
  copied. Tests cover unknown ASCII, leading/embedded/trailing NUL, high bytes,
  `XINFO`, ignored CRs, no output before LF, all 32 command bytes, overlong
  discard/no early error, recovery after LF, silence and no success diagnostics.
  Existing portable protocol/boot/delay/partial/binary/burst/sustain tests remain.
- **RED:** before firmware changes, the focused run produced 10 failed assertions
  for missing diagnostics and 20 passing cases; both C harnesses compiled and
  failures showed the old error line rather than test setup errors.
  **GREEN:** all 30 focused cases passed in 6.63 s after instrumentation.

| Validation command | Result |
|---|---|
| `rtk proxy .venv/bin/python -m pytest tests/hardware/zephyr_dut/test_fixture_protocol.py -q` | 30 passed; both harnesses compiled with C11, `-Wall -Wextra -Werror` |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,527 passed in 42.33 s, including architecture checks |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 source files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed; 66 packages, lockfile unchanged |
| `git diff --check` | Passed |

Cross-build validation used Zephyr `v4.4.0` / SDK `1.0.1`, GNU `14.3.0`, west
`1.3.0`, the existing default board/UART configuration and a separate build ID.
This did not replace or flash the previously accepted Basic image.

```bash
rtk proxy env \
  ZEPHYR_BASE=/Users/nahitpawar/zephyrproject/zephyr \
  ZEPHYR_SDK_INSTALL_DIR=/Users/nahitpawar/zephyr-sdk-1.0.1 \
  CCACHE_DIR=/tmp/dutchmate-basic-ccache \
  /Users/nahitpawar/zephyrproject/.venv/bin/west build \
  -b rpi_pico -s hardware/firmware/zephyr_dut \
  -d build/dutchmate-zephyr-dut-basic-diag-d406684c5dff --pristine -- \
  '-DCONFIG_DUTCHMATE_FIXTURE_BUILD_ID="basic-diag-20261027-d406684c5dff"' \
  -DDTC_OVERLAY_FILE= -DEXTRA_DTC_OVERLAY_FILE= \
  -DUSER_CACHE_DIR=/tmp/dutchmate-basic-zephyr-cache
```

- Source inventory SHA-256, using the earlier sorted relative-path/NUL/content/
  NUL method excluding README:
  `d406684c5dffd4b505c2d683198719913d4d4b4c630be44037539e865bc6c92b`.
- Build passed; `.config` confirms `rpi_pico/rp2040` and build ID
  `basic-diag-20261027-d406684c5dff`. Generated UART0 is 115200 with no
  `hw-flow-control`; both overlay CMake settings are empty. The linked binary
  contains the build ID, diagnostic format and both discard suffixes.
- UF2: `build/dutchmate-zephyr-dut-basic-diag-d406684c5dff/zephyr/zephyr.uf2`,
  35,328 bytes; SHA-256
  `7eeead1fc216035eb4163aae768bdd22838988caa944d9f4bc5d3628575f43f3`.
  `.config` SHA-256:
  `2fdc5a73125134f512a42bf8bd8f8bcd1f765c7c78c8120b3ceec4cf741bc733`.
- All 940 pre-existing `.dutchmate` evidence/configuration files are unchanged;
  earlier history and the accepted Basic HIL report are untouched. No production
  behavior, API, persistence, acceptance criterion or UART configuration changed.
  No hardware was accessed, no serial port opened, no firmware flashed and no
  physical HIL performed. **Phase 1A remains Complete/accepted**; Stage 8,
  Phase 1B and overall Phase 1 remain incomplete. Enhanced HIL/MCP were not started.


## Phase 1A Accepted After Normative Contract Audit — 2026-10-27

- Audited the fresh run `20261027T073956Z-7c038da2` at code baseline
  `31b14a4de28c3713fbb8451f31520600917616dc` against the current
  [Phase 1 specification](phase1_implementation_spec.md), the
  [Stage 8 plan](dutchmate_phase1_v2_coding_agent_plan.md), and the product
  context. This was documentation/evidence review only: no code change, new
  code-test run, service startup, serial open or hardware action occurred.
- **Authority finding:** specification §13.6 defines unexpected reconnect as a
  durable boundary, reconnect deadline, continued ownership session and safely
  opened new segment before the deadline. Section 33 requires that "unexpected
  reconnect works through the same v2 evidence model." Neither clause requires
  a successful deterministic INFO after reconnect. The Stage 8 Basic HIL list
  also has no such requirement; its exit criterion defers to the specification's
  Phase 1A/1B done criteria, and the plan must not redefine the normative contract.
- The previous acceptance interpretation incorrectly promoted an added HIL
  INFO diagnostic into a normative gate. That interpretation is superseded by
  this audit. The earlier history entry remains unchanged as a record of the
  initial decision and the actual unsuccessful INFO operation.
- Stored evidence confirms success 76 within 3.138501291 s of observed reconnect
  start, timeout configured at 5.0 s, the same active native-v2 session, fresh
  segment 2, the durable observation gap, resumed RX 80 and responsive status.
  Thus the actual unexpected-reconnect criterion passed. Under §14.2 the error
  response is real RX evidence; under §21.5 the unmatched condition correctly
  returned timeout with its durable range.
- All other §33 gates were satisfied by this same fresh physical run and its
  recorded pre-start software gate: ambient boot/INFO, follow/detach, duration/
  literal Monitor, enabled exact TX, matched/elapsed/timeout Interact, unrelated
  async RX, delayed fault after terminal 49 at RX 50, live console/post-exit
  recording, native-v2 provenance/retrieval/loss display, and real external
  handoff/reacquire. Default TX denial and linked size/segment rollover were
  covered by the recorded 1,514-test suite; physical 16 MiB/32-segment forcing
  was not performed and is not a required minimum Basic physical HIL scenario.
- **Phase 1A marked Complete.** Stage 8, Phase 1B and overall Phase 1 remain
  incomplete pending Enhanced HIL and remaining physical evidence. No Enhanced
  HIL or MCP work was started by this audit.
- **Anomaly preserved:** exact INFO audit 78/79 accepted five bytes, RX 80 is
  `DMF/1 ERROR COMMAND code=E_COMMAND_001\n`, and terminal 81 remains timeout
  for operation `interact-f1864e18-1d4a-46b0-b666-de286db8e5ca`, range `[77,82)`.
  No retry occurred. The added diagnostic check remains unsuccessful; the
  command-path anomaly remains unresolved, unclassified and non-blocking for
  Phase 1A. No host, adapter, fixture/parser or electrical cause or fix is claimed.
- Updated only current status, the latest Basic run's acceptance interpretation
  and this appended history entry. Raw native sessions, run artifacts, hashes,
  configuration, normative documents and prior history entries remain unchanged.
  In particular, the pre-audit run-summary/stop records retain their original
  conservative decision; the corrected report explicitly supersedes only that
  decision. Documentation consistency, evidence preservation and
  `git diff --check` passed. Changes remain uncommitted for review.


## Fresh Basic Phase 1A Acceptance: Post-Reconnect INFO Failure — 2026-10-27

- Used clean pushed `stage8-phase1-acceptance` HEAD
  `31b14a4de28c3713fbb8451f31520600917616dc`, independently matched by HTTPS
  `ls-remote`. Read the current specification, CLI guide, Stage 8 procedure and
  Basic HIL record. No old failed/diagnostic session was resumed or counted.
- Completed all software checks before physical startup: 1,514 tests passed in
  36.18 s, Ruff passed, mypy passed (103 files), offline lock check passed (66
  packages), and `git diff --check` passed. Commands used prefix
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. CLI help and client
  script syntax checks also finished before service startup. No pytest, extra
  runtime/session store or production/fixture patch ran during physical HIL.
- Reverified FTDI FT231X `0403:6015`, serial `D358SG6A`, location `0-1.4`, at
  `/dev/cu.usbserial-D358SG6A`; no serial owner or service listener existed.
  Operator reconfirmed Pico 1/H, reviewed build and all required wiring/straps.
  UF2 SHA-256 matched
  `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`;
  normal rpi_pico/115200/no-flow-control build and SDK 1.0.1 cache were verified.
  Preflight did not open the port; physical boot/INFO were verified through the
  fresh service.
- Normal Basic startup created fresh native-v2 session
  `20261027T073956Z-7c038da2`, PID 33018, at 07:39:56 UTC / 13:09:56 IST.
  Configuration stayed unchanged: 115200 8-N-1, no flow control, explicit TX,
  default ending none, exact-path/external UART, reconnect **5.0 s**, 16 MiB
  budget, retention disabled, driver-default DTR/RTS. Actual ambient RUN reset
  captured reviewed boot banners; the first INFO Interact matched the exact
  `basic-v2-20261026-7bc2ec377767` build. Reset NUL bytes were preserved.
- Follow displayed PONG and detached with exit 0; post-detach INFO remained
  recorded. Duration and literal Monitor, exact audited TX, matched/elapsed/
  timeout Interact, unrelated async RX, and live console PONG/INFO plus continued
  acquisition after EOF passed. Only the service owned serial during views.
- Dedicated delayed fault passed: ACK RX 48, durable Interact terminal 49,
  fault RX 50 outside `[45,50)`, host delta 10,040,059 us. No bounded operation,
  follow or console ran during the 11-second post-completion interval.
- Release passed in 0.673635 s: final RX 62, intent 63, released 64, segment
  closure and gap count 1. The real external same-port consumer received exact
  PARTIAL output, held ownership for 6 seconds with service released, and closed
  before reacquire. Start/segment-open/success 65..67 created fresh segment 1;
  first reacquired INFO matched. External RX was excluded from the service log.
- Automatic unexpected reconnect passed: disconnect/start 73/74 observed at
  07:48:06.309105 UTC, USB back 07:48:08.782975, node back 07:48:08.791297,
  segment-open/success 75/76 at 07:48:09.447608. Observed elapsed 3.138501291 s,
  inside the unchanged five-second window. Same session, fresh segment 2,
  distinct origin and second durable gap were verified. Passive observation had
  no operator-wait expiry and made no competing external open probe.
- **Required first post-reconnect INFO failed:** operation
  `interact-f1864e18-1d4a-46b0-b666-de286db8e5ca`, range `[77,82)`, attempted
  exact `INFO\n` at 78, successful 5-byte acceptance at 79, then fixture
  `E_COMMAND_001` RX 80 and INFO-condition timeout terminal 81. Acceptance
  stopped. No retry, second INFO, manual reacquire, reset or resynchronization
  followed. The error response proves resumed transport RX, but does not satisfy
  the required deterministic INFO match. Cause remains unclassified; no
  reconnect/software defect, wire corruption or fixture/parser cause is claimed.
- Read-only final status/list/detail/evidence/log retrieval passed. Real CLI
  `loss=not_observable` and `Integrity: not_observable` agreed with API/native
  quality and log warning. Saved cursor retrieved 81 records from 1..81 to tail;
  initial connection 0 remains in native evidence. Final journal has 781 raw
  bytes, 20 RX records, 16 TX pairs, 10 terminal operations, three segments,
  two gaps and contiguous sequences 0..81; decoded RX matches raw exactly.
- Preserved full session/log copies, failure record, exact commands, timing,
  ownership, manifests and criterion results under
  `.dutchmate/hil/basic-acceptance-fresh-20261027/`; detailed report is appended
  to [Basic HIL validation](../hardware/validation/phase1_basic_hil.md).
  Normal stop required no SIGKILL. At 07:50:22.320058 UTC / 13:20:22 IST,
  PID 33018 was absent, no TCP 2040 listener remained and both FTDI paths were
  unowned. Journal state is `completed/service_shutdown`, not an acceptance pass.
  Earlier session hashes/configuration are unchanged. Only Basic report and
  status/history changed; final diff and preservation checks passed.

Phase 1A is incomplete because the required post-reconnect INFO failed; no
diagnosis or fix of the historical anomaly is claimed. Stage 8, Phase 1B and
overall Phase 1 remain incomplete. Enhanced HIL and MCP were not started.
Documentation changes remain uncommitted for review.


## Focused Basic E_COMMAND_001 Diagnosis: Unclassified — 2026-10-27

- Used clean pushed `stage8-phase1-acceptance`, HEAD
  `04f2ff28e47248bead99e9e3dc67d1af34bb693b`, independently matched by read-only
  HTTPS `ls-remote`. Inspected the current fixture UART line loop, protocol
  handler, Basic open/send adapter and installed pySerial 3.5 open code.
- The fixture retains non-CR bytes until LF, then clears length/discard state.
  Its 32-byte buffer and overflow-discard path can pass an unrecognized/empty
  command to the handler; INFO requires an exact length/content match. A prior
  non-CR prefix could explain a failing first command and successful second,
  but **no such bytes or live parser state were observed**. The firmware has no
  ingress echo/parser telemetry, and its protocol harness bypasses the live UART
  line assembler. Host input-buffer reset does not clear Pico parser state.
- Discovery identified FTDI FT231X `0403:6015`, serial `D358SG6A`, path
  `/dev/cu.usbserial-D358SG6A`, location `0-1.4`, on macOS 26.2/25C56, Darwin
  25.2.0 arm64. No service listener or serial owner existed. No analyzer was
  visible, and the operator confirmed no logic analyzer was available. Wire
  bytes, Pico ingress bytes and parser contents remained unobservable.
- Completed software checks before physical startup: 1,514 tests passed in
  37.39 s, Ruff passed, mypy passed (103 source files), offline lock check passed
  (66 packages), and `git diff --check` passed. Commands used prefix
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`, followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. No tests or second
  runtime/store ran during the physical service.
- One normal Basic start created session `20261027T071337Z-3be5f126`, PID 32203.
  Retained all serial/profile settings and reconnect 5.0 s. Made exactly two
  planned separate INFO Interacts using the existing INFO condition and 2 s
  bound, regardless of the first outcome; no operation retried TX. Both matched
  `DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1`.
- First request at 07:13:37.231648 UTC was 72.269166 ms after configured Basic
  source creation. Attempt/result 2/3, RX 4 and terminal 5 formed `[1,6)`.
  Second request at 07:13:38.188250 followed the first HTTP result by
  0.575875 ms (monotonic); attempt/result 7/8, RX 9, terminal 10 formed `[6,11)`.
  Each attempt was exact `494e464f0a` / `SU5GTwo=`, with one successful 5-byte
  result. Host RX before the first was empty and no earlier TX was audited in
  this new session; neither fact establishes what the Pico previously received.
- The new pair did not reproduce `E_COMMAND_001`. Prior errors remain unchanged:
  in `20261027T064604Z-7239cdfe`, RX 4 and 18 were read 29.128772 s and
  26.111850 s after their respective source origins. Those are host read times,
  not measurements of preceding Pico input. No idle-delay or parser workaround
  was tried. Classification remains **insufficient evidence / unclassified**;
  no DUTchMate, USB-UART, fixture/parser or electrical cause is assigned.
- Preserved requests/results, raw bytes, source review, prior-error review,
  before/after-stop native copies, service logs and hashes under
  `.dutchmate/hil/basic-command-diagnostic-20261027/`. Final native state is
  `completed/service_shutdown`; 148 raw bytes, two RX records, two TX pairs,
  two completed operations, one segment and contiguous evidence 0..10. Decoded
  RX matches raw byte-for-byte. All pre-existing session hashes and configuration
  bytes remained unchanged.
- Graceful public CLI stop completed. At 07:15:15.524773 UTC, PID 32203 was
  absent, TCP 2040 had no listener and both FTDI cu/tty paths were unowned.
  Only Basic validation/status/history changed. No production or fixture patch,
  parser/UART/deadline/acceptance change, firmware flash, USB reconnect or full
  Basic HIL was performed. Final diff and preservation checks passed.

Phase 1A, Stage 8, Phase 1B and Phase 1 remain incomplete. Enhanced HIL and MCP
were not started. Historical evidence is preserved; documentation changes remain
uncommitted for review.


## Focused Basic Unexpected-Reconnect Diagnostic — 2026-10-27

- Started from clean pushed `stage8-phase1-acceptance` HEAD
  `7d6cac3764176820f6dc62f79f2d705749735b24`; read-only HTTPS `ls-remote`
  independently matched. Reviewed CLI loss fix `ff8cc51` was already merged.
  Read current reconnect semantics, Phase 1 specification and Basic HIL record.
- Before physical startup, completed 1,514 tests in 36.83 s, Ruff, mypy (103
  files), offline lockfile check (66 packages), and `git diff --check`. Commands
  used `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. No tests or additional
  runtime/store construction occurred during either physical service interval.
- macOS 26.2/25C56, Darwin 25.2.0 arm64; FTDI FT231X `0403:6015`, serial
  `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, current USB location `0-1.4`.
  No service listener or serial owner existed at preflight. Configuration stayed
  byte-for-byte unchanged: reconnect 5.0 s, Basic/external UART/exact path,
  115200 8-N-1/no flow control, TX enabled, default ending none. Correct INFO
  responses identified reviewed build `basic-v2-20261026-7bc2ec377767`.
- Initial diagnostic session `20261027T063720Z-2c95d57d`, PID 3175, timed out
  after disconnect/start 6/7 at 06:44:18 UTC and failure 8 at 06:44:23. Its
  observer wait had expired at 06:44:03.879462 before physical action markers
  06:44:17.251883/06:44:34.144737, so USB/node timings were missed. This attempt
  remains unclassified. Its evidence, later successful post-timeout zero-byte
  external open and helper/precondition failures are preserved. A helper name
  shadowed Python's `operator` module before startup and was corrected locally;
  no product defect is inferred. Service stopped and listener/port were free
  before a fresh focused repeat. The operator-wait expiry was removed from the
  passive helper, without changing DUTchMate's five-second timeout.
- Fully observed repeat `20261027T064604Z-7239cdfe`, PID 18348, **successfully
  reconnected automatically**. Durable disconnect/start 11/12 were first observed
  06:51:47.546443 UTC; USB re-enumeration 06:51:48.560095; node reappearance
  06:51:48.565031; fresh segment/success 13/14 observed 06:51:49.091107. Observed
  start-to-success delta: **1.544660125 s**. Positive service FD observation was
  06:51:49.146319. The successful publication proves an actual in-window open.
- Kept the same active schema-v2 ownership session; fresh segment 1 has
  `start_reason=reconnect` and a new host-monotonic origin. One durable
  observation gap, unchanged profile/serial provenance, resumed RX and responsive
  connected status were verified. No manual reacquire or competing external
  open probe occurred during the automatic reconnect window.
- Operator markers, USB/node/stat/status/descriptor samples and durable evidence
  used paired UTC/monotonic timestamps. Sample bounds and native one-second wall
  resolution are explicit in the report. Physical mechanical contact instants,
  the exact successful open syscall return time and individual failed open
  attempts are not fabricated: existing logs do not expose each attempt, and
  password-free passive syscall tracing was unavailable. No root credentials,
  runtime monkeypatching or production instrumentation were used.
- **Command anomaly recurred:** exact audited INFO received `E_COMMAND_001` at
  RX 4 before unplug and RX 18 after reconnect; INFO-condition Interacts timed
  out. Separate explicit INFO retests matched at RX 9/23, without automatic TX
  retry. Resumed raw RX includes both the anomaly and the correct reviewed
  response. No software/fixture/wiring cause or fix is claimed.
- Preserved both new native sessions, before/after-stop copies, raw logs,
  commands, markers and timing summaries under
  `.dutchmate/hil/basic-reconnect-diagnostic-20261027/` (successful repeat in
  `repeat/`). Repeat evidence: 226 raw bytes, four RX records, four TX pairs,
  four completed operations, two segments, contiguous sequences 0..24; decoded
  RX matches raw exactly. Final state `completed/service_shutdown`, gap count 1.
- Public CLI stop completed normally. At 06:54:05.385913 UTC, PID 18348 was
  absent, no TCP 2040 listener existed and both FTDI cu/tty paths were unowned.
  All pre-existing session hashes and configuration bytes are unchanged. Only
  the Basic HIL validation record and development status/history changed;
  final diff/preservation checks passed. No production/test/hardware code was
  patched, no firmware flashed, and no full Basic HIL was run.

The measured repeat did not reproduce a reconnect defect; earlier timeouts
remain unclassified. This focused diagnostic is not Phase 1A acceptance.
Phase 1A, Stage 8, Phase 1B and Phase 1 remain incomplete. Enhanced HIL and MCP
were not started. Documentation changes remain uncommitted for review.


## Schema-v2 CLI Session Loss Display Fixed in Software — 2026-10-27

- Created `fix/cli-v2-loss-status` from clean, independently verified pushed
  `stage8-phase1-acceptance` HEAD `acffad49ec63765d827f83f2921a61a6a5220bab`.
  Read-only HTTPS `ls-remote` matched the local/tracking SHA. No future fix
  commit is assigned; changes remain uncommitted for review.
- Confirmed the current v2 API list/detail contract serializes
  `evidence_quality.backend_integrity.loss_status`. Both CLI views instead read
  v1's top-level `integrity`, explaining the preserved Basic HIL output
  `Integrity: none` / `loss=none` despite correct `not_observable` API evidence.
- Added RED regressions for both formatters: an ordinary native-v2 payload and
  one with a conflicting obsolete top-level projection. All four failed on
  the actual wrong output before implementation. The minimal formatter-only
  fix selects the v2 field for schema 2 and retains the historical source for
  older schemas. The v0 read-only branch and v1 output are unchanged; an added
  v1 detail check complements existing mixed v1/v0 list and v0 detail coverage.
- GREEN: all ten session CLI tests passed. A focused CLI/session-store/service
  retrieval/architecture gate passed 368 tests. Offline formatting of the actual
  preserved HIL API payload now prints `Integrity: not_observable` and
  `loss=not_observable`; this is software replay, not new physical acceptance.
- Only CLI formatting/tests and development status/history changed. Session
  persistence, API schemas, Basic backend, reconnect and hardware code were
  untouched. All 641 local `.dutchmate` file hashes matched before/after software
  checks, including failed HIL evidence. No serial port was opened, hardware
  accessed, firmware flashed or physical service started. Architecture ownership
  and interfaces did not change; no Graphify update was required.

Commands used prefix `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`
except the final Git check:

| Command | Result |
|---|---|
| `uv run --frozen pytest -q apps/cli/tests/test_sessions.py -k shows_v2_loss_status --tb=short` | RED: 4 failed, 6 deselected in 0.04 s |
| `uv run --frozen pytest -q apps/cli/tests/test_sessions.py --tb=short` | GREEN: 10 passed in 0.03 s |
| `uv run --frozen pytest -q apps/cli/tests tests/unit/session_store apps/service/tests/test_session_endpoints.py tests/architecture --tb=short` | 368 passed in 3.62 s, including architecture checks |
| `uv run --frozen pytest -q --tb=short` | 1,514 passed in 36.46 s |
| `uv run --frozen ruff check .` | Passed |
| `uv run --frozen mypy` | Passed, 103 source files |
| `uv lock --check --offline` | Passed, 66 packages; lockfile unchanged |
| `rtk proxy git diff --check` | Passed |

Phase 1A remains incomplete: unexpected FTDI reconnect is unresolved, and no
physical acceptance is claimed. Stage 8, Phase 1B and Phase 1 remain incomplete.
Enhanced HIL and MCP remain deferred. Historical HIL reports and earlier history
entries were preserved.


## Basic Release-Fix HIL Rerun: Handoff Passed, Acceptance Stopped — 2026-10-27

- Used clean `stage8-phase1-acceptance`, HEAD
  `21991fa403ad39f3100a24259b6f31a4c8ac1756`, containing reviewed release fix
  `df3ca29`. Independent read-only HTTPS `ls-remote` matched pushed HEAD after
  SSH authentication failed. No previous failed session was resumed or counted.
- Completed the full software gate before physical startup: 1,509 pytest tests
  passed in 36.77 s, Ruff passed, mypy passed (103 files), offline lockfile check
  passed (66 packages), and `git diff --check` passed. Exact commands used
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. Current CLI help was
  captured. No pytest, second service/runtime or session-store construction ran
  while the physical service was running.
- Reconfirmed Pico 1/H and all wiring/straps with the operator; independently
  enumerated FTDI FT231X `0403:6015`, serial `D358SG6A`, location `0-1.3`, at
  `/dev/cu.usbserial-D358SG6A`. No serial owner/listener existed. Reviewed UF2
  hash matched `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`.
  Exclusive preflight INFO returned the exact build and closed before startup.
  No hardware was flashed or firmware rebuilt; Zephyr v4.4.0/SDK 1.0.1 inputs
  remained the reviewed 115200 `rpi_pico` build.
- Physical service PID 5444 created new schema-v2 session
  `20261026T185908Z-a2a4fdef` at 18:59:08 UTC October 26 / 00:29:08 IST October
  27. Effective UART was 115200 8-N-1/no flow control, explicit TX enabled,
  default ending none, exact-path/external-UART profile, reconnect 5 s, 16 MiB
  budget and retention disabled. Profile digest remained
  `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
- Ambient operator RUN reset captured complete boot markers; INFO before and
  through service reported `basic-v2-20261026-7bc2ec377767`. The old physical
  `E_COMMAND_001` did not recur and is not declared fixed. Reset NULs and one
  interrupted banner remain raw evidence. Follow/display/detach, continued RX,
  duration/literal Monitor, exact audited TX, matched/elapsed/timeout Interact
  and unrelated async RX passed. Live service console displayed both PONG and
  INFO before EOF; later standalone RX proved continued acquisition.
- Dedicated delayed fault: ACK RX 44, durable Interact terminal 45, fault RX 46
  outside `[41,46)`, with 10,028,466 us ACK-to-fault host delta. No operation or
  view ran during the 11-second post-completion interval. Eight operations
  completed; each Interact had exactly one TX attempt/result and no retry.
- **Release regression did not recur physically:** final PONG RX 58, intent 59,
  released 60; CLI completed in 0.695716 s. Segment 0 closed, intentional gap
  counted, status responsive and physical ownership closed. External PID 5608
  acquired the same port, sent PARTIAL and received the exact response, then
  held ownership for 6 seconds while service stayed released. External close
  preceded reacquire 61/segment-open 62/success 63; fresh segment 1 and INFO RX
  67 passed. External response was correctly absent from service RX. A local
  driver assertion omitted the valid segment-open boundary; only that untracked
  assertion was corrected, with no product/test changes or physical retry.
- **Unexpected reconnect unsuccessful:** operator FTDI USB unplug produced
  disconnect 69/start 70 at 19:04:31 UTC, then timeout failure 71 at 19:04:36.
  Operator confirmed physical replug within about 1–2 seconds. Later discovery
  showed the same adapter/path; OS enumeration/open availability within the
  deadline was not measured. No automatic successor segment exists. Evidence
  does not establish a reconnect product defect versus physical availability;
  deadline was not enlarged and no further acceptance operation followed.
- **Confirmed product display defect at final retrieval:** CLI session/list
  show `Integrity: none` / `loss=none`, while the same API/native-v2 session
  reports `evidence_quality.backend_integrity.loss_status=not_observable`.
  `apps/cli/src/dutchmate_cli/sessions.py` reads obsolete top-level `integrity`
  for both displays. Saved actual CLI/API payloads establish the mismatch;
  logs/status/native evidence remain truthful. Acceptance stopped without a
  production fix. Session/list/detail/log/cursor retrieval itself succeeded.
- Preserved 725 raw bytes, 17 RX records, 15 successful TX pairs, eight completed
  operations, two segments and contiguous sequences 0..71. Decoded RX matches
  raw exactly. Full provenance, commands, operation ranges, criterion results,
  limitations and artifact hashes are appended to
  [Basic HIL validation](../hardware/validation/phase1_basic_hil.md); raw/copy/
  command evidence is in `.dutchmate/hil/basic-release-rerun-20261027/`.
- Earlier failed-run reports/copies remain intact. Normal startup recovered
  stale `20261026T175336Z-3d1dd5a9` metadata to `abandoned/service_restart` and
  removed its reserve; original metadata/reserve hashes still match the
  previous preserved copies. Its RX/action/connection evidence and session
  `20261026T134413Z-e8d17b99` are unchanged; this is not hidden as unchanged live
  stale metadata.
- Graceful public CLI stop succeeded without SIGKILL. OS verification at
  `2026-10-26T19:06:49.366247Z` found PID 5444 absent, no TCP 2040 listener and
  no FTDI cu/tty owner. No production, test, fixture or configuration change was
  made. Final documentation diff and append-only preservation checks passed.

Phase 1A, Stage 8, Phase 1B and Phase 1 remain incomplete. No new acceptance was
declared. Enhanced HIL and MCP work were not started. Only the Basic HIL report
and development status/history changes remain uncommitted for review.


## Basic Release Terminal/FIFO Race Fixed in Software — 2026-10-26

- Worked from clean `fix/basic-release-lifecycle`, baseline
  `b4ad4f32c138a42f255110dc222c1258723cc138`, containing the failed Basic HIL
  report. The real service was stopped. No serial device, firmware flash,
  physical service, Basic/Enhanced HIL, or MCP work was accessed or started.
  Both diagnostic sessions, including `20261026T175336Z-3d1dd5a9`, are unchanged.
- Traced the full release path against actual source and the Stage 7 contract:
  sync `POST /connection/release` → runtime `_ownership_change` arbitration →
  coordinator manual claim/suspend → recorder durable `release_requested` →
  Basic source stop/serial close/reader join/final wakeup → recorder drain →
  line flush → durable `released` transaction closing the segment/counting its
  intentional gap → final released-state publication and lifecycle-claim release.
  One Graphify query with budget 1600 supported impact navigation (its output
  was truncated); important relationships were verified directly in source.
- **Exact blocking cause:** after serial close and reader termination, the
  consumer can observe empty FIFO/EOF and cache `_terminal_error` before close
  enqueues `_SourceClosed`. The next `_next_event` raised the cached error
  without consuming the newly queued wakeup. `has_pending_events` stayed true,
  `_finish_release_drain` could not set `_release_drained`, and release waited
  indefinitely. No `released` transaction or final ownership state was reached.
  Runtime mutation/lifecycle ownership stayed held, blocking shutdown; repeated
  raises of the same exception accumulated traceback frames, consistent with
  the preserved process sample's large footprint and later unresponsiveness.
- **Minimal fix:** replay cached terminal errors only once the FIFO is empty,
  allowing normal consumption of a late close wakeup. Consuming that wakeup
  preserves an existing reader/input failure instead of overwriting its
  diagnostic with generic EOF. No queue is cleared, no RX is discarded, no
  physical-close confirmation is bypassed, and no HTTP/release timeout changes.
  Runtime/coordinator/recorder/store code and interfaces are unchanged.
- **RED:** three real Basic async-source cases failed because the late wakeup
  remained pending after terminal delivery (EOF, serial-read failure, invalid
  timestamp input). The HTTP regression exercised real startup, Basic reader,
  recorder, coordinator, runtime and endpoint with a controlled serial surrogate:
  durable intent preceded close, physical ownership closed, final RX drained,
  but the release request failed its one-second completion assertion. Event
  barriers force the real EOF-before-wakeup ordering; test-only failed-baseline
  rescue resets the error latch after failure so teardown consumes the queue
  normally, avoiding a runaway spin or a hanging pytest process.
- **GREEN:** ten new cases pass (three source, seven service). The success case
  proves exact ambient/final RX preservation, durable segment end and one gap,
  prompt HTTP return, responsive released status, same-session reacquire with a
  fresh segment and RX, and clean recorder/reader/coordinator shutdown. Other
  cases cover cancelled HTTP release, cancellation plus concurrent shutdown,
  direct shutdown with the same late-wakeup ordering, physical-close error, and
  failures persisting either release intent or the released boundary. Errors
  remain faulted rather than claiming released, and lifecycle claims/threads
  settle; busy arbitration remains effective until an accepted release settles.
- All four architecture checks and existing Stage 7 operation/ownership/error
  tests passed in the focused gate. No architecture ownership or shared port
  changed, so an architecture rewrite or Graphify update was unnecessary.
- Before/after SHA-256 inventories of all 521 real `.dutchmate` files matched,
  including preserved HIL sessions/sample. The Basic HIL validation record and
  older development history were not rewritten. Working implementation notes
  were temporary; durable diagnosis and evidence are recorded here.

Validation (all hardware-free, physical service stopped):

| Command | Result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q tests/unit/backends/test_basic.py -k drains_wakeup` | RED: 3 failed on pending wakeups; GREEN: 3 passed in 0.05 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q apps/service/tests/test_basic_release.py -k http_release_drains --tb=short` | RED: request never completed after confirmed close/drain, 1 failed in 1.38 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q apps/service/tests/test_basic_release.py tests/unit/backends/test_basic.py --tb=short` | GREEN: 26 passed in 1.27 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q apps/service/tests tests/unit/backends tests/unit/evidence tests/unit/runtime/test_connection_ownership.py tests/architecture --tb=short` | 345 passed in 8.37 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,509 passed in 37.62 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 source files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed; 66 packages; lockfile unchanged |
| `rtk proxy git diff --check` | Passed |

The software fix is reviewed and accepted. Phase 1A and Stage 8 remain incomplete;
the complete Basic HIL procedure must be rerun after integration of
this fix. Phase 1B/Phase 1 are incomplete, Enhanced HIL was not started, and MCP
remains deferred. No physical INFO-anomaly diagnosis or acceptance claim was made.


## Clean Basic Phase 1A HIL Stopped on Release Failure — 2026-10-26

- Restarted from clean `stage8-phase1-acceptance`, HEAD/upstream tracking ref
  `ad8b63abc3c9330864eaa49cb48aab57cd03f2cd`, containing merged isolation fix
  `7f30a916a3033289dec6908ebeac17a687c0d806`. The former failed session
  `20261026T134413Z-e8d17b99` was neither resumed nor counted; its hashes stayed
  unchanged. Current normative section 33, developer CLI guide, fixture README,
  and Basic validation history were read before hardware startup.
- Completed all software checks with the real service stopped: pytest 1,499
  passed in 35.84 s; Ruff passed; mypy passed (103 files); offline lock check
  passed (66 packages); diff check passed. No pytest, extra application/runtime,
  or session-store construction ran after physical service startup. CLI/HTTP
  clients and read-only JSON/artifact inspection were used during HIL.
- FTDI FT231X `0403:6015`, serial `D358SG6A`, was identifiable at
  `/dev/cu.usbserial-D358SG6A`, USB location `0-1.3`; no preflight owner existed.
  Retained operator-confirmed Pico 1/H wiring and reviewed flash. Independently
  rehashed UF2 to `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`.
  No firmware was rebuilt or flashed. Actual first INFO returned
  `basic-v2-20261026-7bc2ec377767`, with no `E_COMMAND_001` in any new raw RX.
- Real Basic service PID 3451 started at 17:53:36 UTC (23:23:36 IST), creating
  fresh native-v2 session `20261026T175336Z-3d1dd5a9`. Effective UART/profile
  remained 115200 8-N-1, no flow control, explicit TX enabled, driver-default
  DTR/RTS; host-observation timestamps and Basic `not_observable` loss were
  truthful. Profile digest remained
  `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
- Ambient RUN-reset boot bytes were preserved without operation/view ownership.
  Follow displayed PONG, Ctrl-C detached only the view, and INFO RX continued.
  Duration/literal Monitor passed. Interact matched/elapsed/timeout outcomes
  and exact ranges were recorded with one TX each. A PING Interact retained an
  unrelated fault from an earlier DELAYFAULT command. The dedicated DELAYFAULT
  Interact ACK was RX 46, durable matched terminal 47, and later fault RX 48,
  outside range `[43,48)`; ACK→fault host timestamp difference 10,034,749 us.
  No bounded operation or view ran during its 11-second idle interval.
- Service-backed console sent PING/INFO with LF, retained TX/RX audit, and
  acquisition continued after EOF. Pre-release retrieval worked through detail,
  logs and the durable evidence cursor. The saved session had 590 raw bytes,
  16 RX records, 13 successful TX attempts/results, seven completed operations,
  and contiguous evidence sequences 0..57. Two expected synthetic ASYNC fault
  patterns were retained; TX request bytes were absent from RX raw.
- `dutchmate release` began at 17:58:26.789445 UTC, persisted
  `release_requested` sequence 57, then timed out after 65.161843 seconds.
  No `released` boundary appeared. A subsequent status initially remained
  connected; later status requests timed out. The guarded external-owner script
  stopped in its status precondition before `serial.Serial` was called; no
  external reader/consumer or concurrent serial ownership occurred.
- Stopped acceptance per failure policy. Read-only source tracing and macOS
  `sample 3451 1 1` were captured without injecting code or constructing a
  store. Physical serial ownership had closed, but the process remained live;
  the sample reported 11.8G physical footprint. The precise internal failure
  mechanism remains unconfirmed. No production/fixture/test patch was made.
- Public CLI stop sent SIGTERM but the process stayed alive. After preserving
  the session and validating PID/command identity, SIGKILL terminated only the
  owned HIL service. Verified process absent, no HTTP listener, and no FTDI
  owner. Preserved metadata remains stale `active`, with no synthetic terminal
  or release-gap record added after the fact. Both pre-stop/final copies and
  SHA-256 manifests are in `.dutchmate/hil/basic-clean-20261026/`.

Pre-hardware validation commands (all completed before service start):

| Command | Result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,499 passed in 35.84 s; architecture/isolation/recovery/fixture checks included |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed; 66 packages |
| `rtk proxy git diff --check` | Passed before hardware startup and for final docs |

Exact client commands, all operation IDs/ranges, hardware/provenance, release
failure reproduction, cleanup, and per-criterion outcomes are appended to
[Basic HIL validation](../hardware/validation/phase1_basic_hil.md). No new
runtime or physical reproduction was attempted after the release failure.
Basic Phase 1A remains incomplete because handoff/reacquire and unexpected
reconnect were not proven. Stage 8, Phase 1B, and Phase 1 remain incomplete;
Enhanced HIL and MCP were not started. HIL documentation remains uncommitted
for review; previous historical records and diagnostic evidence are preserved.


## Service-Test Session-Store Isolation Fix Validated — 2026-10-26

- Worked on clean `fix/service-test-session-isolation`, starting at
  `5b2cec1769773edde9ba2503e13c8929f8080809`, matching the local
  `stage8-phase1-acceptance` and `origin/stage8-phase1-acceptance` baseline
  containing the preserved failed HIL report. A direct remote SHA requery was
  unavailable because SSH authentication still returned `Permission denied
  (publickey)`; no branch/remote history was changed.
- Root cause: these three `apps/service/tests/test_errors.py` tests create real
  application runtimes with an implicit `.dutchmate/sessions` root:
  `test_exception_handlers_return_json_error_response`,
  `test_input_validation_handler_returns_json_error_response`, and
  `test_exception_handlers_preserve_firmware_error_code`. App startup intentionally
  recovers stale sessions; tests were applying that recovery to developer state.
- Audit before implementation:

  | Boundary inspected | Finding |
  |---|---|
  | All service `create_app` calls | Three unsafe error tests; three lifecycle calls replace the runtime builder; other calls inject runtimes or explicit temporary roots |
  | Service `build_startup_runtime` / `SessionStore` calls | Explicit temporary roots, including recovery-order tests; no additional unsafe persistent root found |
  | Service entrypoint/config | Relative default config and session paths; entrypoint test uses a temporary config and fake app/server |
  | Session listing/baseline/retention service tests | Injected stores rooted in test temporary directories |
  | Complete-suite app/store/startup call and `.dutchmate` path search | Other application calls inject runtimes; store/recovery tests use explicit temporary roots |
  | CLI config/PID/log boundaries | Existing CLI autouse fixture replaces default config loading; direct config tests use temporary files; lifecycle tests use fake process/health/kill seams and temporary PID/log files |

- Added `apps/service/tests/conftest.py`: an autouse fixture changes each service
  test's working directory to its own `tmp_path`. Existing relative config,
  session, PID, and log defaults resolve inside that test; explicit temporary
  roots and injected runtimes continue working. No production function,
  configuration default, recovery/retention policy, or hardware behavior changed.
- Added `test_state_isolation.py`: a real subprocess runs the affected error
  tests and a default-root write/recovery probe from a temporary developer
  directory containing an unrelated active schema-v2 sentinel plus config,
  PID, and log files. The sentinel remains active with null terminal fields;
  all file bytes and mtimes, including evidence/connection files, stay unchanged.
  The test app writes/retrieves its own recovered session under isolated state.
  Two parameterized cases separately preserve real stale-session recovery for
  implicit and explicit test roots, including raw RX/event preservation.
- RED: before isolation, the regression failed because the sentinel became
  `abandoned`; the explicit-root recovery control passed. The final regression
  was also rerun with the shared fixture temporarily removed and failed at the
  same active-state assertion. GREEN after restoring the fixture: 3 passed in
  0.52 s, including both production recovery cases.
- Confirmed no service listening on the known HIL endpoint before running
  checks. No service process was started, no serial device opened, and no
  hardware/HIL, Enhanced HIL, or MCP work occurred. Compared SHA-256 inventories
  of all 424 real `.dutchmate` files before/after validation; no file was added,
  removed, or changed. The failed Basic HIL report and original/preserved session
  `20261026T134413Z-e8d17b99` remain untouched. The earlier physical INFO anomaly
  was neither investigated nor reclassified in this slice.

Validation (repository root, physical service stopped):

| Command | Result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q apps/service/tests/test_state_isolation.py` | RED before isolation; GREEN 3 passed in 0.52 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q apps/service/tests tests/unit/session_store/test_recovery.py tests/unit/session_store/test_v2_persistence.py tests/architecture` | 214 passed in 7.24 s; service startup and all four architecture checks included |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,499 passed in 37.13 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 source files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed; 66 packages; lockfile unchanged |
| `rtk proxy git diff --check` | Passed |

Basic HIL must
still be rerun from the beginning; this software result grants no physical
acceptance. Phase 1A, Stage 8, Phase 1B, and Phase 1 remain incomplete, Enhanced
HIL was not started, and MCP remains deferred. Graphify/architecture changes
were unnecessary for this test-only isolation boundary.


## Basic Phase 1A HIL Stopped After Test-Isolation Interference — 2026-10-26

- Began from clean `stage8-phase1-acceptance`; HEAD and its upstream tracking
  ref both named `b3f850a4b71cc80c2081fb24f5f151ea01625c84`, confirming the
  operator's push. Fixture source baseline remains `746121a`. Operator-confirmed
  Pico 1/H flash/wiring were retained; independent UF2 SHA-256 again matched
  `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`.
- Real Basic service PID 7478 connected to FTDI FT231X `0403:6015`, serial
  `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, 115200 8-N-1, no flow control,
  explicit TX enabled. One service-owned serial descriptor was observed.
  Session `20261026T134413Z-e8d17b99` started at 13:44:13 UTC (19:14:13 IST).
  Effective profile digest:
  `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
- First exact `INFO\n` Interact returned timeout because the fixture emitted
  `DMF/1 ERROR COMMAND code=E_COMMAND_001\n`. It had one TX attempt/result,
  without retry. A separately requested audited INFO send returned the exact
  reviewed build ID. The initial fixture-path rejection remains unexplained;
  no host TX defect was established from it.
- The agent then incorrectly ran the full suite while the physical service
  was active. Three `apps/service/tests/test_errors.py` tests call `create_app()`
  without a temporary session root. `create_app` calls `build_startup_runtime`,
  which recovers the real default `.dutchmate/sessions` even without a profile.
  The live session was marked abandoned with `service_restart` at 13:46:37 UTC.
  Following the operator's requested RUN reset, boot bytes were not persisted;
  the next duration Monitor returned HTTP 503 and status was `faulted`.
- Acceptance stopped. Read-only tracing found the default-store recovery path.
  A standalone reproduction used synthetic Basic sessions in two temporary
  directories: `TestClient(create_app())` changed each active session to
  abandoned, then RX append raised `ValueError: schema-v2 evidence can only
  append while active`. No serial or original session was touched by that
  reproduction. This establishes a service-test isolation defect, rather than
  a physical wiring failure or a normal single-owner RX failure. No production,
  fixture, or tracked test fix was made during acceptance.
- Preserved all 113 raw bytes, two RX records (sequences 4, 8), six operation
  records, metadata, and command/status outputs. Decoded RX exactly equals raw;
  requested TX `INFO\n` is absent from receive-only raw. The service was stopped
  through the public CLI, no port owner remained, and original/preserved hashes
  still matched. Evidence is under `.dutchmate/hil/basic-phase1a-20261026/`;
  the original session remains under `.dutchmate/sessions/`. Full criterion and
  command records are appended to the Basic HIL validation document.

Fresh software checks performed during this attempt:

| Command | Result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,496 passed in 36.01 s; concurrent default-root test side effect invalidated physical HIL |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 files |
| `rtk proxy .venv/bin/python .dutchmate/hil/basic-phase1a-20261026/reproduce_test_isolation.py` | Reproduced active→abandoned→RX append rejection twice in temporary directories |
| `rtk proxy git diff --check` | Passed for final documentation |

No real follow, successful Monitor, delayed-fault ordering, console, handoff,
rollover, or unexpected reconnect claim was made. Stage 8, Phase 1A, Phase 1B,
and Phase 1 remain incomplete. Enhanced HIL and MCP work were not started.
New HIL documentation was left uncommitted for review, with earlier records
preserved. No hardware was flashed by the agent.


## Operator Confirmed Basic Setup; Acceptance Paused for Push — 2026-10-26

- Read-only inventory at `2026-10-26T19:08:29.149606+05:30` again identified
  FTDI FT231X `0403:6015`, serial `D358SG6A`, at the expected cu path; the
  reviewed UF2 SHA-256 still matched exactly. Current CLI help/configuration
  were inspected; `lsof -nP /dev/cu.usbserial-D358SG6A /dev/tty.usbserial-D358SG6A`
  listed no owner. No serial open or HIL operation occurred.
- The operator confirmed that the Pico 1/H had the reviewed
  `basic-v2-20261026-7bc2ec377767` image flashed and all requested Basic wiring,
  3.3 V logic, separate USB power, disconnected FTDI VCC, and open GP2/GP3
  matched. This is operator provenance, not an observed boot/INFO response.
- The SSH push retry failed with `Permission denied (publickey)`. The operator
  requested waiting for their push before Basic HIL, then requested committing
  the remaining branch documentation. No fixture/production source changed;
  all acceptance gates remained incomplete. Documentation diff validation
  passed; software checks were not rerun for documentation-only changes.


## Reviewed Basic Fixture Committed; Push/BOOTSEL Preflight Blocked — 2026-10-26

- Finalized only current review-state wording; preserved earlier dated reports
  and the reviewed fixture source snapshot. `git diff --check` and staged diff
  checks passed. Committed the nine reviewed fixture/preflight files on
  `stage8-phase1-acceptance` as
  `746121a35633c070f4e7112010ce26b656d8ef1d`, subject
  `test(hardware): prepare Basic Phase 1 HIL fixture`.
- `rtk proxy git push origin stage8-phase1-acceptance` failed with
  `Permission denied (publickey)`. Escalated `rtk proxy ssh-add -l` reported
  `The agent has no identities.` An HTTPS retry using existing credentials,
  `rtk proxy env GIT_TERMINAL_PROMPT=0 git push https://github.com/leonahi/DUTchMate.git stage8-phase1-acceptance:stage8-phase1-acceptance`,
  failed with `could not read Username for 'https://github.com': terminal prompts
  disabled`. GitHub CLI was unavailable. No remote URL/configuration changed;
  the commit remains local, not pushed. These are authentication failures, not
  automatic approval-review rejections.
- Read-only preflight at `2026-10-26T19:02:24.994058+05:30` independently
  recomputed the reviewed UF2 SHA-256 and required an exact match. FTDI FT231X
  `0403:6015`, serial `D358SG6A`, remained present at the intended path.
  `/Volumes` contained only `Macintosh HD`; no `INFO_UF2.TXT` or `RPI-RP2`
  volume was found. No flash or serial open was attempted.
- Detailed identity, command, physical-blocker, and criterion results are
  appended to [Basic HIL validation](../hardware/validation/phase1_basic_hil.md).
  No DUTchMate software defect was observed; no v2 session or runtime criterion
  result exists. Stage 8/Phase 1A/Phase 1B/Phase 1 remain incomplete. Enhanced
  HIL and MCP work were not started. Post-commit HIL blocker documentation was
  left uncommitted; final documentation `git diff --check` passed. No source
  behavior or production code changed during this finalization/preflight.


## Basic Delayed-Fault Fixture Prepared, Not Flashed — 2026-10-26

- Stayed on `stage8-phase1-acceptance`, HEAD
  `e8f9e6186e92d6898f011cf8853e1071d0e62f01`. Preserved the three existing
  uncommitted documentation changes and all FTDI discovery/historical evidence.
  No commit/push, production DUTchMate change, serial open, hardware flash,
  Basic/Enhanced HIL, MCP migration, or acceptance-status completion occurred.
- Added fixture command `DELAYFAULT`: exact immediate ACK
  `DMF/1 DELAYFAULT armed delay_ms=10000\n`; the next main-loop poll starts a
  10,000 ms monotonic deadline after command completion. The first due poll
  emits `DMF/1 ERROR ASYNC code=E_ASYNC_001\n` once, without another command.
  UART polling remains responsive. Rearming replaces the deadline; SILENT/reset
  cancels it. Existing blocking load commands can postpone the poll, as documented.
- Extended the portable C harness with deterministic virtual-time scenarios.
  First observed the missing-command regression fail with `E_COMMAND_001`;
  after adding the poll API, deadline/rearm tests failed for missing fault output
  before the deadline implementation. Final fixture suite: 17 passed. Existing
  boot/PING/INFO, silent/failure, binary/partial, burst/sustained tests still pass.
- Source snapshot SHA-256:
  `7bc2ec377767b1b7fa12fe0766ff0a882d42fc2c315bbfe68f503a3ab5c9d1d6`.
  This hashes sorted fixture file paths relative to the fixture directory, NUL,
  file bytes, NUL; README is excluded. It includes the unused Enhanced overlay
  as source inventory only; no overlay was selected for this build.
- Immutable build ID: `basic-v2-20261026-7bc2ec377767`.
  Actual Zephyr checkout: clean tag `v4.4.0`, commit
  `684c9e8f32e4373a21098559f748f06915f950c9`; SDK `1.0.1`, GNU compiler
  `14.3.0`, west `1.3.0`. Host remains macOS 26.2 arm64.

Successful build command, from repository root:

```bash
rtk proxy env \
  ZEPHYR_BASE=/Users/nahitpawar/zephyrproject/zephyr \
  ZEPHYR_SDK_INSTALL_DIR=/Users/nahitpawar/zephyr-sdk-1.0.1 \
  CCACHE_DIR=/tmp/dutchmate-basic-ccache \
  /Users/nahitpawar/zephyrproject/.venv/bin/west build \
  -b rpi_pico -s hardware/firmware/zephyr_dut \
  -d build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767 --pristine -- \
  '-DCONFIG_DUTCHMATE_FIXTURE_BUILD_ID="basic-v2-20261026-7bc2ec377767"' \
  -DDTC_OVERLAY_FILE= -DEXTRA_DTC_OVERLAY_FILE= \
  -DUSER_CACHE_DIR=/tmp/dutchmate-basic-zephyr-cache
```

The initial build attempt used `XDG_CACHE_HOME` instead of `USER_CACHE_DIR`;
Zephyr still selected its external `.cache` and failed writing compiler capability
cache files. Retrying with the explicit CMake cache path above succeeded without
escalation or changing fixture/toolchain source.

| Artifact/check | Result |
|---|---|
| UF2 | `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/zephyr/zephyr.uf2`, 34,816 bytes |
| UF2 SHA-256 | `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16` |
| `.config` SHA-256 | `9bcb30687dd409d62d90fd083c2ebd208e432b54f4007801722a6677c02b714c` |
| ELF SHA-256 | `aa011e9bb29131acdba6bf9d588b51e4b9f719b48d9c5fed11bee8078317b0c1` |
| Generated board/UART | `rpi_pico/rp2040`; chosen UART0 `/soc/uart@40034000`, `current-speed=115200`, `hw-flow-control=false`, parity none; PL011 initializer selects 8 data bits/1 stop bit |
| Overlays | Both CMake overlay settings empty; default board configuration |
| Linked behavior | Final ELF `main` calls `dmf_fixture_poll`; image contains exact command, ACK, fault, boot/INFO format strings, and build ID |
| UF2 integrity | Validated block magic/length/count, flash origin `0x10000000`; decoded payload matches `zephyr.bin` |
| Boot/INFO identity | Host-compiled exact protocol source with generated `autoconf.h` returned exact `basic-v2-20261026-7bc2ec377767` in both markers; not on-device execution |
| Build resources | BOOT_FLASH 256 B; FLASH 17,072 B; RAM 4,952 B |

Detailed per-source and artifact digests plus identity results are retained locally
in `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/fixture-build-report.json`;
compiled main disassembly is in that build's `zephyr/main-disassembly.txt`.
Build outputs are ignored artifacts, not tracked source changes.

Validation commands/results:

| Command | Result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q tests/hardware/zephyr_dut/test_fixture_protocol.py` | 17 passed in 4.65 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,496 passed in 39.83 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 source files |
| `rtk proxy git diff --check` | Passed |

Fixture README documents the later two-second Interact matching the ACK, idle
interval, and required durable operation-complete-before-fault evidence ordering.
That workflow was documented only, not executed. No current v2 HIL session exists.
The fixture preparation passed review. Graphify/architecture updates were not
needed for this localized fixture change; no module/layer ownership changed.


## Basic Adapter Attachment and Fixture Readiness Check — 2026-10-26

- At `2026-10-26T17:18:42.594713+05:30`, read-only serial enumeration identified
  FTDI FT231X `0403:6015`, serial `D358SG6A`, at
  `/dev/cu.usbserial-D358SG6A`, USB location `0-1.4`.
- The user requested fixture firmware guidance before HIL. Inspected the
  documented Basic fixture settings and existing local DUT build artifacts;
  only the 460800-baud Enhanced fixture UF2 was found. Recorded its digest and
  generated build identity in the Basic HIL report. The existing source lacks
  the required delayed-fault behavior; no fixture changes were made.
- No port open, service start, build/flash, or HIL operation occurred; no new
  session or acceptance result exists. Preserved earlier uncommitted reports.
  Enhanced HIL and MCP migration were not started.


## Basic Phase 1A v2 HIL Preflight Blocked — 2026-10-26

- Scope: Basic HIL only on the pushed `stage8-phase1-acceptance` branch.
  HEAD and the local upstream tracking ref both named
  `e8f9e6186e92d6898f011cf8853e1071d0e62f01`; initial working tree/index were
  clean. No fetch, commit, or push was performed.
- Read the current normative acceptance criteria, developer guide, existing
  hardware records, and fixture documentation/protocol source before discovery.
  At `2026-10-26T17:03:49.953709+05:30`, macOS 26.2 (`25C56`), Darwin 25.2.0
  arm64 enumerated only Bluetooth/debug-console serial ports without USB
  metadata. The USB tree showed two GenesysLogic hubs, no identifiable
  USB-UART or Pico. `/Volumes` contained only `Macintosh HD`.
- Stopped before any port open, service start, build/flash, or acceptance
  operation. Adapter/DUT identity, flashed Zephyr/build identity, wiring,
  effective profile/serial provenance, and target-port ownership were not
  established. No session IDs or physical acceptance evidence were created.
- Appended exact discovery commands, observed identities, all section-33
  criterion dispositions, and fixture-source limitations to
  [the Basic HIL record](../hardware/validation/phase1_basic_hil.md#phase-1a-v2-basic-preflight-attempt--2026-10-26).
  All physical criteria are untested; no DUTchMate software defect was diagnosed.
  Historical reports were preserved, and all acceptance statuses are unchanged.
- Documentation-only verification: `rtk proxy git diff --check` and comparison
  against HEAD for preserved historical text passed. Software checks were not
  rerun. Changes were left uncommitted for review. Enhanced HIL and MCP migration
  were not started.


## Stage 8 Software Acceptance and Hardware Availability Audit — 2026-10-26

- Work was scoped to Stage 8 in DUTchMate only. Clean `main` and its upstream
  tracking ref both named `9a228fcc37d746241c4624469cf3d18b4a7fab4a`.
  Created `stage8-phase1-acceptance`; software acceptance passed review.
  No MCP source, firmware, wire schema, or historical hardware evidence changed.
- Enhanced parity required no firmware/protocol redesign. A new test drives the
  real NDJSON parser, async serial adapter, owner-loop host, startup composition,
  continuous recorder, runtime, and v2 store through idle RX, interleaved command
  responses, exact TX/Interact, audited reset/boot configuration, immediate boot
  bytes before later Monitor, overflow/status telemetry, release/reacquire, and
  per-segment RP2350 provenance. Generic wire commands exclude role/DUT-signal
  metadata. Existing protocol/firmware safety and EVENTn tests remain in the gate.
  The historical ring-buffer decision remains `accepted_32k`; no new ring-buffer
  measurement or acceptance claim was made.
- New Basic/Enhanced CLI acceptance invokes the actual Typer CLI and HTTP client
  against the real FastAPI service/runtime/store with controlled normalized
  backends. It covers status, Monitor duration/condition, exact binary TX,
  condition Interact, a later ambient HardFault with a 30-second source timestamp
  advance, follow interrupt/detach, service-only console TX, GPIO/reset/boot where
  supported, durable retrieval/list/detail/logs, and release/reacquire with an
  explicit segment/gap. Existing suites cover rollover/reconnect/retention and
  persistence-fault shutdown; no wall-clock 30-second delay was substituted for
  actual HIL evidence.
- Reference/impact inventory before deletion:

  | Retired path | Remaining consumers found | Disposition |
  |---|---|---|
  | `SessionStore.create_session` and v0/v1 append/control/TX/reconnect writers | Core compatibility, service retrieval/baseline, Debug Agent fixture tests only | Removed from production; frozen fixture construction moved to `tests/support/legacy_*` |
  | Legacy metadata/event writer projections | Those writers only | Moved to the same test-only fixture boundary; shared reader/projection helpers retained |
  | Coordinator finite-workflow callable/retry path and retry injection | Obsolete active-capture tests; runtime used only `close` | Removed; runtime now depends on `ReconnectLifecycle.close`; continuous worker and manual handoff retained |
  | Adapter/host `discard_pending_events` | Discard-specific tests/fakes only | Removed with obsolete tests; continuous queue/drain coverage retained |
  | `CaptureReconnectError`, host `capture_active`, `active_workflow` | Legacy mappings/status/fixtures only | Removed; status displays `active_operations`, host conflicts use `operation_active` |
  | Capture/wait response and CLI-format fallbacks | Old fake workflow results only | Removed; documented aliases serialize/display only Monitor results |
  | `_capture_in_progress`, finite capture/session owner, workflow FIFO, live force send | Already absent from current host runtime | Confirmed absent; explicit rejection tests remain |

- Read-only boundary correction: regression tests first demonstrated that startup
  could abandon v1 and that lifecycle calls could rewrite it. Production now
  classifies schema before transaction recovery, skips v0/v1 bookkeeping unchanged,
  and rejects legacy terminal writes. Recovery fault/transaction tests exercise
  v2. Historical readers/replay and recognized wire error vocabulary remain.
  Normal schema-specific retention/baseline policies were preserved.
- Thirty-one tests for retired workflow/discard/legacy-response behavior were
  removed; seven new acceptance/read-only/Debug Agent regressions were added.
  Other legacy compatibility tests retain their data through explicit test-only
  builders, which are absent from production wheels. This accounts for the full
  suite changing from 1,515 to 1,491 tests.
- Debug Agent schema-v1 fact/evidence tests remain healthy. A new regression
  confirms v2 returns `unsupported_session_schema` without mutating evidence;
  full v2 evidence-package migration was not performed. README/developer guide
  make this limitation explicit. Reconnect documentation now describes current
  continuous ownership instead of the superseded finite-workflow contract.

Validation commands (run from repository root; `rtk proxy` preserves command
semantics and output):

| Command | Observed result |
|---|---|
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q` | 1,491 passed in 39.58 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen pytest -q tests/architecture tests/unit/session_store/test_legacy_read_only.py tests/unit/backends/test_stage8_enhanced_parity.py tests/unit/runtime/test_phase1_cli_acceptance.py apps/service/tests/test_monitor_endpoint.py apps/cli/tests/test_monitor_command.py apps/debug_agent/tests/test_session_facts.py` | 23 passed in 1.36 s |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen ruff check .` | Passed |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen mypy` | Passed; 103 source files |
| `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline` | Passed; 66 packages; lockfile unchanged |
| `rtk proxy uv build --package dutchmate-debug-agent --out-dir /tmp/dutchmate-stage8-dist --offline` | sdist and wheel built successfully |
| `rtk proxy uv build --package dutchmate-core --out-dir /tmp/dutchmate-stage8-dist --offline` | sdist and wheel built successfully |
| `rtk proxy graphify query 'session_store create_session capture runtime' --budget 1800` | Focused impact navigation; verified writer callers and runtime/reconnect boundaries against source/reference searches |
| `rtk proxy graphify update .` | Refreshed structural index; 5,667 nodes, 14,676 edges, 289 communities; existing partial-extraction warning for `hardware/firmware/zephyr_dut/src/fixture_protocol.h` and community-label notice |
| `rtk proxy git diff --check` | Passed |

The temporary writable uv cache initially lacked `uv-build`, so the first offline
Debug Agent build could not resolve its build backend. The successful build
commands above used the existing user cache with sandbox escalation; no dependency
or lockfile change was needed. Wheel inspection found 21 Debug Agent files and 74
core files, with no test fixture builders. Import Linter is not configured;
executable architecture checks are part of both focused and full pytest gates.
Reference searches confirmed no production legacy create/append API, discard API,
finite-workflow retry, single-workflow status, or host capture-exclusion error.
The Enhanced wire schema's recognized `capture_active` error remains a protocol
compatibility value, not host arbitration. Deferred MCP files were untouched.

After the software gate passed, a read-only hardware availability inventory ran:
`rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen --package dutchmate-service python -`
with `serial.tools.list_ports.comports()` projecting device, description, HWID,
VID/PID, serial number, manufacturer, and product. At
`2026-10-26T03:47:57.412758+00:00` (09:17:57 IST), macOS 26.2 arm64 reported only
`/dev/cu.debug-console` and `/dev/cu.Bluetooth-Incoming-Port`; all USB identity
fields were null and description/HWID were `n/a`. No serial port was opened.

- **Basic HIL:** not run; no identifiable generic USB-UART + Zephyr Pico 1 fixture.
- **Enhanced HIL:** not run; no identifiable RP2350/Pico 2 Debug Helper + same DUT
  fixture. Firmware/build identity and physical wiring could not be established.
- No new HIL session IDs, measured overflow, boot timing, leakage, sequencing, or
  analog UART evidence exists for this slice. Historical ring-buffer and Revision A
  records were preserved byte-for-byte. Their open physical gates remain open.
- These results establish software acceptance only. They do not establish Stage 8,
  Phase 1A, Phase 1B, or shared Phase 1 completion. Current disposition is owned
  solely by `development_status.md`.


## Phase 1 v2 Migration Stage 7 Completed — 2026-10-25

- Started from clean HEAD `5643c65` (committed Stage 6). Implemented only the
  Stage 7 ownership lifecycle, Basic open-line provenance, and safe native USB
  selection. Settlement follows the current DUTchMate normative specification,
  particularly sections 13.8 (explicit release) and 25.5 (release exclusivity).
- Added the framework-independent seven-state connection vocabulary, ownership
  boundary/result/error values, and ownership port in `connection.py`. Runtime
  derives `connected` from explicit state, claims lifecycle requests without
  waiting behind competing lifecycle/mutation work, and rejects release during
  Interact or submitted TX/Control, including reentrant mutation callbacks.
  Read-only Monitor settles as `released`; follow does not own the transport.
  Shutdown waits for submitted mutation result evidence and fences late source
  publication; detach also cancels pending publication.
- Added atomic service `/connection/release` and `/connection/reacquire` plus
  HTTP-only CLI commands. Release durably records intent, closes/drains the
  physical source through the authoritative admission path, flushes line state,
  closes the segment, and records an intentional observation gap while keeping
  the session journal alive. The coordinator suspends automatic reconnect.
- Reacquire uses the resolved profile and records start/success/failure facts.
  A valid active journal continues with a fresh segment; a terminal prior
  journal produces a new v2 session with fresh session-local integrity. Existing
  segment-count rollover is reused. Rollover during a released interval carries
  the closed segment and ongoing gap instead of fabricating an open connection.
  Same-session/rollover cursors remain ordered. An exhausted cursor into an ended
  journal explicitly expires when reacquire creates an unrelated ownership
  session; it neither silently jumps nor waits forever on the old tail.
- Reused the coordinator's exclusive attempt claim for automatic/manual opens.
  Competing requests fail busy. Returned candidates rejected during shutdown,
  detach, deadline expiry, or publication failure are closed. Confirmed failed-
  open cleanup allows retry; missing/failed cleanup proof retains a blocking
  fault. Basic/Enhanced close failures remain visible on subsequent close calls.
  Enhanced failed-open cleanup retains the original exception identity and a
  cleanup certainty fact; lifecycle persistence failures remain typed
  `persistence_fault` errors and cannot be overwritten as safe disconnected
  ownership. The existing idle retry backoff is preserved.
- Basic now constructs an unopened serial object, applies requested DTR/RTS
  intent, then opens the selected path. Segment `serial` provenance records
  effective framing/flow settings, requested states, RTS ownership, and bounded
  preconfigured/driver-managed open intent without electrical readback or
  glitch-free/passive claims. RTS flow-control conflicts are rejected before
  opening. Optional semantic `serial_line_control` remains unavailable; Basic
  advertises neither GPIO control nor arbitrary line toggles.
- Added complete bounded `[backend.selector]` VID/PID/serial-number validation
  and backend-boundary unique discovery for native USB. Exact external-UART
  paths remain deterministic. Only a unique configured stable identity permits
  path change. Ambiguity opens nothing and exposes `service_unavailable` /
  `ambiguous_device`; automatic ambiguity leaves ownership disconnected with
  bounded status diagnostics. Native USB gaps remain real segment boundaries.
  CLI startup forwards the resolved selector to the service process.
- Added 50 deterministic hardware-free regressions across runtime, backend,
  service composition, and CLI. Coverage includes durable intent-before-close,
  RX drain, intentional gaps, active Monitor/Interact/TX settlement, same/new
  sessions, segment/size rollover, follow continuity/expiry, competing lifecycle
  claims, shutdown/detach fences, confirmed/unknown cleanup, persistence faults,
  Basic line provenance and capability separation, safe changed-path selection,
  ambiguity, startup selector forwarding, and unchanged retry backoff. New
  concurrency tests use Event/Condition synchronization; the retry test advances
  a fake clock without wall-clock sleeps.
- Focused validation:
  `UV_CACHE_DIR=/tmp/dutchmate-uv-cache uv run --frozen pytest tests/unit/runtime tests/unit/evidence tests/unit/backends tests/unit/profile tests/unit/session_store apps/service/tests apps/cli/tests tests/architecture -q --tb=short`
  — 830 passed in 12.86 seconds.
- Full validation:
  `UV_CACHE_DIR=/tmp/dutchmate-uv-cache uv run --frozen pytest -q`
  — 1,515 passed in 39.93 seconds. Ruff passed; configured mypy passed (103
  source files); `uv lock --check` passed (66 packages; temporary writable cache,
  no lockfile changes); executable architecture/import checks passed; and
  `git diff --check` passed. Import Linter is not configured.
- Updated architecture ownership, status, and the legacy reconnect document's
  supersession header. `graphify update .` refreshed the ignored structural
  graph (5,698 nodes, 14,813 edges), with the existing partial-extraction warning
  for `hardware/firmware/zephyr_dut/src/fixture_protocol.h` and a community-label
  refresh notice. Generated graph artifacts are excluded from review changes.
- Completed the Stage 7 slice from implementation baseline `5643c65`. No Stage 8,
  MCP migration, firmware/protocol changes, composite workflow, or physical
  acceptance work was started. No hardware was accessed.


## Phase 1 v2 Migration Stage 6 Completed — 2026-10-25

- Implemented `GET /dut/evidence` over committed schema-v2 primary streams.
  Cursorless attachment returns no historical records. Cursor requests merge
  UART, operation, hardware, and connection records by contiguous evidence
  sequence with exact RX bytes/raw offsets and segment timestamp provenance.
  Action/operation/connection projections omit arbitrary exception detail.
- The separate public cursor is versioned URL-safe base64 containing a session,
  next evidence sequence, and four stream seek offsets. It follows explicit
  rollover successors; missing retained positions return HTTP 410
  `cursor_expired` without guessing or silently attaching forward. Initial
  cursorless attachment resamples a tail retired by concurrent rollover.
- Snapshot metadata, file handles, and committed lengths are captured under the
  store lock; incremental replay runs outside that lock. Reference-counted
  snapshot leases reuse retention protection and release on success/error.
  Long polls use recorder notifications only as wakeups, then reread persisted
  evidence. No subscriber queue or additional backend reader was introduced.
- Enforced integer limit 1..500 (default 100), finite wait 0..30 seconds
  (default 1.0), and the 262144-byte compact UTF-8 envelope cap. Whole records
  deferred by that cap are counted within the selected bounded window and left
  unread by `next_cursor`, so clients can recover them exactly once.
- Added HTTP-only `dutchmate follow` and line-oriented `dutchmate console`.
  Follow starts at tail or resumes an opaque cursor, renders UART and bounded
  evidence markers, and reports expiry without automatic reattachment. Console
  requires effective `uart_send`, resolves its default ending from the service's
  immutable effective profile, and submits explicit endings through the Stage 5
  audited standalone-send endpoint. Interact conflicts report `operation_active`
  without TX/retry. Console displays authoritative stream evidence; EOF/Ctrl-C
  closes and joins only the view. Neither command owns serial/session lifecycle.
- Added 35 regressions covering attachment, deterministic exactly-once paging,
  rollover, expiry, committed snapshot boundaries, byte-cap recovery including
  maximum-sized control-byte UART, long-poll wakeup, malformed cursors, safe
  markers, slow-reader isolation, retention lease cleanup, client-only exits,
  audited HTTP console sends and profile defaults, and real Interact conflicts.
- Focused validation:
  `UV_CACHE_DIR=/tmp/dutchmate-uv-cache uv run --frozen pytest tests/unit/evidence tests/unit/runtime tests/unit/session_store apps/service/tests apps/cli/tests tests/architecture -q`
  — 629 passed in 12.16 seconds.
- Full validation:
  `UV_CACHE_DIR=/tmp/dutchmate-uv-cache uv run --frozen pytest -q`
  — 1,465 passed in 42.86 seconds, including historical v0/v1 compatibility,
  continuous recorder/Monitor/Interact, audited actions, and import boundaries.
  `uv run --frozen ruff check .` passed;
  `uv run --frozen mypy` passed (101 source files);
  `uv lock --check` passed (66 packages; writable temporary UV cache);
  `git diff --check` passed. Import Linter is not configured; the executable
  architecture tests supply the repository's import/dependency gate.
- `graphify update .` refreshed the ignored local structural index (5,576 nodes,
  14,404 edges) with the existing partial-extraction warning for
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h` and a community-label
  refresh notice. Generated artifacts are excluded from the review diff.
- Started from clean HEAD `857261b` (committed Stage 5), reconciling the stale
  current-status baseline without rewriting prior history.
  No Stage 7/8, MCP migration, composite workflow, or physical
  hardware acceptance work was started. No hardware was accessed.


## Stage 5 Atomic-Capability Cleanup Completed — 2026-10-25 (Uncommitted)

- Applied the documented review decision to the existing Stage 5 diff. Removed
  `DeviceCoreRuntime.run_boot_test`, its reset-and-observe implementation,
  `/dut/boot-test`, `RuntimeProvider.run_boot_test`, `BootTestRequest`, the CLI
  `boot-test` command, its HTTP client, and its dedicated result formatter.
  No replacement composite was introduced; reset and boot-mode Control remain.
- Removed the boot-test-only `_reset_audited` helper, internal composite Control
  ownership parameters, fake-runtime boot-test support, and unused imports.
  Live bounded-operation types and new v2 operation admission now allow only
  Monitor/Interact; the Control evidence schema still records standalone
  `operation_id: null` without changing stored evidence formats.
- Deleted live boot-test CLI/service test modules and client tests. Removed the
  composite-only runtime validation/observation tests; converted immediate boot
  RX coverage to audited standalone reset with no Monitor running, followed by
  a separate Monitor proving pre-start evidence is not retroactively matched.
  Converted mixed service coverage to the standalone reset endpoint.
- Added regressions for the absent runtime/client/formatter/schema/CLI/HTTP
  surfaces and rejection of new v2 boot-test operation admission. Retained all
  historical v0/v1 readers, replay, metadata workflow vocabulary, baseline/
  comparison compatibility, and fixtures. A synthetic historical v2 boot-test
  fixture verifies detail, terminal evidence, and UART replay remain readable.
  No existing historical evidence or prior history entries were rewritten.
- Preserved the remaining Stage 5 contracts: one continuous RX owner, exact-byte
  audited TX, durable attempt-before-dispatch, known/unknown result evidence,
  standalone mutation serialization, Interact exclusivity, read-only Monitor
  coexistence, and reconnect without TX retry.
- Validation: 472 focused tests passed across runtime, payload validation,
  session compatibility/persistence, Control/GPIO, and service/CLI public
  surfaces. All 1,430 pytest tests passed in 43.82 seconds. Ruff passed;
  configured mypy reported no issues in 97 source files; `uv lock --check`
  passed (66 packages, temporary writable `UV_CACHE_DIR`); and
  `git diff --check` passed. Import Linter is not configured. The local structural
  Graphify index was refreshed (5,485 nodes) with the pre-existing partial
  extraction warning for `hardware/firmware/zephyr_dut/src/fixture_protocol.h`.
- Baseline remains `365c302`; all Stage 5 work remains uncommitted. Stage 6,
  release/reacquire, Stage 8 cleanup/HIL, and MCP migration were not started.
  No physical hardware was accessed.


## Stage 5 Review Decision — Remove Dedicated Boot-Test Composite — 2026-10-25

- Stage 5 review concluded that `boot-test` is a use-case-specific composite and
  should not remain a Device Core, service, CLI, or future MCP capability.
- The target product boundary remains the generic deterministic primitives:
  continuous evidence, Monitor, Interact, audited UART TX, audited Control, and
  durable evidence access. Clients/coding agents compose reset-and-observe,
  bootloader validation, and similar procedures from those atomic capabilities.
- Continuous acquisition preserves immediate post-reset UART even when it arrives
  between client requests. The Phase 1 durable evidence cursor is the generic
  mechanism for an exact pre-action observation boundary; a later Monitor does
  not retroactively match pre-cursor bytes.
- The already implemented uncommitted Stage 5 boot-test path must therefore be
  removed before Stage 5 is committed. Historical v0/v1 boot-test sessions,
  readers, fixtures, and prior validation records remain truthful compatibility
  evidence and are not rewritten.
- Normative/current documentation was updated first so the coding-agent cleanup
  follows one source of truth. Final Stage 5 validation is pending that removal.


## Phase 1 v2 Migration Stage 5 — 2026-10-25 (Uncommitted Review Diff)

- Implemented byte-first standalone UART send with exactly one binary/text input,
  explicit `none|lf|cr|crlf|profile_default` transformations, final 1..1024-byte
  validation, exact transmitted bytes, and durable attempt/result references.
  Public service/CLI `force`, implicit newline append, and optional perturbation
  auditing were retired. No TX enters the RX-only raw log.
- Reused the existing bounded operation lifecycle, cursor, incremental reader,
  matcher, range-quality projection, and retention lease for Interact and
  boot-test. Interact establishes its cursor before TX, holds exclusive mutation
  ownership, supports duration/conditions/cancellation, and preserves one
  operation through reconnect without retransmission. Transport-interrupted or
  lifecycle-terminalized attempts expose truthful unknown acceptance.
- Added common standalone mutation serialization and v2 attempt-before-dispatch
  auditing for reset, boot mode, and GPIO mode changes while preserving accepted
  role/electrical state. Failed/unavailable results remain explicitly known or
  unresolved; inability to persist an attempt prevents physical dispatch.
- Boot-test records a composite start while acquisition is already active,
  audits reset without changing boot mode, then observes the same durable stream.
  It releases mutation serialization after reset. Read-only Monitor continues
  alongside standalone mutations and Interact. Shutdown cancels operations and
  waits for in-flight action result evidence before closing recording.
- Extended recorder admission to existing v2 TX/Control persistence primitives,
  including exact action-unit rollover preflight, line-boundary flushing,
  pending-attempt transfer, and fatal persistence handling. Reconnect failure and
  backend-input terminalization now cover all three bounded operation types.
- Mapped callers before removing the old finite `CaptureWorkflow`,
  `CaptureRecorder`, `TransportCaptureRunner`, workflow reader lifecycle,
  runtime capture/exclusion/session-rebasing state, and per-capture reconnect
  path. Obsolete finite-execution and forced-send tests were replaced/retired;
  the Basic pipeline proof now exercises continuous v2 recording. Source/health/
  reconnect contracts remain for live backend/service consumers. V0/v1 reading,
  replay, stored evidence formats, and session-store compatibility fixtures were
  preserved. Low-level protocol/MCP text helpers remain outside the new live TX
  contract; no MCP files were changed.
- Added service/CLI Interact and migrated send/boot-test contracts. Regression
  evidence covers immediate reply ordering, unrelated and post-operation ambient
  RX, one reader on Basic/Enhanced, read-only coexistence, exclusivity, mutation
  ordering, request validation, partial/failed actions, attempt/result failures,
  recovery of unknown attempts, reconnect success/failure/deadline precedence,
  cancellation, action-triggered rollover, early boot RX, and shutdown ordering.
- Validation: 357 focused regressions passed; `uv lock --check` passed (66
  packages, using a writable temporary `UV_CACHE_DIR`); Ruff passed; configured
  mypy reported no issues in 97 source files; all 1,449 pytest tests passed in
  35.95 seconds; and `git diff --check` passed. The structural Graphify index was
  refreshed with its existing partial-extraction warning for
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h` and an aggregated view for
  5,503 nodes. Generated graph artifacts remain untracked local navigation data.
- Baseline is `365c302`; no commit was created. Stage 6 durable cursor/follow/
  console, Stage 7 ownership handoff, Stage 8 acceptance, MCP migration, and
  physical hardware acceptance were not started in this slice.

## Phase 1 v2 Migration Stage 4 Review Fixes — 2026-09-28

- Made Monitor lifecycle admissions rollover-boundary aware. Continuous line
  state is finalized before a start or terminal record rolls, and the start
  cursor plus pre-cursor incomplete-line snapshot are taken from the actual
  start session.
- Guaranteed terminal ownership after a durable start. Operation-local reader,
  matcher, and initialization failures persist an `error` terminal while
  storage remains usable; terminal persistence failure faults authoritative
  recording and fails session ownership without fabricating a result.
- Derived terminal integrity and timestamp provenance from every operation
  evidence range. Integrity now uses only telemetry inside each exact half-open
  range, excluding cumulative loss observed before the start or after the end,
  while preserving in-range loss across rollover/reconnect and each relevant
  session-local timestamp provenance segment.
- Replaced lock-held full UART JSONL rescans with operation-local seek readers
  opened at the durable start byte offset. Each poll reads only newly admitted
  UART evidence and does not acquire the global store mutation lock. A bounded
  operation reader lease is extended atomically with terminal persistence so
  retention cannot delete predecessor ranges until result construction ends;
  runtime cleanup then releases it on every exit path.
- Removed the runtime's public v1 capture/wait fallbacks. Both legacy spellings
  now require and call Monitor; only finite capture infrastructure needed by
  the not-yet-migrated Stage 5 boot-test remains. Obsolete v1 wait execution
  tests were removed, while retained boot-test infrastructure tests call the
  internal workflow explicitly.
- Added deterministic regressions for start/terminal rollover with partial
  lines, reader/matcher/post-start initialization failures, terminal persistence
  failure, earlier-range loss/provenance, incremental unlocked reading, and
  Monitor-only aliases. Stage 5 behavior was not started.
- Validation: 79 focused Monitor/persistence/status regressions passed;
  `uv lock --check`, Ruff, configured mypy (94 source files), all 1,488 pytest
  tests, and `git diff --check` passed. Graphify was refreshed with its existing
  partial extraction warning for
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h`.

## Phase 1 v2 Migration Stage 4 — 2026-09-28

- Added one common bounded Monitor model with validated duration or ordered
  literal-condition completion, globally unique Device Core operation IDs,
  monotonic deadlines, cancellation, active-operation status, durable start/end
  cursors, rollover-spanning ranges, normalized terminal outcomes, exact match
  references/excerpts, and line-processing quality.
- Monitor consumes only schema-v2 UART records after its durable start cursor.
  Operation-local line buffers never search history or join across session,
  segment, or pre-cursor partial-line boundaries; oversized lines are excluded,
  and match selection uses evidence order, byte offset, then request order.
- Preserved Monitor across successful reconnect with the same operation ID and
  terminalized reconnect-deadline failure as durable `disconnected` evidence.
  Backend-input faults produce durable `error` operation terminals, while HTTP
  cancellation produces `cancelled`; continuous ingestion remains the only
  physical reader throughout.
- Added `POST /dut/monitor`, `dutchmate monitor --seconds`, and `dutchmate
  monitor --until ... --timeout ...`. Legacy capture/wait runtime, service, and
  CLI paths are temporary wrappers over Monitor whenever continuous recording
  is active; boot-test and action semantics remain deferred to Stage 5.
- Added focused validation for bounds and condition metadata, no-side-effect
  rejection, pre-start/pre-cursor exclusion, oversized boundary handling,
  deterministic tie-breaks, normal timeout, exact durable match projection,
  reconnect success/failure, cancellation, backend fault, concurrent observers,
  rollover ranges, active status, HTTP responses, CLI behavior, and aliases.
- Validation: `uv lock --check` passed; Ruff passed; configured mypy reported no
  issues in 96 source files; all 1,487 pytest tests passed; and
  `git diff --check` passed. The structural Graphify index was refreshed; it
  reported the existing partial extraction of
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h` after a syntax warning.

## Phase 1 v2 Migration Stage 3 Review Fixes — 2026-09-28

- Replaced indefinite idle reopen with the profile-snapshotted reconnect
  deadline. Unexpected disconnect now flushes derived line state, durably closes
  the segment, records `unexpected_disconnect` and `reconnect_started`, and
  records either `reconnect_succeeded` or `reconnect_failed`. Deadline expiry
  fails the active v2 session with `reconnect_timeout` and projects service state
  as `disconnected` with no active session.
- Required every Enhanced replacement candidate to establish a segment timestamp
  origin before publication. Identity/capability validation remains non-consuming,
  and the first queued timestamped event remains available to the recorder.
- Made clean shutdown close physical receive, drain every normalized event
  retained by Basic/Enhanced sources (including an Enhanced event blocked on
  bounded FIFO admission), finalize continuous line state, and only then
  terminalize the active session. Basic now uses a fixed-capacity FIFO so
  backend-to-recorder backpressure is bounded.
- Finalized line processors at disconnect, UART- or telemetry-triggered rollover,
  and shutdown. Partial lines cannot join across boundaries, and an oversized
  unterminated line produces exactly one bounded `line_limit_exceeded` fact while
  raw UART remains authoritative.
- Added deterministic regressions for reconnect success/timeout, segment close
  timestamps/reasons, Enhanced origin establishment, shutdown draining, each
  line-state boundary, actual Enhanced queue draining (including a deterministic
  capacity-one blocked-admission case), service disconnected projection, and
  Basic queue boundedness. Stage 4 behavior was not started.
- Validation: focused backend/recorder/service tests passed; `uv lock --check`,
  Ruff, configured mypy (93 source files), all 1,441 pytest tests,
  and `git diff --check` passed. The structural Graphify index was refreshed; it
  reported partial extraction of
  `hardware/firmware/zephyr_dut/src/fixture_protocol.h` after a syntax warning.

## Phase 1 v2 Migration Stage 3 — 2026-09-28

- Replaced the service-owned idle drain/discard coordinator with a core-owned
  `ContinuousEvidenceRecorder`. Production Basic and Enhanced startup now
  creates an active schema-v2 ownership session after backend identity and
  timestamp provenance are established, then starts exactly one authoritative
  receive loop before reconnect supervision.
- Persisted ambient UART RX, Enhanced buffer telemetry, connection lifecycle,
  derived line-limit facts, default pattern matches, continuous `first_error`,
  segment timestamps, integrity summaries, and continuity gaps through one
  contiguous v2 evidence order. Durable-tail waiters advance only after the
  complete admission transaction commits and do not backpressure acquisition.
- Preserved one ownership interval across validated source replacement and
  linked rollover sessions, rebasing physical segment IDs to session-local
  contiguous IDs and resetting line state at reconnect/rollover boundaries.
  Clean shutdown flushes and completes ownership; backend-input or persistence
  faults close the source and fail the session rather than continuing silently.
- Removed the obsolete continuous-ingestion module and its workflow-FIFO/idle-
  discard tests. Added recorder and service regressions for idle Basic/Enhanced
  UART, no-client delayed faults, telemetry and contiguous ordering, line limits,
  rollover isolation, reconnect lifecycle/continuity, one physical reader,
  persistence faults, shutdown cleanup, active-session status, and Stage 4
  Monitor non-implementation.
- Stage 4 Monitor execution and Stage 5 audited TX/Interact/Control behavior were
  not implemented.
- Validation: focused recorder/service and 181 session-store tests passed;
  `uv lock --check` passed; Ruff passed; configured mypy reported no issues in
  93 source files; all 1,431 pytest tests passed; `git diff --check` passed; and
  the structural Graphify index was refreshed.

## Phase 1 v2 Migration Stage 2 Final Review Fixes — 2026-09-28

- Made every schema-v2 terminalization path relinquish active-operation
  ownership, close open evidence ranges into `interrupted_operations`, and set
  the active count to zero without fabricating `operation_terminal` evidence.
  This includes normal completion, failure, abandonment/recovery, and
  persistence-fault terminalization.
- Added explicit pending UART-TX/Control attempt ownership to v2 metadata.
  Rollover transfers that ownership to the successor, retention protects each
  attempt's origin session until its linked result is durable, result evidence
  references the origin session/sequence, and resolution reruns retention. If a
  successor terminalizes or is recovered as abandoned first, the pending state
  remains an explicit unresolved/unknown outcome while operation ownership is
  relinquished; terminal pending state does not indefinitely protect its origin
  from retention.
- Removed the unbounded historical operation-ID metadata registry. Persistence
  rejects collisions visible in the bounded current-session operation evidence,
  including continued operations, while globally unique ID generation remains
  the responsibility of Device Core operation callers in their later stages.
- Unified v2 `operation_counts` as the four operation-state counters (`started`,
  `completed`, `failed`, `active`) across list, detail, model, and service
  projections. Detail no longer maintains a competing event-type count shape.
- Added targeted regressions for normal/failure/abandonment and persistence
  terminalization, recovery, both attempt kinds across rollover, result and
  crash paths, bounded operation-ID metadata, and list/detail/service count
  equality. Runtime ownership, continuous ingestion, and Monitor execution were
  not changed; Stage 3 and Stage 4 were not started.
- Validation: 181 session-store tests passed; configured mypy reported no issues
  in 92 source files; Ruff passed; `uv lock --check` passed; all 1,482 pytest
  tests passed; and `git diff --check` passed.

## Phase 1 v2 Migration Stage 2 Review Fixes — 2026-09-28

- Moved active-operation ownership entirely into the rollover successor. The
  predecessor now closes its ranges and clears active ownership while the
  successor owns the continued operation and its open range.
- Rebuilt rollover-sensitive session-local fields against the admitted
  successor: operation cursors/ranges, segment IDs, UART raw offsets and pattern
  references, connection records, and TX/Control attempts. Operation IDs remain
  unique across a retained rollover chain and action ownership references must
  name an active operation.
- Added stable schema-v2 list/detail snapshots using transaction-marker and
  metadata-before/after checks, explicit `rollover_succeeded` connection
  evidence, and an immediate retention pass after rollover.
- Restricted terminal outcomes to the normalized Phase 1 vocabulary, required
  bounded error data to agree with the `error` outcome, and rejected operation
  identities with edge whitespace or Unicode control characters.
- Added regressions for each review finding, including nonzero-segment rollover,
  active-operation transfer, start/terminal cursor rebasing, action and segment
  rebasing, stable concurrent retrieval, lifecycle evidence, retention, and
  identity/outcome validation. Runtime ownership and continuous ingestion were
  not changed; Stage 3 was not started.
- Validation: 172 session-store tests passed; configured mypy reported no issues
  in 92 source files; Ruff passed; `uv lock --check` passed; all 1,473 pytest
  tests passed; and `git diff --check` passed.

## Phase 1 v2 Migration Stage 2 — 2026-09-26

- Added an independently usable native schema-v2 session store with the seven
  required evidence artifacts plus an active-only terminal reserve. Creation
  publishes compact bounded metadata only after all required files are durably
  initialized; failed creation removes the partial directory.
- Added one contiguous primary `evidence_seq` across UART RX, operation,
  UART-TX, Control, and connection records. UART admission preserves exact raw
  offsets/base64 equivalence and atomically stores derived pattern references;
  action attempt/result matching exposes unresolved outcomes after restart.
- Added whole-unit evidence preflight, exact-boundary admission, linked
  `rollover_size`, rollover before segment 33, and operation continuation ranges
  across successors. Successor or authoritative append failures terminalize the
  affected active sessions with explicit local persistence-fault evidence.
- Added stale-active abandonment without invented connection evidence,
  discriminated v2/v1/v0 list/detail projections, v2 log replay, first-error
  projection, baseline/comparison rules, and retention protection for active,
  baseline, active-operation-range, and in-progress-reader sessions. Historical
  v0/v1 directories remain read-only and are not upgraded in place.
- Added bounded v2 service serialization while leaving Device Core runtime
  creation and ingestion on v1 for the Stage 3 migration. The Debug Agent
  continues to reject non-v1 evidence explicitly.
- Validation: 154 focused session-store tests passed; configured mypy reported
  no issues in 92 source files; Ruff passed; all 1,455 pytest tests passed; the
  structural Graphify index was refreshed; and `git diff --check` passed.

## Phase 1 v2 Migration Stage 1 — 2026-09-25

- Introduced `core/profile` as the single file-backed configuration authority.
  Its resolved immutable DUT Profile owns backend mode, exact/discovery selector,
  current path, reconnect timeout, topology, UART framing/flow/TX policy,
  requested DTR/RTS open behavior, default line ending, and Enhanced GPIO
  configuration.
- Added a bounded deterministic canonical JSON projection and stable SHA-256
  digest. Runtime, service status, and CLI status expose the effective projection,
  name, digest, and concise UART settings without writing schema-v2 evidence.
- Changed CLI/service startup to pass one validated effective profile into the
  runtime. Physical adapters receive only a derived `BackendSettings` projection;
  the superseded independent backend config parser/resolver and tests were
  removed.
- Preserved physical behavior: TX remains disabled by default, accepted framing
  remains Basic 115200 8N1 or Enhanced 460800 8N1, flow control remains off,
  existing device discovery/reconnect remains in place, and requested DTR/RTS
  states are recorded but not physically manipulated.
- Focused profile, CLI configuration/lifecycle/status, and service startup/status
  validation passed (105 tests). Ruff passed; mypy reported no issues in 92
  source files; all 1,432 pytest tests passed; the structural Graphify index was
  refreshed; and `git diff --check` passed.

## Phase 1 v2 Migration Stage 0 — 2026-09-25

- Adopted `project_context.md` and `phase1_implementation_spec.md` as the
  canonical product and Phase 1 behavior contracts and classified the migration
  plan as a temporary execution aid.
- Reopened Phase 1 against the v2 success criteria. Earlier Basic, Enhanced,
  firmware, ring-buffer, and HIL results remain historical physical/backend
  evidence but do not establish continuous ambient recording, schema v2,
  Monitor, Interact, follow/console, or release/reacquire.
- Marked all production migration stages as not started and Stage 1 DUT
  Profile/effective serial provenance as the next development slice.
- Scoped the existing architecture, reconnect/session, and MCP documents as
  pre-v2 implementation references wherever their contracts conflict with the
  new normative baseline. No production or test behavior changed.
- Documentation validation confirmed that the normative files and migration
  plan were unchanged from `efe93060`, all newly used relative links resolve,
  superseded current-status acceptance claims are absent, only documentation
  files changed, and `git diff --check` passed.

## Repository Documentation Cleanup Task 4 — 2026-09-24

- Split the 2,580-line pre-task status into a 126-line current authority and an
  append-only historical record. `Resume Here` is 31 lines.
- Inventoried source boundaries were lines 488–2183 (`Latest Validation`),
  2184–2218 (`Already Complete`), 2219–2248 (Phase 2), 2251–2271 (completed
  Phase 4 checklist), and 2275–2316 (Delivery Infrastructure). A mechanical
  comparison against `HEAD:docs/development_status.md` found all five blocks
  exactly once and byte-for-byte in this file.
- Rewritten current prose was limited to `Resume Here`, the Phase 1 assessment,
  paused/deferred queues, and later-phase ordering. The current milestone,
  exact next step, blockers, and queue remain in Development Status.
- Ruff passed; mypy reported no issues in 89 source files; all 1,435 pytest
  tests passed; and `git diff --check` passed.

## Latest Validation

Repository documentation cleanup Task 3, reviewed 2026-09-24:

- The root README is 97 lines and now leads with an installed-user workflow,
  verified Enhanced GPIO/boot-test syntax, a deterministic formatter-backed
  first-error example, backend exclusivity, and the tools-only MCP surface.
- The documentation index links current status, append-only history, glossary,
  canonical contracts, hardware records, and release guidance. The glossary
  defines recurring product, evidence, reconnect, and hardware terms without
  placeholders.
- Ruff passed; mypy reported no issues in 89 source files; all 1,435 pytest
  tests passed; and `git diff --check` passed.

Repository documentation cleanup Task 2, reviewed 2026-09-24:

- All 13 completed working design/implementation plans (8,356 lines) were
  removed. No active file referenced them, and the async adapter, service
  ownership, coordinated reconnect, monitoring, and RP2350 invariants remain
  represented in authoritative architecture, behavior, and firmware docs.
- Planning guidance now routes durable decisions, current progress, and
  completed evidence to their respective authoritative documents instead of a
  permanent working-plan archive.
- Ruff passed; mypy reported no issues in 89 source files; all 1,435 pytest
  tests passed; and staged and unstaged `git diff --check` passed.

Repository hygiene cleanup Task 1, reviewed 2026-09-24:

- The machine-specific `.codex/hooks.json` and all generated `graphify-out/`
  artifacts are untracked and ignored while their local files remain intact.
  The tracked hook example parses as JSON, resolves `graphify hook-check` from
  `PATH`, and contains no absolute user path.
- Active tracked files contain no `/Users/` path. Developer guidance documents
  both lightweight structural regeneration and the full semantic Graphify flow.
- Ruff passed; mypy reported no issues in 89 source files; all 1,435 pytest
  tests passed; and `git diff --check` passed.

Public Python v0.1.0 release, reported 2026-09-23:

- The `v0.1.0` tag built and retained the five accepted public wheel
  and source-distribution pairs. `dutchmate-debug-agent` was not selected or
  published.
- All five projects were created on TestPyPI through Trusted Publishing. The
  aggregate `verify-testpypi` job matched every remote filename and SHA-256
  digest to the retained artifact before production approval became available.
- All five projects were then created on production PyPI through the protected
  `pypi` environment and OIDC. The final `verify-pypi` job passed the same
  aggregate filename and digest contract.
- GitHub treated the first environment approval on each index as sufficient for
  later dependent jobs using that environment. Each not-yet-registered project
  therefore failed safely before creation, was registered after the preceding
  pending publisher converted, and succeeded through **Re-run failed jobs**.
  Successful predecessors and the original retained artifact were not rebuilt.
- The owner reports that the DCO App is installed and its status check is
  required through branch protection, and that the GitHub Release is public.
- The prepared GitHub Release body, public README installation guidance, and
  corrected bootstrap runbook passed lock verification, Ruff, mypy (89 source
  files), all 1,435 tests, and `git diff --check`.

Sequential Trusted Publisher bootstrap revision, reviewed 2026-09-23:

- The release workflow now publishes each of the five `v0.1.0` distributions
  through its own protected OIDC job on each index. Explicit dependencies keep
  the order `dutchmate-core`, CLI, service, MCP server, then the `dutchmate`
  aggregator, allowing only one pending publisher to be registered and
  converted at a time.
- Every publish job downloads the single retained build artifact and has no
  build authority. Aggregate TestPyPI filename/SHA-256 verification gates the
  first production job, and an equivalent aggregate check follows production
  publication. The protected `testpypi` and `pypi` environments and the
  five-package allowlist remain unchanged.
- The operator runbook records the one-at-a-time registration and failed-job
  rerun sequence and a tightly scoped temporary-token contingency. No tag was
  created and no artifact was published during this revision.
- The workflow contract was observed failing before implementation and passing
  afterward. Release YAML syntax parsing, all 23 packaging tests, lock
  verification, Ruff, mypy (89 source files), all 1,435 tests, and
  `git diff --check` passed.

Five-distribution `v0.1.0` release staging, reviewed 2026-09-23:

- The public aggregator no longer declares the deferred `debug-agent` extra or
  exposes `dutchmate debug`. Its four deterministic executables and MCP surface
  are unchanged.
- Normal CI continues to build and clean-install all six workspace
  distributions, including the standalone `dutchmate-debug` development
  command. The release workflow selects only the five public wheel/source pairs,
  revalidates that exact set, and retains it for TestPyPI and PyPI publication.
- `dutchmate-debug-agent` remains provider-disabled, independently tested, and
  source-available in the workspace. Its first public distribution is queued
  for the coordinated `v0.2.0` release after its coding-agent access model and
  public command surface are reconfirmed.
- The artifact gate built and accepted 12 workspace artifacts, selected and
  reaccepted exactly 10 public artifacts, and completed installed MCP discovery.
  Lock verification, Ruff, mypy (89 source files), all 1,435 tests, release YAML
  parsing, and `git diff --check` passed. Graphify was refreshed after removing
  the aggregator-to-Debug-Agent dependency; its existing
  `fixture_protocol.h` partial-extraction warning remains.

PCB source-layout migration, reviewed 2026-09-23:

- The owner-moved historical Revision A EAGLE design is preserved under
  `hardware/pcb/debug-helper/legacy-eagle/`; active specifications, firmware
  guidance, validation records, licensing policy, and repository navigation now
  reference that path explicitly as legacy evidence.
- `hardware/pcb/debug-helper/rev-a/` is reserved for the future KiCad project.
  Its README records the source/library/provenance/manufacturing ownership model
  and keeps the CERN-OHL-P-2.0 grant blocked until the design and provenance
  audit exist.
- KiCad local settings, locks, autosaves, backups, cache/rescue files, and
  conventional scratch export directories are ignored. Editable KiCad sources,
  project libraries, and reviewed `manufacturing/` outputs remain trackable.
- A repository-wide reference scan found no remaining references to the former
  schematic directory. Focused license contracts, the full test suite, Ruff,
  mypy, lock verification, and `git diff --check` passed.

Mixed-license and Python-release enablement, reviewed 2026-09-23:

- The root scope map applies Apache-2.0 to host software, protocol/build
  infrastructure, the portable plugin, and both firmware projects;
  CC-BY-4.0 applies to general documentation. The legacy EAGLE design material
  now under `hardware/pcb/debug-helper/legacy-eagle/` is explicitly outside the
  new grants. `hardware/pcb/debug-helper/rev-a/` is reserved for the
  owner-managed KiCad replacement and provenance audit.
- All six Python projects declare `License-Expression: Apache-2.0`, Nahit Pawar
  as author, and the public repository URLs. Their complete local Apache texts
  match the canonical SPDX text, and all six wheels and source distributions
  contain the expected license metadata and file without hardware content.
- DCO 1.1 contribution guidance and a pull-request reminder are added. The
  external DCO App installation and required status check remain an owner
  configuration step.
- The release workflow validates exact stable tags, builds and accepts artifacts
  once, grants OIDC only to separate publish jobs, publishes in dependency
  order, verifies every TestPyPI filename and SHA-256 digest, and reuses the
  retained artifacts for protected production publication.
- Lock verification, Ruff, mypy (89 source files), all 1,437 tests, the
  12-artifact build, isolated base/Debug-Agent command checks, installed MCP
  discovery, release YAML parsing, and `git diff --check` passed.

Hosted delivery-infrastructure acceptance, reported 2026-09-23:

- All host CI jobs are green, including the Python 3.10 timeout-regression
  paths and the clean package-build jobs.
- All three firmware jobs are green after the runner-capacity and SDK
  size-tool corrections. The successful firmware workflow took approximately
  18 minutes; this is accepted for the initial path-filtered compile workflow
  and does not block the delivery milestone.

Firmware-CI SDK size-tool correction, reviewed 2026-09-23:

- After the runner-capacity correction, all three hosted firmware builds
  reached successful ELF/UF2 generation and then failed in their shared size
  capture because `arm-zephyr-eabi-size` is not exported on the pinned image's
  `PATH`.
- The image's official Dockerfile installs SDK 1.0.1 below
  `/opt/toolchains/zephyr-sdk-1.0.1`; the workflow now invokes the SDK's ARM
  size executable through that pinned root and the image-provided
  `ZSDK_VERSION`, rather than relying on command lookup.
- A regression contract covers both firmware jobs. The equivalent SDK 1.0.1
  executable produced size output for existing RP2040 and RP2350 ELFs, and the
  workflow YAML plus all six embedded Bash scripts parse locally. Locked
  resolution, Ruff, mypy (89 source files), all 1,426 tests, and
  `git diff --check` passed. The subsequent hosted firmware workflow passed all
  three configurations.

Python 3.10 timeout-normalization correction, reviewed 2026-09-23:

- The hosted Python 3.10 suite exposed the pre-3.11 distinction between
  built-in `TimeoutError` and `asyncio.TimeoutError`. That caused provider
  deadlines to be reported as generic provider failures and allowed Enhanced
  serial hello/command deadlines to escape without their transport-level
  normalization and cleanup.
- The three `asyncio.wait_for` boundaries now catch `asyncio.TimeoutError`;
  the provider boundary additionally catches a provider-raised built-in
  `TimeoutError`. No timeout values, lifecycle behavior, or public error
  contracts changed.
- The six reported cases and the additional provider-raised timeout case were
  reproduced under Python 3.10.19 before correction. All 1,425 tests then
  passed under Python 3.10.19; lock verification, Ruff, mypy (89 source files),
  and `git diff --check` also passed. The subsequent hosted host-CI workflow
  passed.

Firmware-CI runner-capacity correction, reviewed 2026-09-22:

- All three first hosted firmware jobs failed before checkout because the
  standard runner exhausted its disk while Docker registered the job-level
  Zephyr image. Container retry could not help, and a workflow step could not
  clean the host before GitHub created a job-level container.
- The firmware jobs now start on the host, remove only disposable preinstalled
  runner SDK/tool caches, prune Docker storage, explicitly pull the same
  digest-pinned official Zephyr v0.29.4 image, and execute each build inside it
  with bounded workspace and temporary-directory mounts. The Zephyr, SDK,
  target, configuration, provenance, and artifact contracts are unchanged.
- Workflow YAML and all embedded Bash scripts parse locally. A regression test
  enforces the absence of job-level containers and cleanup-before-pull ordering
  in both jobs. The subsequent hosted firmware workflow passed without the
  runner-capacity failure.

Host-CI portability corrections, reviewed 2026-09-22:

- The first Ubuntu full-suite run exposed two environment-specific assumptions:
  Typer/Rich inserted ANSI styling inside the invalid `--log-level` token, and
  glibc hid POSIX `strnlen` during the Debug Helper's strict ISO C11 host build.
- The CLI regression now forces colored output and compares its unstyled text.
  The firmware host harness explicitly limits POSIX visibility to 2001, while
  `hello.c` uses an internal bounded ISO C11 string-length helper. The focused
  nine failing cases were reproduced before the corrections and all pass after
  them.
- Full local validation passed after the corrections: locked resolution, Ruff,
  mypy (89 source files), 1,425 pytest tests, and `git diff --check`. The RP2350
  Debug Helper also rebuilt successfully with Zephyr 4.4.2 and SDK 1.0.1. The
  subsequent hosted workflow passed.

Delivery Infrastructure private-validation slices, reviewed 2026-09-22:

- The locked workspace exposes all four aggregator-owned public commands, and
  `dutchmate debug` invokes the optional Debug Agent Python API directly.
  Component distributions no longer duplicate those public scripts; direct
  `dutchmate-debug` remains available only for component development.
- All six synchronized `0.1.0` source distributions and wheels built with
  `uv build --all-packages --no-sources`. An isolated `uv tool install` smoke
  removed repository `PYTHONPATH`, checked public help commands and the
  missing-extra error, verified that dependency executables were not exposed,
  and completed real MCP discovery with the nine deterministic tools and clean
  EOF.
- The RP2350 Debug Helper compiled with Zephyr 4.4.2 and SDK 1.0.1. Both the
  default 115200 and opt-in 460800 Pico fixtures compiled with Zephyr 4.4.0 and
  SDK 1.0.1. Each configuration produced ELF, map, UF2, size, and SHA-256
  provenance artifacts.
- Portable plugin manifests validate against the checked-in official 1.0.0
  schemas, skill frontmatter and marketplace registration pass, and the
  installed-MCP acceptance above validates the plugin's command surface.
- Full repository validation passed: locked resolution, Ruff, mypy (89 source
  files), 1,425 pytest tests, and `git diff --check`. `graphify update .`
  refreshed the module graph; its existing `fixture_protocol.h` partial-
  extraction warning remains. Both GitHub workflow files also pass YAML syntax
  parsing and tests enforce commit-pinned actions and the intended job matrix.

Phase 4 named coding-host acceptance, reviewed 2026-09-21:

- VS Code 1.138.0 with the OpenAI coding-agent extension 26.908.40401 hosted
  the active acceptance session. From that host, the Coding Agent launched the
  absolute `.venv/bin/dutchmate-debug` entrypoint and reproduced the reviewed
  `qwen3:4b` preview manifest and digest for completed native session
  `20260913T174342Z-ebdcfa44`. The preceding digest-approved live analysis was
  also run from this VS Code-hosted agent session.
- A temporary Claude Code 2.1.278 client launched successfully, but its official
  authentication status was `loggedIn: false`; the user confirmed that no
  Claude Code subscription is available. No DUTchMate prompt or evidence was
  submitted. The login was cancelled and all temporary client and configuration
  files were removed. Claude Code acceptance is unavailable rather than failed.
- Documentation now distinguishes the host-facing Debug Agent CLI from MCP
  registration and states that a coding agent may skip local-model analysis.
- Full repository validation passed: Ruff, mypy (87 source files), 1,402 pytest
  tests, and `git diff --check`.

Phase 4 live local-model smoke and citation-constrained Ollama output, reviewed
2026-09-20:

- An isolated local Ollama 0.33.0 runtime served `qwen3:4b` for a completed
  native session (`20260913T174342Z-ebdcfa44`). The host-facing `preview`
  returned manifest digest
  `8b5f89667a55a1f75ee7f26ac15c42115464c95030b8512a954f2e286f1455e0`;
  `analyze` with that digest returned a validated report preserving request
  digest `fbacbd3ef7721e9ea307cf4e4904b1962274ab77591a8a4e16e607ac147ccd98`,
  native first-error coordinates, and a citation to selected UART ordinal 0.
  The source-area recommendations named two paths absent from the repository;
  model recommendations remain advisory.
- Initial unconstrained live attempts timed out or used invalid citation
  coordinates. The adapter now disables model thinking, bounds context and
  output tokens, rejects token-limit truncation, and supplies a structured
  output schema constrained to coordinates in the frozen request. Focused
  tests cover the selected-coordinate schema and truncation response. Named
  VS Code and Claude Code host UIs were not exercised in this smoke run.
- Full repository validation passed: Ruff, mypy (87 source files), 1,402 pytest
  tests, changed-file Ruff format check, and `git diff --check`.

Phase 4 local Ollama adapter and host-facing CLI, reviewed 2026-09-20:

- Fourteen new tests cover the exact local chat request and validated report,
  local-origin and redirect rejection, malformed responses, disabled default,
  explicit context input, manifest-digest approval, model changes, timeout,
  and invalid-output failure without a partial report. The Debug Agent package
  has 82 focused tests; existing fixture tests still cover remote opt-in and
  no-fallback behavior at the generic provider boundary.
- Full repository validation passed: Ruff, mypy (87 source files), 1,400 pytest
  tests, changed-file Ruff format check, `git diff --check`, and offline uv
  lock check. The workspace package installed from the frozen lock and its
  `dutchmate-debug --help` entrypoint launched. The incremental Graphify update
  refreshed the module graph; its
  existing `fixture_protocol.h` partial-extraction warning remains.
- The local Ollama endpoint at `127.0.0.1:11434` was not running during this
  review, so no live-model or named host UI result is claimed.

Phase 4 report and provider boundary, reviewed 2026-09-20:

- Nineteen new tests passed for selected-evidence citations, advisory
  first-failure separation, native provenance warnings, bounded recommendations,
  secret-free report metadata, disabled default, local/remote fixture parity,
  pre-submission manifests, remote opt-in, request size, timeout, invalid output,
  provider failure, immutable manifest limits, and no fallback. The Debug Agent
  package now has 68 focused tests. No concrete provider SDK or credentials were
  added.
- Full repository validation passed: Ruff, mypy (85 source files), 1,386 pytest
  tests, changed-file Ruff format check, and `git diff --check`. The incremental
  Graphify update refreshed the module graph; its existing `fixture_protocol.h`
  partial-extraction warning remains.

Phase 4 Coding Agent context and analysis request, reviewed 2026-09-20:

- Thirty-two new tests passed for source/diff provenance, exact session
  correlation, path and secret rejection, per-field/aggregate limits, and
  native evidence composition without repository lookup. The Debug Agent
  package now has 49 passing focused tests.
- Full repository validation passed: Ruff, mypy (83 source files), 1,367 pytest
  tests, and `git diff --check`. Changed Python files pass Ruff formatting;
  repository-wide format check still reports 66 previously unformatted files.
  `graphify update .` refreshed the module graph with the existing
  `fixture_protocol.h` partial-extraction warning.

Phase 4 conditional baseline context, reviewed 2026-09-20:

- Six new tests passed for absent designation, a valid designated comparison,
  timing-provenance mismatch, an active ineligible subject, corrupt pointer
  rejection, and pointer retargeting during assembly. The Debug Agent package
  now has 17 passing focused tests. The projected comparison omits raw UART
  line-change text while retaining its bounded counts and timing state.
- Full repository validation passed: Ruff, mypy (81 source files), 1,335 pytest
  tests, and `git diff --check`. `graphify update .` refreshed the module graph;
  its existing `fixture_protocol.h` partial-extraction warning remains.

Phase 4 bounded evidence excerpts, reviewed 2026-09-20:

- Seven new end-to-end session-store tests passed for early failure/pattern and
  session start/end priority, 300-line/64-KiB UART and 100-event hardware caps,
  omission counts, failed/partial and unknown UART TX outcomes, active sessions,
  corrupt UART text rejection, and reconnect segment ordering. The Debug Agent
  package now has 11 passing focused tests.
- Full repository validation passed: Ruff, mypy (80 source files), 1,329 pytest
  tests, and `git diff --check`. `graphify update .` refreshed the module graph;
  its existing `fixture_protocol.h` partial-extraction warning remains.

Phase 4 native session-facts slice, reviewed 2026-09-20:

- The new `dutchmate-debug-agent` workspace package imports from the installed
  environment and depends only on `dutchmate-core`. Four focused tests exercise
  native fact projection, bounded metadata without raw evidence arrays, legacy
  and unknown schema rejection, and path-safe session IDs.
- Full repository validation passed: Ruff, mypy (76 source files), 1,322 pytest
  tests, and `git diff --check`. `uv lock` and `uv sync --all-packages --frozen`
  resolved and installed the complete workspace.
- `graphify update .` refreshed the structural graph. Extraction warned that
  the existing `hardware/firmware/zephyr_dut/src/fixture_protocol.h` could be
  only partially parsed; that header supplied no graph symbols.

Phase 2 live MCP smoke, reviewed 2026-09-20:

- Device Core started with the connected Enhanced Pico 2 on
  `/dev/cu.usbmodem11401` at 460800 baud; status showed a connected device, no
  active workflow, and all four controls unconfigured. The locally installed
  Python SDK launched `.venv/bin/dutchmate mcp` by absolute path with the
  virtual environment removed from `PATH`, negotiated modern stdio, and listed
  the exact nine tools.
- A read-only `get_recent_uart_log` call with `lines=1` reached the live service
  as `GET /dut/logs?lines=1` and returned HTTP 200 plus a complete structured
  MCP result. The verification checked schema fields without printing UART
  content or the session identifier. No reset, capture, or control tool was
  called. Device Core was stopped afterward, and stopped status was confirmed.

Phase 2 scoped stdio acceptance, reviewed 2026-09-20:

- The acceptance interpretation is now explicit in
  `docs/mcp_integration_plan.md`: direct modern stdio behavior and the existing
  SDK/tool contract tests are primary; the official HTTP-only conformance
  projection supplies only named, applicable supporting checks. Optional
  fixture/HTTP features are excluded without being reported as passes.
- A new installed-CLI subprocess test passed modern SDK v2 discovery, the exact
  nine-tool catalog, and a complete structured `service_unavailable` result
  over real stdio with no virtual-environment `PATH`. Its Device Core URL was
  deliberately unreachable. The official Inspector 2.7.0 CLI again passed
  strict modern stdio `tools/list` and returned the same nine names.
- The pinned official `2026-07-28` requirement set was rerun against a
  temporary loopback HTTP projection of the same `create_server()` composition,
  again with unreachable Device Core. Of 50 scenarios, the full suite reported
  104 passed checks and 61 failed, including 13 unscored scenarios. The scoped
  stateless case passed 23 checks; only its two synthetic sampling-tool checks
  failed. All three `tools-list` checks and the four required tool-cache/TTL/
  scope/schema checks passed. The projection was stopped after validation and
  is not part of the product.
- Ruff passed, mypy found no issues in 74 source files, all 1,318 pytest cases
  passed, and `git diff --check` found no whitespace errors. The Phase 2
  tools-only stdio exit gate is accepted; named host UIs remain follow-up
  validation when available, and deferred Phase 1 hardware gates are unchanged.

Phase 2 host registration and conformance investigation, reviewed 2026-09-20:

- The developer guide now gives named VS Code and Claude Code stdio
  registrations. Neither host UI is installed or independently exercised in
  this workspace; the installed CLI's absolute-path launch is covered by a
  subprocess regression with the virtual environment removed from `PATH`.
- Official MCP Inspector 2.7.0 CLI connected to the installed
  `.venv/bin/dutchmate mcp` over modern stdio, passed strict `tools/list`
  validation, and returned the nine tools in documented order. Local Node
  22.18.0 is below Inspector's declared 22.19.0 minimum, though this check
  completed successfully. No live session data was requested.
- Official conformance CLI 0.2.0-alpha.11 accepts an HTTP URL, not a stdio
  command. Its pinned `2026-07-28` requirement set was run against a temporary
  loopback HTTP projection of the same `create_server()` composition, with an
  unreachable Device Core URL so it could not access hardware or sessions.
  This projection is not a shipped transport and was stopped after the run.
- The suite ran 50 scenarios and reported 104 checks passed, 61 failed; 13
  scenarios were explicitly unscored for this requirement revision, 11 of
  those failing. Its fixed fixture expects optional prompts, resources,
  synthetic media/progress/sampling tools, and HTTP behavior that the Phase 2
  stdio product does not expose. The scoped `server-stateless` run passed
  23 of 25 applicable checks; the two failures require a synthetic sampling
  tool absent from DUTchMate. `tools-list` passed all three checks.
- The initial run exposed an actual capability mismatch: SDK 2 served empty
  prompt/resource lists despite tools-only discovery. Focused wire tests
  reproduced it before the fix and now verify `METHOD_NOT_FOUND`; the official
  capability-declaration and handler-match checks both pass. The fix removes
  SDK default handlers via its internal registry, which should be retested
  when upgrading SDK 2. At this investigation, Phase 2 remained open pending
  a defensible stdio conformance acceptance gate.
- Fresh repository validation passed: Ruff reported `All checks passed!`, mypy
  found no issues in 74 source files, the full pytest suite passed 1,317 cases,
  and `git diff --check` reported no whitespace errors.

Phase 2 MCP CLI launch wiring, reviewed 2026-09-17:

- `dutchmate mcp` accepts `--service-url`, `DUTCHMATE_SERVICE_URL`, and the
  five supported log levels, then replaces itself with `dutchmate-mcp` while
  inheriting stdin, stdout, and stderr.
- The CLI and MCP delivery packages remain import-independent. The MCP
  entrypoint owns final URL/default resolution, normalizes log levels for the
  SDK, and exposes stdio as its only transport.
- Focused launch tests pass all 17 CLI, entrypoint, and server-composition
  cases. A real EOF subprocess at debug level exits cleanly without writing to
  stdout.
- The installed `dutchmate mcp --log-level debug` process chain also exits zero
  on EOF with empty stdout and diagnostic output confined to stderr.
- Fresh repository validation passed: Ruff reported `All checks passed!`, mypy
  found no issues in 74 source files, the full pytest suite passed 1,314 cases,
  and `git diff --check` reported no whitespace errors.
- Graphify refreshed the new CLI launch module and cross-package executable
  relationship: 4,839 nodes, 12,762 edges, and 251 communities. Its existing
  partial-extraction warning for the Zephyr fixture header remains unchanged;
  firmware compilation and tests remain authoritative for that source.

Phase 2 modern MCP protocol integration, reviewed 2026-09-17:

- The SDK v2 client connects through its stream-framed in-memory transport,
  completes `server/discover` at `2026-07-28` without an `initialize`
  handshake, and receives the fixed DUTchMate identity, instructions, tools
  capability, complete result type, and private 300-second cache hint.
- DUTchMate now overrides the generic SDK discovery capability advertisement:
  the fixed tool catalog reports `listChanged: false`, while unused prompt and
  resource capabilities are absent. SDK wire validation, response identity
  stamping, and cache-hint stamping remain unchanged.
- Two uncached `tools/list` calls return the same nine tools in documented
  order. Every observed modern request carries protocol version, client info,
  and client capabilities in `_meta`, with no HTTP transport request or MCP
  session identifier.
- Stream tests also preserve a complete structured tool call, exact
  `UnsupportedProtocolVersion` context, cancellation through
  `notifications/cancelled`, and sub-second clean EOF shutdown. The legacy SDK
  handshake smoke test lists the same nine tools.
- Focused MCP validation passes all 29 server, service-client, protocol
  baseline, and modern/legacy integration tests.
- Fresh repository validation passed: Ruff reported `All checks passed!`, mypy
  found no issues in 73 source files, the full pytest suite passed 1,305 cases,
  and `git diff --check` reported no whitespace errors.

Phase 2 MCP tool registration and error projection, reviewed 2026-09-17:

- `create_server()` registers the nine documented tools in their normative
  order while retaining the fixed server identity and private finite cache
  hints.
- Each tool delegates through a short-lived `DeviceCoreClient`, returns the
  service's JSON object as complete structured content, and makes no direct
  serial, firmware-protocol, GPIO, or model-provider call.
- Local argument failures return `invalid_argument` without HTTP dispatch.
  Canonical Device Core failures retain their exact code, detail, truncation
  marker, and optional context. Connection and invalid-response failures use
  bounded `service_unavailable` and `service_protocol_error` results.
- Focused MCP server/client tests pass: 23 tests, including all nine endpoint
  wrappers, deterministic listing, success projection, structured service
  errors, unavailable service handling, invalid response handling, and UART
  payload byte-limit context.
- Fresh repository validation passed: Ruff reported `All checks passed!`, mypy
  found no issues in 73 source files, the full pytest suite passed 1,300 cases,
  and `git diff --check` reported no whitespace errors.

Five-cycle helper-side TX pull-up repeatability, reviewed 2026-09-17:

- `hardware/validation/evidence/20260917-tx-pullup-five-cycles-digital.csv`
  spans 300.812861440 seconds. D1 and D2 each have 396 transitions forming
  exactly six PONG packets with valid stop bits. There are no other transitions;
  paired edge timestamps differ by no more than 40 ns.
- Session `20260917T200511Z-b56c8116` completed its requested 300 seconds with
  exactly six PONGs (66 bytes) for six successful sends. It has one segment,
  zero reported loss, and no overflow, interruption, resumption, or truncation.
- This passes the planned repeatability comparison and establishes that the
  helper-side 10 kOhm idle-high bias prevents the reproduced TX-disconnect
  disturbance. The accepted next-revision correction retains TXU0202 and adds
  10 kOhm from `UART_TX`/`U1.B2` to `DUT_VIO`.

Helper-side TX pull-up comparison, reviewed 2026-09-17:

- The operator installed 10 kOhm from J1 pin 4 (`DUT_UART_TX`) to the existing
  3.3 V `DUT_VIO`, leaving it and D2 on the helper side during the TX wire cycle.
- `hardware/validation/evidence/20260917-tx-paired-with-pullup-digital.csv`
  spans 138.529996800 seconds. D1 and D2 each have 198 transitions forming only
  three exact PONG packets, all with valid stop bits. Corresponding edge times
  differ by at most 40 ns; neither channel has wire-cycle transitions.
- Session `20260917T195304Z-a810227d` completed its requested 300 seconds and
  retained exactly three PONGs (33 bytes) for three successful sends, with no
  extra receive bytes. It has one segment, zero reported loss, no overflow,
  interruption, resumption, or truncation.

Corrected paired-probe TX cycle, reviewed 2026-09-17:

- `hardware/validation/evidence/20260917-tx-paired-corrected-digital.csv`
  shows matching PONGs on D1 (Pico 2 GP1) and D2 (J1 pin 4). D1 additionally
  has four low intervals during CSV seconds 215.555–233.268; D2 stays high
  throughout that interval. Sampling the abnormal starts at 460800 8-N-1
  yields `00 F8 00 00`, with invalid stop bits on all three zero candidates.
- Session `20260917T152349Z-8e3cd93e` completed its 300 seconds normally:
  37 raw bytes, three successful sends/PONGs, one segment, zero reported loss,
  no overflow/interruption/truncation. The extra bytes have corresponding
  receive-pin disturbances; this does not prove the translator itself faulty.
- The preceding passive session `20260917T152150Z-ff5f724f` completed in
  10 seconds with ten advancing buffer-status events and no reported loss.
  The separate handshake/lifecycle failure remains unexplained.

Corrected-probe baseline timeout, reviewed 2026-09-17:

- `hardware/validation/evidence/20260917-paired-baseline-timeout-digital.csv`
  records both signals high throughout 94.841077760 seconds, with no edges.
  Both probes monitor the reply path, so this does not prove whether PING
  reached the fixture.
- Session `20260917T151535Z-d8c07406` has zero received bytes, one timed-out
  PING with unknown accepted-byte count, a `usb_disconnect` event, and a
  terminal `reconnect_timeout`. The OS still lists Pico 2; the event does not
  establish a physical USB unplug. A fresh service start also failed to receive
  Enhanced hello. The cause remains unresolved; no wire-cycle result was obtained.

Paired-probe attempt, reviewed 2026-09-17:

- Retained `hardware/validation/evidence/20260917-tx-paired-hotplug-digital.csv`
  contains three clean PING packets on its first signal column and three clean
  PONG packets on its second, with no other transitions. The operator confirmed
  D1 was on Pico 1 GP1, so it does not establish translator input/output behavior.
- Session `20260917T144831Z-0f9b7835` completed by `duration_elapsed` with
  39 bytes: three PONGs plus `00 00 00 00 F8 00`. The extra bytes approximately
  align to CSV seconds 81.232–91.513, when both exported signals are high.
  One segment, zero reported buffer loss, no overflow or interruption; the
  extra received bytes remain corruption evidence despite those integrity flags.

TX-only trace discrepancy, reviewed 2026-09-17:

- `hardware/validation/evidence/20260917-tx-only-hotplug-digital.csv` decodes
  three clean PING/PONG exchanges, with no extra D2 transitions. Session
  `20260917T090848Z-ebdef0d3` includes the same three PONGs plus 17 extra
  bytes, approximately aligned to CSV seconds 62.320-69.066, when D2 is high.
- Recovery commands succeeded immediately without reset. The discrepancy
  remains unresolved pending physical probe verification and a trace across
  the translator; no firmware change is justified by this evidence alone.
- A later USB disconnect at 09:13:27 UTC ended the session at 09:13:32 UTC
  with `reconnect_timeout` and `interrupted=true`. The run is partial evidence,
  not an uninterrupted acceptance pass. Its 50 raw bytes, one segment, zero
  reported buffer loss, and artifact hashes are preserved in the validation
  record. Service status confirmed stopped on resumption.

Fixture-RX pull-up comparison, reviewed 2026-09-17:

- The user installed 10 kOhm from Pico 1 GP1 to its own 3.3 V output, keeping
  the pull-up and Saleae D1 on GP1 throughout the RX-only wire cycle.
- Retained CSV `hardware/validation/evidence/20260917-rx-only-hotplug-with-pullup-digital.csv`
  has no RX transitions outside the four clean PING packets. Both post-cycle
  commands returned PONG immediately, matching session
  `20260917T085816Z-5c60e312` (four recorded sends, 72 response bytes).
- The session completed with one segment, zero reported buffer loss, and no
  overflow/interruption. CSV and session hashes are recorded in the validation
  record. Device Core is stopped; the fixture RX pull-up remains installed.
- The initial baseline error still occurred before wire movement. This
  comparison supports a fixture-side undriven-input cause of RX-only hot-plug
  corruption and a local diagnostic mitigation; it does not close startup
  behavior, the opposite UART direction, or full hot-plug acceptance.

Continuous RX-only digital trace, reviewed 2026-09-17:

- The retained `hardware/validation/evidence/20260917-rx-only-hotplug-digital.csv`
  covers baseline, the GP1 wire change, and both recovery commands. D1 is
  Pico 1 GP1/RX; D2 is GP0/TX. CTRL0 is connected to RUN but unconfigured.
- GP1 had irregular digital transitions around 172.295-173.358 s. Commands
  at 214.910 s and 221.777 s both decode as clean `PING\n`; the responses are
  `E_COMMAND_001` then PONG. The return path stayed idle during the wire change.
- Session `20260917T084116Z-b6095f44` contains the matching 61 response bytes,
  three forced sends, one segment, zero reported loss, and no interruption.
  The digital trace localizes the rejection to preceding input activity on the
  disturbed fixture RX path; an undriven input remains the electrical hypothesis
  pending a controlled bias comparison. Full timings and CSV hash are recorded
  in `hardware/validation/phase1_revision_a.md`.

Loaded UART hot-plug, reviewed 2026-09-16:

- Session `20260916T213110Z-dbeb6b07` captured cycle 1 transition bytes,
  `E_COMMAND_001` on the first post-reconnect PING, and PONG on the next.
  Cycle 2 transition bytes were retained, but the recovery sends were late.
- Controlled cycle 3 in `20260916T214409Z-5fedcd96` captured baseline PONG,
  five NUL bytes, `E_COMMAND_001`, and recovery PONG. Both post-reconnect sends
  were inside the active capture and recorded as forced perturbations. No
  reset was needed; Enhanced remained connected with zero reported buffer loss.
- CTRL0 was connected to Pico 1 RUN and configured active-low/open-drain.
  Dedicated boot-test `20260916T214156Z-ad4b412e` captured the expected 63-byte
  reset/boot sequence; normal capture correctly rejected a standalone reset.
- Empty captures `603b59ec`, `ae2d3714`, and `e4258b21` did not encompass the
  corresponding sends. They establish neither UART failure nor recurrence of
  a first-command-after-reset fault. Full IDs, timestamps, raw evidence, and
  the corrected interpretation are in `hardware/validation/phase1_revision_a.md`.
- Recovery with one rejected command is demonstrated; corruption-free loaded
  hot-plug remains unaccepted. The electrical source needs directional traces.
- Cycle 3 completed with 66 raw bytes, one segment, and no overflow or
  interruption. Artifact verification confirmed the exact byte sequence and
  all three successful send records. Hashes are retained in the validation
  record. Device Core was stopped after retrieval; CTRL0-to-RUN wiring remains.

Loaded missing-`DUT_VIO` isolation sweep, reviewed 2026-09-16:

- The user explicitly deferred the populated U1/U2/U3/U5/U6 identity and
  physical pin/net continuity audit. The 75 uA correlation remains separately
  deferred.
- Pico 1, normal `DUT_VIO`, and external pull-ups were disconnected. With Pico
  2 USB as the only normal supply and Device Core stopped, `3V3(OUT)` measured
  3.3 V while `DUT_VIO`, `DBG_UART_IF_EN`, `DBG_INPUT_IF_EN`, and all four
  `DBG_CTRL_ENn` points measured 0.0 V.
- A first unloaded `DUT_CTRL0` injection charged the floating `DUT_VIO` rail to
  1.8 V; both returned to 0.0 V after source removal. The run was repeated with
  a defined 10 kOhm `DUT_VIO`-to-ground load. A current-limited 1.8 V source
  through a separate 10 kOhm resistor was moved across all four `DUT_CTRLx`,
  all four `DUT_EVENTx`, `DUT_UART_RX`, and `DUT_UART_TX` connector lines.
  Every injected line remained at 1.8 V while loaded `DUT_VIO` remained at
  0.0 V.
- This passes the loaded missing-supply/high-impedance check for all ten
  external lines and the DUT-side-supply-absent half of translator isolation.
  No source-current measurement was taken, so absolute leakage remains open;
  the reverse-direction and all-order sequencing checks remained open at this
  point.

Debugger-supply-absent pulled-control isolation, reviewed 2026-09-16:

- Pico USB, Pico 1, UART, and event connections were absent. `DUT_VIO` was
  supplied at 1.80 V with a 1 mA current limit, and each of the four DUT control
  outputs had its own 10 kOhm pull-up to `DUT_VIO`.
- `DUT_VIO` measured 1.8 V and every `DUT_CTRLx` measured approximately
  1.8 V. Pico `3V3(OUT)`, `VSYS`, and `VBUS` each measured approximately
  0.0 V.
- This passes static debugger-supply-absent isolation for every control output
  at 1.8 V. Exact insertion/removal sequencing and direct UART/event loading in
  this supply direction remain open.

Pulled-control supply-order sequence, reviewed 2026-09-16:

- The four individual 10 kOhm control pull-ups were retained while Device Core
  remained stopped. With VIO applied first, USB insertion produced
  `DUT_VIO = 1.8 V`, all controls approximately 1.8 V, `3V3(OUT) = 3.3 V`, and
  every measured enable at 0.0 V. USB removal returned all three Pico rails to
  0.0 V while VIO and all controls remained approximately 1.8 V.
- With debugger USB applied first and VIO absent, VIO and all controls measured
  0.0 V, `3V3(OUT)` approximately 3.3 V, and every measured enable
  approximately 0.0 V. Applying VIO raised VIO and every control to
  approximately 1.8 V without changing the enable readings; removing VIO
  returned VIO and controls to approximately 0.0 V while `3V3(OUT)` remained
  approximately 3.3 V and all measured enables remained approximately 0.0 V.
- These settled readings pass the rail, external pull-up, and measured-enable
  expectations for both supply orders. The active-low `DBG_CTRL_nOE0` through
  `DBG_CTRL_nOE3` nodes were then measured in a direct follow-up.
- In the debugger-first order, all four `/OE` nodes and controls measured
  approximately 1.8 V after VIO application and approximately 0.0 V after VIO
  removal while `3V3(OUT)` remained at 3.3 V. In the VIO-first order, all four
  `/OE` nodes and controls measured approximately 1.8 V before USB connection,
  after USB connection, and after USB removal; the Pico rails remained
  approximately 0.0 V whenever USB was absent.
- This passes the settled all-order `/OE` pull-up and control-disable
  requirement. Transition waveforms remain unmeasured.

Debugger-supply-absent UART/event isolation, reviewed 2026-09-16:

- Pico USB was disconnected, `DUT_VIO` remained at 1.80 V with a 1 mA current
  limit, and Pico `3V3(OUT)` was loaded to ground through 10 kOhm. A second
  10 kOhm resistor pulled each `DUT_EVENT0` through `DUT_EVENT3`,
  `DUT_UART_TX`, and `DUT_UART_RX` high to VIO in turn.
- Every pulled signal measured approximately 1.8 V. Loaded `3V3(OUT)`, `VSYS`,
  and `VBUS` all measured approximately 0.0 V.
- Together with the preceding control sweep, this passes static debugger-
  supply-absent isolation for all ten external digital signals. Hot-plug/
  transient behavior, absolute leakage, and ESD validation remain open.

Repeated unloaded supply hot-plug, reviewed 2026-09-16:

- With Pico USB connected, all external signals disconnected, common ground
  retained, and the 1.80 V/1 mA source enabled, the positive `DUT_VIO` lead was
  connected and disconnected five times. Every cycle behaved identically:
  connected VIO measured approximately 1.8 V, disconnected VIO approximately
  0.0 V, `3V3(OUT)` remained approximately 3.3 V, and every enable remained
  approximately 0.0 V.
- With VIO then held continuously at 1.8 V, Pico USB was disconnected and
  reconnected five times. Every insertion enumerated and every cycle behaved
  identically. With USB connected, `3V3(OUT)` measured approximately 3.3 V,
  all enables approximately 0.0 V, and all four `/OE` nodes approximately
  1.8 V. With USB disconnected, all Pico rails measured approximately 0.0 V
  while VIO and all `/OE` nodes remained approximately 1.8 V.
- This passes repeated unloaded supply hot-plug at 1.8 V using settled readings.
  Loaded DUT-cable hot-plug and transition waveform capture remain open.
- The user then explicitly deferred analog UART cable/edge and series-resistor
  waveform validation because no analog oscilloscope is available. The 25 MS/s
  Saleae can retain digital decoding evidence but cannot close the analog
  waveform checks.

Phase 1 acceptance and voltage-safety audit, reviewed 2026-09-16:

- The normative Phase 1A, Phase 1B, and shared done criteria were compared with
  committed tests and HIL records. All software/protocol/workflow groups have
  evidence; the Revision A first-prototype criterion remains open.
- A source parser confirmed exact agreement for all 17 Revision A mappings
  between section 10.1, legacy EAGLE schematic `U4` pinrefs, legacy EAGLE board
  `U4` pads, and the RP2350 overlay. Legacy EAGLE devicesets/board values match U1
  `TXU0202DCUR`, U2 `TXU0104PWR`, U3 `SN74LV4T125PWR`, and U5/U6
  `SN74LVC2G06DBVR`. This does not prove populated-part identity or physical
  continuity.
- With the 3.3 V Pico 1/Pico 2 fixture connected, malformed channel and
  electrical-mode requests returned CLI exit 2 and service HTTP 400
  `invalid_argument`; duplicate config assignment raised `GpioConfigError`.
  Accepted CTRL0/CTRL1 state, commanded boot mode, and connection state were
  unchanged. The service was stopped afterward.
- The audit found an unconsumed voltage declaration. Enhanced startup now
  requires `hardware.dut_io_voltage` before opening a configured serial port,
  and runtime GPIO configuration requires the declaration before transport
  dispatch. Focused tests observed both regressions fail before implementation
  and pass afterward. Out-of-range declarations remain rejected by the
  existing 1.8–5.0 V parser contract.
- A positive startup with the local trusted declaration set to 3.3 V connected
  the real Pico 2 as `dutchmate-rp2350` firmware `development`, advertised all
  five Enhanced capabilities, reported zero UART loss, and stopped cleanly.
  Its control channels remained unconfigured during this check.
- The deferred 75 uA correlation remains unresolved by user request.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,295 cases, and
  `git diff --check` passed.

Enhanced configured GP2 boot-mode HIL, reviewed 2026-09-15:

- The user wired Revision A `DUT_CTRL1` to Pico 1 GP2, retained
  `DUT_CTRL0` on `RUN`, left GP3 open, and kept 460800-baud UART, common
  ground, and `DUT_VIO=3.3 V`. The normal Pico 2 UF2 was in service. Public
  configuration accepted `CTRL0` open-drain active-low reset and `CTRL1`
  push-pull active-high/idle-low boot control. The operator held Pico 1
  `RUN` low during each GP2 mode change, then released it before each boot
  capture as required by the fixture strap procedure.
- Native 15-second boot sessions `20260915T203733Z-7d502d02` (`normal`),
  `20260915T204533Z-0d15abc2` (`bootloader`), and
  `20260915T204741Z-617d85d9` (restored `normal`) retained exact
  63/82/63-byte fixture output. The two normal raw artifacts share SHA-256
  `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`;
  the GP2-high run retained `E_INIT_001` with SHA-256
  `7ac5b2f71bfd7f1d4da1edf607407c8cfcec70c4e4cb9dc2fd333c6aa26481e4`
  and a detected `ERROR` in segment 0. Every session snapshotted its
  commanded mode, one accepted 100 ms reset, RP2350 device timestamps, one
  segment, `none_reported`/zero loss, and public session/log retrieval.
  Local assertions verified exact raw/event equivalence and control evidence.
- A post-restoration in-session forced `PING` capture
  `20260915T204855Z-51d462a8` returned exact `DMF/1 PONG\n` without
  a first error. The earlier transient first-command rejection did not
  recur; its cause is unestablished. Artifact hashes and action timestamps are
  in `hardware/validation/phase1_enhanced_hil.md`. The service was stopped
  after retrieval, returning its controls to high impedance.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,292 cases, and
  `git diff --check` passed.

Basic/Enhanced downstream evidence comparison, reviewed 2026-09-15:

- The accepted Basic Pico 1/FTDI HIL record and the Enhanced Pico 1/Pico 2 HIL
  record both verify raw UART, normalized events, native session storage, and
  public session/log retrieval through the shared pipeline. The historical
  Basic session files are absent locally, so their original field sets cannot
  be directly re-read.
- A focused deterministic current-code test sends the same `DMF/1 PONG\n`
  payload through fake Basic and Enhanced sources into the real
  `CaptureWorkflow`/`SessionStore` path. It passes equal artifact filename,
  top-level metadata, segment/backend, session-detail, and recent-log field
  sets; UART-event records and raw bytes are identical. Explicit backend
  identity, advertised capabilities, host/device timestamp provenance, and
  `not_observable`/`none_reported` integrity retain their declared mode
  distinctions. The test and comparison limits are recorded in
  `hardware/validation/phase1_enhanced_hil.md`.
- After binding the test's per-mode session ID factory, fresh Ruff passed,
  mypy found no issues in 73 source files, the full pytest suite passed 1,292
  cases, and `git diff --check` passed.

Enhanced idle and active USB reconnect HIL, reviewed 2026-09-15:

- With Pico 1 and the Revision A UART/control wiring left powered, the
  diagnostic Pico 2 image disconnected while idle at 20:05:00 UTC and
  reconnected at 20:05:30 UTC on the same CDC path. An active diagnostic-image
  capture `20260915T200703Z-d86f54e3` failed as `backend_input_error` after
  the image intentionally advanced its `hello.firmware` stack-reading
  identifier. Public retrieval preserved its one interrupted, unresumed
  segment and `usb_disconnect` evidence; the host identity guard behaved as
  specified.
- The operator flashed the normal Zephyr 4.4.2/SDK 1.0.1 Pico 2 UF2 SHA-256
  `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`.
  The replacement `hello` reported stable `development` identity and all
  five Enhanced capabilities. Using the documented 60-second reconnect
  setting for operator timing, active capture
  `20260915T201343Z-57c45321` disconnected at 20:15:00 UTC and resumed
  on the same port at 20:15:15 UTC. It completed after 150 seconds with two
  contiguous device-timestamp segments, `usb_disconnect`,
  `usb_reconnect`, and `timestamp_discontinuity` records, `interrupted`
  and `resumed` flags, no reported loss/overflow, and public session/log
  retrieval. The first segment retained a Pico 1 generic command-error line;
  two exact `PONG` lines were captured in the second segment. The first
  `PING\n` host payload and send acknowledgement were exact; the fixture
  rejection's cause is not established. Artifact hashes and the diagnostic
  image limitation are in `hardware/validation/phase1_enhanced_hil.md`.
  The service was stopped and the local reconnect setting restored to 5.0
  seconds after the run.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,291 cases, and
  `git diff --check` passed. Local HIL assertions also verified the idle
  state sequence, preserved diagnostic-image failure, two-segment normal-image
  resume, raw-byte/UART-event equivalence, and ordered lifecycle records.

Enhanced configured boot workflow and lifetime-counter host correction,
reviewed 2026-09-15:

- User-confirmed Pico 1 460800-baud fixture, Pico 2 diagnostic UF2, `CTRL0` to
  Pico 1 `RUN`, common ground, and `DUT_VIO=3.3 V` formed the live HIL setup.
  Initial session `20260915T192952Z-2cf24586` retained the exact 63-byte
  boot output and a successful 100 ms reset, but its first `buffer_status`
  carried the earlier dense run's absolute 23,663 dropped bytes and six
  overflow events. The host falsely marked this clean new boot as lost.
- After the host correction, session `20260915T194748Z-78db848e` again
  retained reset `0x00` plus the exact 62-byte
  `phase1-enhanced-460800-001` fixture marker. It completed in one segment
  with device `rp2350_timer` timestamps, `none_reported` loss, zero session
  overflow, no interruption, and successful public `dutchmate session`
  retrieval. Its 63 raw bytes have SHA-256
  `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`.
  The first raw `buffer_status` still records 23,663 lifetime dropped bytes
  and six lifetime overflow events; the firmware wire/evidence format is
  unchanged. Details and artifact hashes are in
  `hardware/validation/phase1_enhanced_hil.md`.
- Same-fixture session `20260915T195131Z-28e6d4b8` accepted a forced `BURST`
  UART send during capture and retained 19,079 plus 24,002 explicitly dropped
  bytes, exactly reconciling the 43,081-byte fixture output. Six current-session
  overflow records, BEGIN/END markers, `loss_reported` integrity, and one
  uninterrupted segment survived despite a nonzero MCU-lifetime starting
  counter. The service was stopped after the test.
- Regression tests cover prior lifetime counters, new status deltas, explicit
  overflow before the first status, two reconnect segments, and idle health
  projection. Fresh Ruff passed; mypy found no issues in 75 source files; all
  1,291 pytest cases passed; and `git diff --check` passed.
- The shared capture-storage port changed to pass capture-window counter totals
  without altering raw MCU status evidence. `graphify update .` refreshed the
  structural graph to 4,754 nodes and 12,575 edges. Its existing Zephyr fixture
  macro-heavy header warning did not affect the update.

Ring-buffer final stack and load HIL, reviewed
2026-09-15:

- The first USB-only diagnostic image measured CDC RX at 3,872/4,096 bytes,
  leaving only 224 bytes. The corrected image SHA-256 is
  `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66`.
  It reports `stackprobe-1` and all five Enhanced capabilities and froze all
  eight thread/ISR high-water readings after each revised workload.
- Revised boot session `20260915T191042Z-7b355b2a` retained the exact 63-byte
  reset byte plus fixture marker with zero loss/overflow and one segment. The
  504.049 ms backpressure session `20260915T191158Z-a59e0ff6` retained the
  exact 94,299-byte stream, all 4,096 numbered records and checksum 8,386,560,
  zero loss/overflow, and one segment. Dense session
  `20260915T191317Z-172eb838` reconciled 19,418 retained plus 23,663
  explicitly dropped bytes to the 43,081-byte fixture output with six overflow
  records, visible `loss_reported`, and one uninterrupted segment.
- Revised CDC RX high-water was 3,872/5,120 bytes under backpressure and
  overflow, leaving 1,248 bytes (24.4%); the other seven stacks kept 272–1,808
  bytes free. Final normal static RAM is 81,040/532,480 bytes, leaving 451,440
  bytes; the diagnostic build uses 82,136 bytes. No allocation, stack, watchdog,
  USB CDC, or lifecycle failure was observed. The ring record is `accepted_32k`.
- The corrected source passed Ruff, mypy on 73 application files and both HIL
  helper scripts, all 1,286 pytest cases, both Zephyr 4.4.2 RP2350 target
  builds, and `git diff --check` before the revised HIL. After the evidence/status
  update, fresh Ruff passed, mypy found no issues in 75 source files, all 1,286
  pytest cases passed, and `git diff --check` passed.

Revision A initial electrical validation record, reviewed 2026-09-11:

- The user confirmed that the connected hardware is a fully assembled Revision
  A translator prototype. macOS enumerated DUTchMate Debug Helper
  `2E8A:000A`, serial `FA63A4D787572B33`, at
  `/dev/cu.usbmodem11401`.
- With the DUT and `DUT_VIO` absent, pre-epoch, active-epoch, and post-epoch
  enable/output measurements were qualitatively as expected. Device Core
  reported the Enhanced backend connected with all control channels
  unconfigured, UART TX policy disabled, and zero reported loss. Exact numeric
  readings and calibrated instrument identity were not recorded, so those
  checklist items remain open.
- One initial direct adapter epoch received `hello` and then observed a USB
  re-enumeration through pyserial errno 6. A 4.119-second raw epoch and three
  further consecutive epochs did not reproduce it; all delivered complete
  `hello` and zero-loss `buffer_status` frames. The transient remains recorded
  for later reconnect/load correlation.
- With USB disconnected and `DUT_VIO` supplied at 1.80 V with a 1 mA current
  limit, idle current was 25.2 uA, below the documented 50 uA target. Pico
  `VSYS` and `VBUS` measured 0 V. Pico `3V3(OUT)` measured 0.13 V on an old,
  uncalibrated DMM.
- With `DUT_VIO` still at 1.80 V, connecting Pico USB while Device Core remained
  stopped produced a 28.93 uA steady-state `DUT_VIO` current. `DUT_VIO` remained
  1.8 V, Pico `3V3(OUT)` reached 3.3 V, and `DBG_UART_IF_EN`,
  `DBG_INPUT_IF_EN`, and all four `DBG_CTRL_ENn` signals measured 0.0 V. This
  passes the safe enable-state expectations for that VIO-first power-up
  sequence but does not prove output high impedance or cover every ordering.
- With `DUT_VIO` kept at 1.80 V and Device Core stopped, Pico USB was then
  disconnected. The operator reported that settled current, `DUT_VIO`, and all
  interface/control enable voltages were as expected. Exact values were not
  recorded, so this is preliminary power-down evidence rather than an accepted
  reproducible checklist result.
- With Pico USB connected first and Device Core stopped, applying `DUT_VIO` at
  1.80 V with a 1 mA current limit produced a 28.96 uA steady-state current.
  `DUT_VIO` measured 1.8 V, Pico `3V3(OUT)` measured 3.3 V, and every interface
  and control enable measured 0.0 V. This passes the measured enable-state
  expectations for that debugger-first power-up sequence but does not close
  the broader high-impedance or all-orderings checks.
- With Pico USB left connected and Device Core stopped, the bench supply was
  turned off and disconnected from `DUT_VIO` while common ground remained.
  `DUT_VIO` measured 0.0 V, Pico `3V3(OUT)` remained 3.3 V, and every interface
  and control enable measured 0.0 V. This passes the measured rail and enable
  expectations for that debugger-first VIO power-down sequence without proving
  high impedance or loaded leakage.
- With both rails powered and `DUT_VIO` at 1.80 V, an Enhanced 460800-baud epoch
  with UART TX policy disabled and controls unconfigured measured 28.93 uA,
  `DBG_UART_IF_EN = 3.3 V`, `DUT_UART_RX = 1.8 V`, and every unrelated enable at
  0.0 V. Device Core remained connected with zero reported loss. After clean
  shutdown, current measured 28.96 uA and both `DBG_UART_IF_EN` and
  `DUT_UART_RX` measured 0.0 V while all other enables remained 0.0 V. This
  passes the recorded static active/post-epoch voltage expectations, not UART
  output high impedance.
- The first DUT-side loopback attempt exposed a firmware CDC ingress defect:
  device-to-host telemetry continued, but `uart_send` and a raw invalid command
  both timed out. The registered CDC callback now drains RX readiness with the
  Zephyr FIFO API and queues bounded bytes to the command thread. The reusable
  command-ingress probe failed before the correction and passed after flashing
  the corrected 104,448-byte UF2 with SHA-256
  `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`.
- With the loopback installed, `DUT_VIO = 1.8 V`, and idle current at 28.94 uA,
  capture `20260910T192926Z-033765ed` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_1V8_460800_A5\n` payload at 460800 baud. The device
  accepted all 33 bytes; the session completed with zero reported loss, no
  overflow, one segment, and RP2350 timer provenance.
- At `DUT_VIO = 2.5 V`, idle current measured 39.96 uA, below the 60 uA target.
  Capture `20260910T193944Z-07bc3bc9` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_2V5_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance.
- At `DUT_VIO = 3.3 V`, idle current measured 54.47 uA, below the 70 uA target.
  Capture `20260910T194704Z-334fb7df` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_3V3_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance.
- At `DUT_VIO = 5.0 V`, idle current measured 79.66 uA, below the 100 uA
  target. Capture `20260910T195209Z-b9518e95` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_5V0_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance. This completes the short-jumper functional loopback sweep
  across all four supported VIO points; electrical margins and remaining baud
  rates are still open.
- At `DUT_VIO = 1.8 V`, `CTRL0` through `CTRL3` each passed configured
  push-pull idle-low, active-high, return-to-idle, and post-epoch disabled
  measurements. Enabled currents ranged from 68.0 uA to 68.76 uA; active-high
  DUT outputs measured 1.8 V, idle-low outputs measured 0.0 V, and post-epoch
  current returned to 28.90–28.95 uA with all target control signals at 0.0 V.
  Representative unrelated enables remained at 0.0 V.
- Two earlier `CTRL0` epochs entered the measured safe-disabled state and
  required USB power cycling. The operator later reported removing the UART
  loopback during the measurement, leaving the enabled `DUT_UART_TX` receiver
  floating. A controlled repeat with the loopback continuously installed held
  the configured idle-low state for five minutes with zero reported loss and
  did not reproduce the interruption. This is recorded as the likely cause,
  not a conclusively identified firmware fault, because no fault-source
  telemetry was available.
- At `DUT_VIO = 2.5 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Enabled current measured 93.71–94 uA, the active-high DUT output measured
  2.5 V, and post-epoch current returned to 39.98 uA with all target control
  signals at 0.0 V.
- At `DUT_VIO = 3.3 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Enabled current measured 122.60–122.70 uA, the active-high DUT output measured
  3.3 V, and post-epoch current returned to 54.60 uA with all target control
  signals at 0.0 V.
- At `DUT_VIO = 5.0 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Idle-low current measured 184.12 uA, the active-high DUT output measured
  5.0 V at 243.26 uA, and returned idle-low measured 183.96 uA. The active-high
  increase remained with the DMM disconnected and reproduced on `CTRL1`
  (183.44 uA idle-low, 243.13 uA active-high), identifying expected U3
  state-dependent input supply current rather than channel-specific leakage.
  After returning `CTRL1` idle-low at 183.78 uA, clean epoch shutdown returned
  current to 79.79 uA with all measured control and unrelated enable signals at
  0.0 V. This completes representative push-pull level validation across all
  four supported VIO points.
- At `DUT_VIO = 1.8 V`, `CTRL0` passed representative open-drain reset
  assertion/release and loaded high-impedance behavior against an external
  10 kOhm pull-up to `DUT_VIO`. Released current measured 29.34–30 uA with
  `DUT_CTRL0 = 1.8 V`; held assertion measured 239.44 uA with
  `DUT_CTRL0 = 0.0 V`. A Saleae measured a commanded 250 ms reset pulse as
  250.853 ms with clean edges and approximately 240 uA asserted current. Final
  shutdown returned to 29.87 uA, the external pull-up restored `DUT_CTRL0` to
  1.8 V, and all measured enables were 0.0 V.
- A pre-fix 10,000 ms reset request reproduced the fixed 1.0-second Enhanced
  command-response timeout. After correcting that layer, a 2,000 ms retry
  exposed the CLI's independent fixed 2.0-second HTTP timeout while the service
  and transport remained connected. Focused regression tests now require the
  Enhanced adapter to use `max(1.0 s, pulse + 0.5 s)` and the CLI to use
  `max(2.0 s, pulse + 1.0 s)`, while retaining their existing minima for short
  operations. Real 2,000 ms and maximum 10,000 ms reset commands then completed
  successfully. The Saleae measured 2.000 s and 10.00 s with clean 1.8 V/0.0 V
  edges; PPK2 measured approximately 240 uA asserted and 30 uA released. Status
  after each command remained connected in the same Enhanced epoch with
  `CTRL0` configured and zero reported UART loss.
- TDD red first proved a 2,000 ms pulse still received only the old 1.0-second
  Enhanced timeout, then separately proved the CLI still assigned its old
  2.0-second HTTP timeout. The focused Enhanced and CLI suites passed with 77
  tests after both corrections. Ruff passed; mypy reported no issues in 73
  source files; full pytest passed with 1,276 tests; and `git diff --check`
  found no whitespace errors.
- With the service stopped, `DUT_VIO = 1.8 V`, and an external 10 kOhm pull-up
  moved across `DUT_CTRL0` through `DUT_CTRL3`, every DUT control output stayed
  at 1.8 V without a low glitch while the Pico 2 `RUN` input was grounded for
  approximately one second. Target enable/data signals and all unrelated
  enables remained 0.0 V, PPK2 current stayed near 30 uA, and the RP2350 USB
  device reappeared after release. This passes the every-control-output
  debugger-reset high-impedance item at the representative 1.8 V point.
- With Pico USB and Saleae signal leads disconnected, the PPK2 supplied
  `DUT_VIO = 1.8 V` at a 1 mA limit. Pico `VSYS` and `VBUS` remained 0.0 V.
  Loading Pico physical pin 36 from `3V3(OUT)` to ground through 10 kOhm
  collapsed the unloaded 0.13 V reading to 0.02 V; average PPK2 current stayed
  at 75 uA and maximum current changed from 85 uA to 82 uA. This passes the
  specific debugger-unpowered source-impedance check as high-impedance leakage
  or instrument offset. It remains instrument-limited because the DMM identity,
  calibration, accuracy, and input impedance are unknown. The 75 uA absolute
  reading did not reproduce the earlier 25.2 uA idle measurement and remains
  flagged for controlled-load correlation.
- A pristine `rpi_pico2/rp2350a/m33` build at application commit
  `3e149a530bfa6fd2b29682874f2942d619d7a30c` reproduced under Zephyr 4.4.2 and
  SDK 1.0.1. It used 52,012 bytes flash and 78,032 of 532,480 RAM bytes. The
  complete 45,136-byte RX-ring object contains the selected 32,768 raw bytes,
  512 timestamp descriptors, and accounting state. Configured stacks total
  14,144 bytes, the system heap is zero, and 454,448 bytes of static RAM margin
  remain. The 104,448-byte UF2 SHA-256 is
  `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`,
  matching the digest of the file previously reported as flashed; no Pico
  readback was performed. Runtime stack high-water and HIL load profiles remain
  open; detailed ignored-tree artifacts and hashes are recorded in
  `hardware/validation/phase1_ring_buffer.md`.
- The accepted Pico 1 Basic fixture defaults to 115200 baud, which cannot drive
  the fixed 460800-baud Debug Helper ring-buffer profile. A new opt-in
  `rpi_pico_460800.overlay` preserves that Basic default while setting UART0
  `current-speed` to 460800 for Enhanced HIL. A pristine Zephyr 4.4.0/SDK 1.0.1
  target build confirmed generated `current-speed = < 0x70800 >` and immutable
  build ID `phase1-enhanced-460800-001`. The 34,304-byte candidate UF2 SHA-256
  is `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6`.
  It was flashed on 2026-09-12. A direct 25 MS/s Saleae capture decoded the
  exact 62-byte build marker at 460800 8-N-1. Integrated sessions then exposed
  that Pico 1 GP0 TX stays low during reset, creating PL011 break/framing flags
  before its valid marker begins 28.647 ms after `RUN` release. The old Debug
  Helper classified those positive line errors as fatal, disabled
  `DBG_UART_IF_EN`, and stopped servicing later CDC epochs. Sessions
  `20260912T201857Z-7d797e80` and `20260912T204452Z-1f60f8f1` each retained one
  `0x00` instead of the marker. Focused TDD now proves positive line-error flags
  preserve the epoch and later valid ring input, while a negative driver result
  remains fatal. The 93-test Debug Helper suite and a pristine Zephyr 4.4.2/SDK
  1.0.1 RP2350 target build pass. The corrected 104,448-byte UF2 SHA-256 is
  `94a633420025ed1564b8066ca48adb1dc5b619df7c17d754ec84939a81f86bc8`;
  it was flashed on 2026-09-12. Sessions
  `20260912T212549Z-09d805d0` and `20260912T213056Z-dbb8e66c` each completed a
  15 s Enhanced boot test with the reset-induced `0x00` byte followed by the
  exact marker, 62-byte ring high-water, zero dropped bytes, zero overflow,
  and no connection interruption. Saleae showed a good commanded 100 ms
  `RUN` pulse and clean TX edges, and `DBG_UART_IF_EN` remained at 3.3 V. The
  second run's PPK2 trace measured 54 uA idle, 177 uA during reset, 108 uA
  during the TX burst, and 54 uA after return to idle.
  Eight consecutive sessions on 2026-09-13 completed the ten-boot profile:
  `20260913T172726Z-f5bd6a28`, `20260913T172806Z-17f9e499`,
  `20260913T172841Z-77f0338e`, `20260913T172915Z-a47bcb84`,
  `20260913T172950Z-61fe0955`, `20260913T173025Z-678e82e0`,
  `20260913T173057Z-6095a8ba`, and `20260913T173133Z-e9fd8542`. Every
  run received the exact marker, reached a 62-byte ring high-water mark,
  reported zero dropped bytes and zero overflow events, and completed in one
  uninterrupted segment. The ten-consecutive-boot acceptance criterion passes.
- Dense profile session `20260913T174455Z-b94d2252` ran a synchronized 15 s
  capture with `BURST` sent 0.5 s after capture start under normal host load.
  The fixture emitted 43,081 deterministic bytes; 8,825 were retained and five
  explicit overflow episodes reported 34,256 dropped bytes, reconciling the
  output exactly. Final high-water was 7,842 bytes, the final
  `count=2048 checksum=2096128` marker survived, loss scope was
  `debug_helper_rx_buffer`, and the one-segment session had no interruption,
  truncation, CDC failure, or false `first_error`. Diagnostic setup sessions
  and their exclusion reasons are recorded in the ring-buffer validation file.
- No-stall control session `20260913T175222Z-b278daf8` then sent the
  94,299-byte `SUSTAIN` stream without artificial backpressure. It retained
  13,188 bytes and explicitly reported 81,111 dropped across 17 episodes, with
  a 5,405-byte high-water mark and an uninterrupted epoch. This invalidated the
  earlier dense-only limitation classification and blocked the stall profiles.
  Source tracing identified the unconditional 10 ms wait after each descriptor
  drain as the cause. TDD now batches up to 32 ready outputs and continues
  immediately while backlog remains; all 96 firmware host tests pass. A
  pristine Zephyr 4.4.2/SDK 1.0.1 build uses 52,100 bytes flash and 78,032 RAM.
  The candidate UF2 SHA-256 is
  `7ac75259f7e11d4ae8b17da2fb49864994b4da6cca524d5e2881bdc3dd975814`;
  its HIL result is superseded below.
- The bounded-drain candidate passed parser-reset boot session
  `20260913T180846Z-6de3ee06`, then failed no-stall session
  `20260913T180919Z-df367ab0` with 52,541 retained plus 41,758 explicitly
  dropped bytes across 22 episodes. The exact total remained 94,299 bytes; the
  session was uninterrupted and error-free, but its 4,019-byte high-water and
  64-byte CDC TX FIFO isolated packet-boundary serialization. A new regression
  requires the FIFO to hold the 1,536-byte maximum evidence frame. The
  2,048-byte-FIFO candidate passes all 97 firmware host tests and target-builds
  at 52,100 bytes flash and 80,016 bytes RAM. Its UF2 SHA-256 is
  `a1a3459994b29686b772fbc01f2ee2ecfbd0eb943d1e7e8353fd70077b488ae5`;
  it was flashed on 2026-09-13. Parser-reset session
  `20260913T182730Z-5ecc6e50` retained the exact expected 63 bytes with zero
  loss/overflow. No-stall session `20260913T182750Z-85ac6c6f` reported zero
  firmware loss/overflow, one uninterrupted segment, no error, and only a
  160-byte ring high-water mark, but persisted just 67,336 raw bytes, 2,926 line
  feeds, and 2,925 complete sequence lines. The retained device timestamps span
  about 6.145 s, showing that the 15 s host workflow fell behind the source.
  Source tracing isolated one crash-recoverable filesystem transaction per UART
  event, including repeated raw/JSONL `fsync`, metadata replacement, and marker
  updates. Focused TDD now combines up to 64 consecutive UART events in one
  existing transaction, preserves exact per-event evidence and rollback, falls
  back to ordered single admission when the whole batch exceeds quota, and
  leaves wait-pattern capture single-event. Ruff passes, mypy reports no issues
  in 73 source files, all 1,286 tests pass, and `git diff --check` is clean.
  Repeat no-stall session `20260914T205443Z-f931321d` then retained exactly
  94,299 bytes and 4,098 lines: BEGIN, all 4,096 ordered sequence lines, and the
  exact `count=4096 checksum=8386560` END record. It completed with zero
  overflow/loss, one uninterrupted segment, no truncation or first error, and a
  131-byte maximum/final ring high-water mark. The final occupancy was zero.
  This passes the no-stall gate; the 100 ms host-backpressure profile is next.
- A controlled host-backpressure run sent `SIGSTOP` to the verified Device Core
  Service process during `SUSTAIN` and resumed it after a monotonic measured
  104.328 ms. Session `20260914T205746Z-79a5348b` retained the identical exact
  94,299-byte stream and SHA-256, all 4,096 ordered sequence lines, and the END
  checksum. It reported zero loss/overflow, one uninterrupted segment, no
  truncation or first error, a 160-byte maximum/final ring high-water mark, and
  zero final occupancy. This passes the 100 ms profile; 250 ms is next.
- The formal 250 ms profile paused the same verified service process for a
  monotonic measured 250.255 ms. Session `20260914T205958Z-ccfb482c` again
  retained the identical exact 94,299-byte stream and SHA-256, all sequence
  lines, and the END checksum. It completed with zero loss/overflow, one
  uninterrupted segment, no truncation or first error, a 160-byte maximum/final
  high-water mark, and zero final occupancy. The 250 ms acceptance criterion
  passes; 500 ms is next.
- The 500 ms profile paused the service for a monotonic measured 505.137 ms.
  Session `20260914T210144Z-282b29e0` retained the same exact 94,299-byte stream,
  all sequence lines, checksum, and SHA-256. It completed with zero
  loss/overflow, one uninterrupted segment, no truncation or first error, a
  160-byte maximum/final high-water mark, and zero final occupancy. No
  allocation, stack-overflow, watchdog, USB CDC, or session-lifecycle failure
  was observed. All required backpressure durations now pass; deliberate
  overflow is next.
- Corrected dense session `20260914T210453Z-104d1c17` deliberately overflowed
  without a host pause. It retained 15,691 bytes and reported 27,390 dropped
  bytes across eight overflow records; the exact sum is the fixture's 43,081
  bytes. The END checksum survived, proving post-loss capture continued.
  Metadata and the public session view exposed `loss_reported` with
  `debug_helper_rx_buffer`, while the session remained one uninterrupted,
  untruncated segment and Pico2 stayed connected. This passes the corrected
  dense and deliberate-overflow gates; runtime stack high-water is next.

Enhanced macOS startup and RP2350 PL011 correction working tree, reviewed 2026-09-09:

- Hardware diagnosis isolated pyserial's default open sequence: it asserted DTR
  before its final input flush, while the RP2350 firmware emits its one-shot
  epoch `hello` immediately on DTR assertion. The flush could therefore discard
  the frame before the async reader received it.
- The concrete Enhanced opener now creates the serial resource closed, holds
  DTR low while opening and flushing, attaches the resource to the asyncio
  reader, and asserts DTR exactly once afterward. Partial-open failures close
  the serial resource.
- The next hardware run reached async transport attachment and exposed a second
  issue: `serial_asyncio` reapplied the configured 460800 rate through macOS
  `IOSSIOSPEED`, which the CDC device rejected with errno 83. That value belongs
  to the firmware-owned DUT UART; the Phase 1 contract explicitly keeps it off
  the independent host USB CDC port. The host now uses portable 115200 CDC line
  coding without changing the 460800 DUT UART.
- TDD red proved the old production opener still used the unsafe
  `open_serial_connection` path. A second red proved that the DUT UART rate was
  still passed to the CDC opener. The focused Enhanced serial I/O suite now
  passes all 13 tests, including exact DTR ordering, separation of CDC line
  coding from DUT UART rate, and attachment-failure cleanup.
- Pico 2 diagnosis then isolated two firmware-side requirements. DTR must remain
  asserted for 100 ms before an epoch starts, and the CDC device publishes DCD
  and DSR readiness without clearing carrier during DTR-low gaps. This makes
  macOS port open deterministic while DTR alone continues to own epochs.
- With Zephyr's default 1,024-byte CDC TX FIFO, the firmware accepted the whole
  175-byte `hello`, disabled TX interrupts, delivered exactly two 64-byte
  packets, and wedged before the final 47 bytes. The board overlay now fixes the
  FIFO at one 64-byte full-speed packet so each completion advances the next
  chunk through the existing partial-acceptance state machine.
- The first Zephyr 4.4.0 HIL result was not stable: `hello` could arrive, but
  periodic `buffer_status` stopped and DTR-low/close blocked for about 6.5
  seconds. Controlled diagnostic images showed hello-only healthy, UART-only
  broken, UART with interrupts masked healthy, RX interrupt only healthy, and
  error interrupt only broken. This isolates the failure to the PL011 error
  interrupt path rather than CDC, protocol, telemetry, or UART RX.
- Zephyr advisory
  [GHSA-36rp-2hcp-f5hv](https://github.com/zephyrproject-rtos/zephyr/security/advisories/GHSA-36rp-2hcp-f5hv)
  confirms releases before 4.4.2 enable PL011 error interrupts without
  acknowledging them in the ISR. The application now rejects Zephyr before
  4.4.2 at configure time and keeps UART error interrupts enabled.
- The full production build with Zephyr 4.4.2/SDK 1.0.1 confirms
  `tx-fifo-size = <0x40>`: 51,772 bytes flash, 75,944 bytes RAM, and a
  103,936-byte UF2 with SHA-256
  `db5ba9dfcbcc6d6bbfd83149dd9d5c1b8f206478ad2d7d6ef68f18b57dc16afe`.
- Patched Pico 2 HIL delivered the complete valid 175-byte `hello`, then six
  complete 172-byte periodic `buffer_status` frames over 6.5 seconds. DTR-low
  and close completed immediately. A fresh epoch again delivered `hello` and
  status before closing normally.
- The exact CLI sequence `start`, `status`, `stop`, immediate `start`, `status`,
  `stop` passed twice against `/dev/cu.usbmodem11401`. Both status checks
  reported `connected`, device `dutchmate-rp2350`, firmware `development`, and
  all five required capabilities.
- Retain the independently validated USB/host corrections alongside the Zephyr
  4.4.2 minimum: portable 115200 CDC line coding, deterministic DTR
  open/flush/attach/close sequencing, the DTR-low restart dwell, and the
  one-packet CDC TX FIFO each addressed a separate observed failure. Do not
  blanket-revert them as part of the PL011 correction. The firmware's 100 ms
  DTR-high qualification and DCD/DSR publication are optional future cleanup
  candidates only; remove either one only after an isolated Zephyr 4.4.2 A/B
  run passes sustained telemetry and consecutive CLI start/status/stop cycles.
- All 91 portable firmware tests and all 14 focused Enhanced serial I/O tests
  passed. Ruff passed; mypy reported no issues in 73 source files; full pytest
  passed with 1,274 tests; and `git diff --check` found no whitespace errors.

RP2350 firmware test/build audit commit
`1409522dcdbc69b5b4e16be2576b2869bccbef21`, reviewed 2026-09-05:

- The audit maps every portable boundary to host-compiled tests: exact protocol
  identity/output, NDJSON framing and command validation, the RX ring and loss
  telemetry, CTRL/UART command state machines, epoch cancellation, and exact
  CDC FIFO-acceptance semantics. No uncovered hardware-independent behavior was
  found, so no artificial source-text tests or production behavior were added.
- The firmware README now gives a reproducible build command from the pinned
  Zephyr west workspace and one focused command for all portable firmware
  tests. It explicitly separates host tests, target-build evidence, and HIL
  claims.
- EVENT0 through EVENT3 remain input-only and reserved. The EVENT translator
  remains disabled; neither capture behavior nor `gpio_events` was added.
- Zephyr 4.4.0 with SDK 1.0.1 built warning-free for
  `rpi_pico2/rp2350a/m33`: 51,476 bytes flash, 76,904 bytes RAM, and a
  103,424-byte UF2 image.
- All 90 portable firmware tests passed. Ruff passed; mypy reported no issues
  in 73 source files; full pytest passed with 1,269 tests; and
  `git diff --check` found no whitespace errors.
- Graphify was queried for the firmware/build/test boundary. No structural
  graph update was required because this audit changed documentation only.

RP2350 complete CDC write implementation commit
`cf5325b5b3c8b132c2a07bb02a087b8c18ccfd0b`, reviewed 2026-09-05:

- TDD red first failed six scenarios because the CDC TX state module was absent;
  a second red failed seven scenarios when bounded no-progress timing was added.
  Green covers exact 1..1,536-byte bounds, owned frame copying, busy rejection,
  partial FIFO progress, exact-once completion, invalid progress, driver faults,
  timer wrap, cancellation, and no replay of a staged suffix.
- One Zephyr CDC callback is the only context that calls `uart_fifo_fill`; the
  main USB TX owner starts, polls, and cancels frames. Hello, responses, UART
  events, overflow records, and status records all use the same adapter.
- The approved ownership description now records the Zephyr constraint: the
  main USB TX thread remains sole output scheduler/frame owner, while the CDC
  workqueue callback may advance only its already armed immutable frame.
- Responses and status snapshots are acknowledged only after the complete frame
  reaches the CDC driver FIFO. A 250 ms no-progress deadline resets after every
  accepted chunk. DTR loss cancels pending output and ends the active epoch;
  invalid progress or a driver fault ends it as a fatal transport failure.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 51,476 bytes flash, 76,904 bytes RAM, and a
  103,424-byte UF2 image.
- Focused CDC TX gate: 7 tests passed; all 90 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,269 passed with zero failures.
- Graphify updated the structural graph to 4,563 nodes and 12,157 edges. Its
  parser still reports the existing macro-heavy Zephyr fixture header as a
  partial syntax extraction; target compilation remains authoritative there.
- `git diff --check`: passed with no whitespace errors.
- USB FIFO timing, driver-buffer behavior across physical reset, reconnect
  behavior, command load, and electrical behavior remain HIL gates because the
  Revision A prototype is unavailable.

RP2350 live CDC command integration commit
`a8ac38362144fbd05fdbb69be515371ad07166e7`, reviewed 2026-09-05:

- TDD red failed six ingress scenarios because the bounded ingress module was
  absent and failed executor rejection routing because that API was absent.
  Green covers fragmented and batched input, exact consumed-byte ownership,
  malformed/schema-invalid/oversized mapping, resynchronization, and epoch
  reset. Exact invalid-command and invalid-argument responses use the existing
  one-response lane.
- A dedicated CDC RX thread drains at most 128 bytes per bounded staging chunk
  and stops reading when the single static command slot is full. A separate,
  higher-priority command/control thread is the sole executor, CTRL, pulse, and
  UART TX owner. The lower-priority main thread remains the sole CDC writer.
- `hello` is written before command ingress starts. Responses take the response
  lane before the next evidence frame; existing internal observation sequences
  continue to order UART, overflow, and status evidence.
- Epoch end waits for RX and command owners to stop, resets partial framing,
  purges the command slot, cancels executor work, discards unsent responses and
  CTRL mappings, and forces the hardware safe state. Internal runtime faults end
  the epoch instead of accepting more work.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 50,444 bytes flash, 75,312 bytes RAM, and a
  101,376-byte UF2 image.
- Focused ingress/executor gate: 14 tests passed.
- All 83 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,262 passed with zero failures.
- Graphify updated the structural graph to 4,522 nodes and 12,052 edges. Its
  parser still reports the existing macro-heavy Zephyr fixture header as a
  partial syntax extraction; target compilation remains authoritative there.
- `git diff --check`: passed with no whitespace errors.
- Complete CDC-driver frame acceptance, reconnect timing, command load,
  CTRL/UART electrical behavior, and stack margins remain HIL gates because the
  Revision A prototype is unavailable.

RP2350 command executor implementation commit
`97f5c0b13480c128bf8d839995efe760e37be68a`, reviewed 2026-09-05:

- TDD red failed all seven scenarios because the command executor was absent.
  Green covers exact control success/error responses, one owned response lane,
  wrap-safe pulse completion, UART partial-write and physical-completion
  semantics, timeout/fault terminalization, and epoch cancellation.
- Configure and set-state acknowledge at the operation timestamp. Pulse
  acknowledges only after idle restoration; UART send acknowledges only after
  physical completion and reports the exact accepted byte count.
- Pending work and staged responses reject another command. Epoch cancellation
  cancels UART TX without retry, discards any response, restores all CTRL
  channels to high impedance, and forgets accepted CTRL mappings.
- Error mapping is exact for invalid commands/arguments, unconfigured CTRL
  channels, CTRL hardware faults, UART faults, and UART timeouts. Live CDC
  framing and shared evidence/response scheduling remain the next slice.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,580 bytes flash, 63,912 bytes RAM, and an
  87,552-byte UF2 image.
- Focused executor gate: 7 tests passed.
- All 76 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,255 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC command throughput, response/evidence ordering, disconnect behavior, and
  CTRL/UART electrical behavior remain HIL gates because the Revision A
  prototype is unavailable.

RP2350 UART TX implementation commit
`197d9b56a04ee1fccffa9dd5b2d0c55cc8f506b7`, reviewed 2026-09-05:

- TDD red failed all seven scenarios because the portable TX state machine was
  absent. Green covers null/zero/1,024/1,025-byte bounds, owned payload copying,
  busy rejection, partial FIFO progress, physical completion, and one exact
  `bytes_accepted` result.
- Zero, negative, and over-reported FIFO progress plus completion-check and
  mid-transmission driver faults terminate as `hardware_fault`. Later callbacks
  cannot retry or complete a terminal transmission.
- Timeout uses unsigned 64-bit elapsed time across timer wrap. A timed-out or
  epoch-cancelled partial transmission stops without retry and cannot report
  success.
- The RP2350 adapter uses the existing UART0 interrupt callback and a spinlock
  around portable state. A Zephyr work item contains the PL011 driver's
  synchronous initial TX kick so the future command/control caller can poll the
  100 ms internal deadline and preempt it on disconnect or fault.
- UART RX stop now cancels TX before disabling the bidirectional translator;
  UART driver faults terminate both directions. CDC commands still cannot start
  TX until the command executor and ordered response lane exist. EVENT pins
  remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,580 bytes flash, 63,912 bytes RAM, and an
  87,552-byte UF2 image.
- Focused TX/decoder gate: 14 tests passed.
- All 69 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,248 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real partial writes, physical-drain completion, timeout, disconnect, and UART
  signal integrity remain HIL gates because the prototype is unavailable.


RP2350 generic control implementation commit
`81491bb222a05f0b90fae0e1e0849b38dab6f305`, reviewed 2026-09-04:

- TDD red failed all seven initial scenarios because the portable control module
  was absent. Green coverage now exercises accepted open-drain and push-pull
  mappings, active/idle application, invalid and failed reconfiguration,
  unconfigured actions, and all four physical channels.
- Pulse coverage proves active drive, exact 1..10000 ms bounds, deadline restore,
  64-bit timer wrap, cancellation without late completion, and no successful
  completion when idle restoration faults.
- Every transition disables output before changing data and enables only a
  requested driven state. Enable failure performs a best-effort disable;
  channel faults retain accepted configuration for retry, while epoch end
  cancels the pulse, drives every channel high impedance, and discards mappings.
- The Revision A adapter binds the portable enable/data port to fixed
  `CTRL0`–`CTRL3` GPIO arrays. The target compiles it, but command execution does
  not instantiate the control owner yet. EVENT pins remain input-only and the
  EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. Linker allocation is unchanged before command-path
  integration.
- Focused control/decoder gate: 16 tests passed.
- All 62 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,241 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CTRL electrical sequencing and disconnect/fault behavior remain HIL gates
  because the Revision A prototype is unavailable in this workspace.

RP2350 typed command protocol implementation commit
`f6fbae41150783ef4206ec7288a5d969fb801f58`, reviewed 2026-09-04:

- TDD red first proved response encoding absent, then green covered exact plain,
  timestamped, UART-acceptance, and error frames plus limits, JSON escaping,
  UTF-8 validity, and Unicode control rejection. A focused red-green regression
  closed invalid multibyte continuation acceptance.
- A second TDD red proved command decoding absent. Green validates all
  four committed command types independent of field order, including escaped
  ASCII values, `CTRL0`–`CTRL3`, open-drain/push-pull electrical invariants,
  1..10000 ms pulses, active/idle states, and 1..1024 decoded UART bytes.
- Invalid/missing/unknown commands and malformed objects classify as
  `invalid_command`; missing, extra, duplicate, wrong-type, out-of-range, and
  invalid-base64 fields classify as `invalid_argument`. Failed decoding clears
  the typed output, so it cannot carry partial state into a hardware action.
- Systematic debugging isolated one wrong-type `data_b64` classification to a
  missing value-token check; the narrow fix preserves malformed-string
  classification and the focused decoder/response gate passes.
- The modules are target-compiled but CDC RX remains disconnected until command
  execution and ordered response routing exist. EVENT pins remain input-only
  and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. No decoder/response instance is allocated yet.
- All 53 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,232 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC command execution, response ordering, disconnect cancellation, and
  recovery remain HIL gates because the Revision A prototype is unavailable in
  this workspace.

RP2350 bounded host-command framing implementation commit
`c3ce6aa58d26f3531c4b735261ec8ecf4e87dcdf`, reviewed 2026-09-04:

- TDD red failed in all seven scenarios because the framer was absent. Green
  covers fragmented frames, multiple frames in one input chunk, CRLF handling,
  exact 2,048/2,049-byte boundaries, discard-through-LF resynchronization,
  disconnect reset, and invalid arguments.
- The framer retains at most 2,047 bytes and reports consumed input so its
  caller can hand off exactly one completed frame or oversize result at a time.
- The implementation is target-compiled but CDC RX remains disconnected until
  the command decoder and response path exist; complete commands therefore
  cannot yet be consumed without their required ordered response.
- EVENT pins remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. No framer instance is allocated until CDC integration.
- All 40 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,219 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC input, frame handoff, disconnect reset, and error recovery remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 buffer telemetry implementation commit
`1bf616c5ac1b28096b2a1ceefc214793f988af89`, reviewed 2026-09-04:

- TDD red gates first proved both telemetry encoders and the periodic scheduler
  were absent, then proved status snapshots lacked ring observation ordering
  and atomic overflow staging.
- Green coverage verifies exact canonical `buffer_overflow` and `buffer_status`
  frames, full-width counters, invalid invariants and capacities, one-second
  scheduling, newest-pending coalescing, and UART/overflow/status ordering.
- Status snapshots receive their sequence inside the ring spinlock. Selecting
  and removing the next UART or overflow observation also happens atomically
  against the pending-status sequence; encoding and CDC writes remain outside
  the lock.
- DTR loss clears the pending status snapshot with the rest of the connection
  epoch. EVENT pins remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image.
- All 33 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,212 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real CDC throughput, telemetry cadence, overflow ordering, and reconnect
  behavior remain HIL gates because the Revision A prototype is unavailable in
  this workspace.

RP2350 ordered UART event output commit
`aadefb0e279242a606bc405388b28019cec6322d`, reviewed 2026-09-03:

- TDD red gate failed in eight UART-event scenarios because the encoder was
  absent; green covers canonical output, binary data, base64 padding, maximum
  1,024-byte staging, 64-bit timestamps, channel bounds, and invalid sizes.
- A second ring TDD red gate proved observation ordering was absent, then green
  added internal 64-bit sequences and prevents a consumer from taking UART data
  ahead of an earlier overflow episode.
- The sole CDC writer emits one bounded UART event per scheduling pass. A
  pending overflow intentionally pauses later UART output until the next slice
  adds loss telemetry, avoiding evidence reordering.
- The 512 descriptors are now 24 bytes each (12 KiB) because they retain the
  internal observation sequence; this remains within the committed 8-16 KiB
  metadata budget and still requires HIL acceptance.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 41,484 bytes flash, 62,824 bytes RAM, and an
  83,456-byte UF2 image. RAM includes the 1,024-byte UART staging buffer,
  1,536-byte encoded-frame buffer, and expanded descriptor metadata.
- All 26 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,205 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real CDC throughput, overflow ordering, and reconnect behavior remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 UART RX and hardware timestamp adapter commit
`6129759b1652bc703b6c3baeeacb9ee17002ee0b`, reviewed 2026-09-03:

- Straightforward Zephyr peripheral initialization was target-build verified;
  no artificial TDD test was added, matching the approved test boundary.
- Generated devicetree selects UART0 GP0 TX/GP1 RX at 460800 baud. Source fixes
  8 data bits, no parity, one stop bit, and no flow control.
- ELF symbols confirm the 64-bit RP2350 `time_us_64` path and allocated RX ring
  are linked. Each IRQ callback samples once before draining its FIFO.
- The DTR lifecycle sends `hello` before enabling UART RX/translator. DTR loss
  and UART driver faults disable RX and return UART/CTRL/EVENT enables to safe
  state; EVENT pins remain input-only with no capture path.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 40,612 bytes flash, 56,152 bytes RAM, and an
  81,408-byte UF2 image. RAM now includes the allocated 32 KiB byte ring and
  8 KiB descriptor ring.
- All 18 portable firmware tests passed unchanged.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,197 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real UART capture, timestamp, overflow, and disconnect behavior remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 portable UART RX ring commit
`285323983e1c4a35e6248c5c90bbe98553f73956`, reviewed 2026-09-03:

- TDD red gate failed in all seven scenarios because the ring implementation
  was absent.
- Focused green gate covers initialization, FIFO wrap, bounded descriptor
  staging, callback timestamp preservation across split drains, byte-space and
  descriptor-space drop-oldest behavior, oversized callback handling,
  overflow-episode coalescing, and disconnect discard with boot-cumulative
  counters preserved.
- The descriptor ring is fixed at 512 16-byte metadata entries (8 KiB); this
  remains subject to the committed RAM and HIL acceptance gates.
- All 18 portable firmware tests passed after integration with the prior hello
  and connection-epoch suites.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 39,212 bytes flash, 15,120 bytes RAM, and a
  78,848-byte UF2 image. The ring source is target-compiled but its storage is
  not allocated until the hardware UART adapter owns an instance next slice.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,197 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Hardware UART integration and ring load HIL were not run in this portable
  logic slice.

RP2350 USB identity and connection-epoch hello commit
`6bbee39b37ed35d41fa4d3b01372303038dcfb46`, reviewed 2026-09-03:

- TDD red gates failed as expected: eight hello tests first lacked the encoder,
  then three connection-epoch tests lacked the state machine.
- Focused green gate passed all 11 portable firmware tests, including the exact
  five-capability v1 hello, firmware-version bounds, and DTR edge semantics.
- Zephyr 4.4.0 with SDK 1.0.1 built warning-free for
  `rpi_pico2/rp2350a/m33`: 39,212 bytes flash, 15,120 bytes RAM, and a
  78,848-byte UF2 image.
- A production build retaining development VID/PID `2E8A:000A` failed at the
  intended compile-time guard. A validation build using replacement VID/PID
  `1234:5678` passed; these are test values, not assigned production identity.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,190 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- USB enumeration and DTR reconnect HIL were not run because the Revision A
  prototype is not available in this workspace.

RP2350 application and safe-I/O scaffold commit
`dcf8d8d94fd961055e236a3cb09941b9f7322ff6`, reviewed 2026-09-03:

- Zephyr 4.4.0 with SDK 1.0.1 cross-built the application for
  `rpi_pico2/rp2350a/m33` and generated a 27,648-byte UF2 image.
- Generated devicetree evidence preserves the exact Revision A UART enable,
  CTRL0–CTRL3 enable/data, EVENT enable, and EVENT0–EVENT3 GPIO ordering.
- Source inspection confirms EVENT channels have no interrupt registration or
  event-capture path; their translator remains disabled.
- No TDD test was manufactured for this straightforward peripheral-
  initialization slice, matching the approved firmware test boundary.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,179 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Physical startup voltage and translator-state HIL checks were not run because
  the Revision A prototype is not available in this workspace.

RP2350 identity and timestamp-provenance migration commit
`c8a9aba8278283421df79b8033f27b58aa44dd44`, reviewed 2026-09-03:

- TDD red gate failed in the expected two places because Enhanced segment
  normalization still emitted `rp2040_timer` and the canonical hello still
  identified `dutchmate-rp2040`.
- Focused green gate passed: 807 backend, protocol, session, runtime, service,
  and CLI tests. An explicit compatibility test proves legacy
  `dutchmate-rp2040` / `rp2040_timer` evidence remains readable.
- Active source/fixture search found RP2040 names only in the deliberate legacy
  timestamp type/reader support and its compatibility test.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,179 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

RP2350 capability-contract alignment commit
`816055db8990aeee07fc07b740aeaf0a8435320f`, reviewed 2026-09-03:

- TDD red gate failed in the expected five places because the schema and host
  parser rejected `device_timestamp` / `overflow_telemetry`, while the canonical
  hello omitted them; green gate passed all 109 focused protocol tests.
- Broader protocol/Enhanced gate passed: 299 tests.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,177 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

Previous RP2350 firmware architecture documentation commit
`31e9d4a50f6fa9aee012f23bb51dffaf469d7a47`, reviewed 2026-09-02:

- Architecture self-review found no placeholders, RP2040 target leakage, or
  unresolved scope contradiction. The known capability mismatch is explicit
  and assigned to the first implementation slice.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,173 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

Previous sync-path removal validation based on implementation commit
`11e5bd24d665a8f113884acfc5f6cd509ba82909`, reviewed 2026-09-01:

- Focused removal gate passed: 195 tests across Enhanced adapter,
  serial-frame writing, reconnect/startup, runtime, GPIO configuration, and
  device-action workflow coverage.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,173 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Exact stale-reference search found no remaining synchronous Enhanced adapter,
  transport, hello, startup, or reconnect compatibility symbols outside
  historical design/implementation records.
- The dependency-direction search for `apps` or `dutchmate_service` imports in
  `core/src` returned no matches.
- Graphify code update completed with 4,078 nodes, 11,006 edges, and 191
  communities. Its parser reported the existing Zephyr fixture header as a
  partial-extraction warning; source compilation/tests remain authoritative.

## Completed Queue — Delivery Infrastructure

The owner activated this milestone on 2026-09-22. It does not wait for the
deferred Phase 1 hardware queue.
`docs/ci_packaging_distribution_plan.md` defines the approved design and
acceptance contracts; this section alone tracks its progress.

- [x] Establish the always-running host CI workflow, extend the existing
  architecture and protocol contract tests, and normalize Python 3.10 asyncio
  timeout behavior.
- [x] Add the `dutchmate` aggregator, synchronized host-version validation, and
  the atomic console-script ownership migration.
- [x] Add clean-wheel and isolated `uv tool install` acceptance, including the
  direct-Python optional Debug Agent path and installed MCP discovery.
- [x] Add independent Debug Helper firmware version authority, compile CI, and
  provenance artifacts for all three firmware configurations.
- [x] Confirm all three firmware configurations on the GitHub-hosted runner
  after the job-container disk-capacity and SDK size-tool corrections.
- [x] Add and validate the repo-local portable coding-agent plugin against the
  installed MCP surface.
- [x] Record owner approval of the mixed-license policy and Nahit Pawar as the
  public publisher; add artifact license contracts, DCO repository guidance,
  and the separately gated release workflow.
- [x] Limit the `v0.1.0` public artifact set to five distributions while
  retaining clean installed-artifact coverage for all six workspace packages.
- [x] Configure protected `testpypi` and `pypi` GitHub environments.
- [x] Revise the first-publication workflow for PyPI's monorepo pending-publisher
  constraint: one OIDC job per project, one pending registration at a time,
  aggregate TestPyPI verification before production, and no artifact rebuilds.
- [x] Install and require the DCO status check.
- [x] Sequentially register and convert the five TestPyPI Trusted Publishers,
  beginning with `dutchmate-core`.
- [x] Validate the immutable accepted host artifacts through TestPyPI.
- [x] Sequentially register and convert the five production Trusted Publishers,
  then publish and digest-verify those same artifacts in dependency order.
- [x] Publish the GitHub Release from the existing `v0.1.0` tag using the
  prepared release body without rebuilding or replacing Python artifacts.

Exit gate passed: the plan's host CI, packaging, firmware-build, plugin, gated
release, TestPyPI, production PyPI, and GitHub Release contracts have evidence.
HIL and public firmware binary release remain explicitly separate.

## Completed Phase 4 Evidence-Packaging Work

- [x] Map the bounded evidence-package contract and existing deterministic
  evidence sources before selecting the first implementation slice.
- [x] Define focused acceptance tests for that slice using
  `docs/debug_agent_context_contract.md`; keep provider-specific work behind
  the documented boundary.
- [x] Add a separate Debug Agent workspace package and project native session
  facts through validated `SessionStore` retrieval; reject unsupported schemas
  without reading or inferring raw evidence.
- [x] Assemble bounded UART and hardware-event excerpts with contract limits,
  priority rules, and explicit truncation/omission metadata.
- [x] Attach a baseline comparison summary only for a valid designated project
  baseline; preserve its session ID and timing-comparability state.
- [x] Validate an optional Coding Agent context package and assemble a bounded
  versioned analysis request without invoking a provider.
- [x] Validate the common report shape, then add a disabled-by-default
  provider adapter boundary with explicit opt-in and submission manifest.
- [x] Add a local Ollama adapter and host-facing digest-reviewed manifest/report
  flow without expanding Device Core permissions or persisting credentials.
- [x] Run live local-model preview/analyze acceptance on a completed native
  session and review the report against its selected evidence.
- [x] Validate the Debug Agent CLI from the installed VS Code coding-agent host.
## Completed Queue — Phase 2

Work follows the independently testable sequence in
`docs/mcp_integration_plan.md`.

- [x] Lock the official MCP SDK 2.x protocol/dependency baseline and record
  `2026-07-28` as normative.
- [x] Compose one stateless stdio-only `MCPServer` with fixed identity and
  private finite cache hints.
- [x] Register the nine Phase 2 tools in documented order and project complete
  structured success and actionable validation/service error results.
- [x] Add modern SDK v2 integration tests for `server/discover`, required
  per-request metadata, deterministic cacheable tool listing, calls,
  cancellation, and clean EOF shutdown. Retain one compatibility smoke test
  only for the SDK-owned legacy path.
- [x] Wire `dutchmate mcp` with `--service-url`,
  `DUTCHMATE_SERVICE_URL`, stderr-only logging, and no additional transport.
- [x] Document named VS Code and Claude Code stdio registrations and verify
  absolute-path launch with the official Inspector CLI.
- [x] Run the official `2026-07-28` conformance requirement set against the
  temporary HTTP projection and fix the discovered capability mismatch.
- [x] Establish scoped tools-only stdio acceptance for the official runner's
  HTTP/fixture-only cases, pass the direct-process and applicable official
  checks, and record named host UI validation as follow-up when available.
- [x] Complete one read-only MCP tool call through the installed stdio launcher
  to a running Device Core Service; stop the temporary service afterward.

Exit gate: the MCP integration plan's protocol, packaging, error, launch, and
host-acceptance requirements all have fresh automated or conformance evidence.

## Already Complete — Do Not Reimplement

The following items are no longer backlog work:

- backend-neutral events, capabilities, timestamp provenance, and integrity;
- Basic raw UART receive and policy-gated complete UART send;
- shared capture, boot-test, literal wait-pattern, and UART-send workflows;
- native session lifecycle, bounded evidence, recovery, and reconnect segments;
- session list/detail, recent logs, stable pagination, and legacy read-only views;
- count-based retention with active and baseline protection;
- project baseline mark/replace/clear and bounded comparison;
- finite-workflow reconnect coordination and live reconnect status;
- deterministic line processing, pattern detection, and `first_error`;
- explicit public `device_timestamp_us` action fields plus accepted reset pulse,
  boot mode, and RFC 3339 action completion reporting;
- nullable commanded boot state with accepted-mapping initialization,
  certainty-aware invalidation, status/CLI reporting, and session snapshots.
- normalized boot-test reset evidence, including accepted pulse duration,
  segment timestamp provenance, atomic quota admission, and crash rollback.
- native-v1 evidence and log replay using `segment_id` as the sole timestamp
  epoch selector while retaining the recognized unversioned legacy shape.
- bounded structured `invalid_argument` context for GPIO `role` and
  `dut_signal` identifier type, length, whitespace, and control errors.
- typed `not_configured` context with originating operation, required role,
  and exact unconfigured or rejected role state.
- typed Enhanced backend-input classification with operation/backend context
  and bounded frame sizes kept out of session metadata.
- continuous idle connection-state and Enhanced integrity projection through the
  existing status contract.
- coordinated idle and active reconnect for Basic and Enhanced, with production
  Enhanced startup and replacement retained on one async host, capability-
  compatible publication, and retained rejected-candidate cleanup failures.
- removal of the obsolete synchronous Enhanced command/source, hello, startup,
  and reconnect compatibility path.

[Return to current Development Status](development_status.md).
