# CI, Packaging, Release, Firmware, and Plugin Distribution Plan

**Status:** Approved design; implementation progress is tracked only in
`docs/development_status.md`.

## Purpose

Add repeatable CI, installable Python distributions, independently versioned
firmware artifacts, gated public releases, and local coding-agent integration
without changing DUTchMate's Device Core, backend, protocol, or hardware-control
boundaries.

The delivery-infrastructure milestone can proceed independently of the
remaining Phase 4 source-area quality review and deferred Phase 1 hardware
work. Normal pull-request CI remains independent of physical hardware.

## Architectural Invariants

- Every console executable has exactly one authoritative owning distribution.
- All DUTchMate host distributions in one release use one synchronized version.
- Debug Helper firmware has an independent Semantic Version and release
  lifecycle.
- Enhanced protocol version, firmware version, host version, hardware revision,
  and build identity are separate concepts.
- Host/Debug-Helper interoperability is governed primarily by protocol version
  and capabilities, not matching product versions.
- Clean-wheel artifacts are the release candidates, and publishing uses exactly
  the artifacts that passed acceptance.
- MCP remains the common coding-agent boundary. Plugins contain registration and
  workflow guidance, not Device Core or hardware-control implementations.
- `docs/development_status.md` remains the only progress tracker and owner of the
  current next step.

## Python Distribution Model

### Current distribution graph

The repository currently builds five component distributions:

```text
dutchmate-core
├── dutchmate-cli
├── dutchmate-service
├── dutchmate-mcp-server
└── dutchmate-debug-agent
```

Add a sixth workspace distribution, `dutchmate`, under `packages/dutchmate`.
It is the normal user installation target and, for `v0.1.0`, depends on:

```text
dutchmate
├── dutchmate-cli
├── dutchmate-service
└── dutchmate-mcp-server
```

Keep the existing distribution name `dutchmate-mcp-server`; `dutchmate-mcp` is
the executable name, not a package rename.

All first-party runtime dependencies use exact same-release constraints. The
aggregator does not duplicate application or hardware-control logic.

### Executable ownership

Move normal-user executable ownership to the aggregator:

| Executable | Current owner | Authoritative owner |
|---|---|---|
| `dutchmate` | `dutchmate-cli` | `dutchmate` |
| `dm` | `dutchmate-cli` | `dutchmate` |
| `dutchmate-service` | `dutchmate-service` | `dutchmate` |
| `dutchmate-mcp` | `dutchmate-mcp-server` | `dutchmate` |
| `dutchmate-debug` | `dutchmate-debug-agent` | `dutchmate-debug-agent` |

The aggregator's scripts call the existing component entry functions. Remove
the competing script declarations from the CLI, service, and MCP component
distributions only after the migration inventory and workspace acceptance below
are in place.

The supported installation interface is:

```text
uv tool install dutchmate
pipx install dutchmate
```

It exposes:

```text
dutchmate
dm
dutchmate-service
dutchmate-mcp
```

Component packages remain importable implementation dependencies. Installing a
component package directly is not the normal user interface.

### Deferred Debug Agent Distribution

`dutchmate-debug-agent` remains an independently testable workspace package for
`v0.1.0`. It retains its direct component-development command:

```text
uv run --package dutchmate-debug-agent dutchmate-debug ...
```

The public `v0.1.0` aggregator does not declare a `debug-agent` extra or expose
`dutchmate debug`, and the release artifact set excludes the Debug Agent wheel
and source distribution. Normal CI still builds, installs, and tests the sixth
workspace distribution so deferral does not allow it to decay.

The first public Debug Agent release is planned for the coordinated `v0.2.0`
host release. That slice must confirm its coding-agent access model and public
command surface before adding any aggregator extra or launcher. If
`dutchmate debug` is introduced, it must invoke the installed Debug Agent's
Python API directly rather than locating the dependency-owned executable on
`PATH`, because `uv tool install` does not expose dependency executables by
default.

The `v0.2.0` acceptance slice must also preserve import failures raised inside
the installed Debug Agent rather than converting them into misleading
missing-feature errors.

### Console-script migration gate

Before transferring executable ownership, inventory every repository assumption
about the affected commands. Classify each occurrence as:

- a runtime subprocess or process-replacement path;
- a unit, integration, or installed-process test;
- a developer command or helper script;
- current user or architecture documentation;
- historical validation evidence that should remain unchanged.

The known migration surface includes the CLI service lifecycle launcher, the
MCP process-replacement launcher, their tests, the installed MCP integration
test, developer-guide workspace commands, and architecture text describing
component-owned executables.

Transfer the metadata ownership and update active consumers atomically. Do not
commit an intermediate state in which two distributions own the same command.
Historical evidence in `development_status.md` may continue to describe the
ownership that applied when the evidence was recorded.

The normal workspace development interface becomes:

```text
uv run --package dutchmate dutchmate --help
uv run --package dutchmate dutchmate-service --help
uv run --package dutchmate dutchmate-mcp --help
uv run --package dutchmate-debug-agent dutchmate-debug --help
```

Component entry functions remain directly testable as Python APIs.

## Version Authorities and Release Identities

### Host software

Use the non-published root `dutchmate-workspace` version as the logical host
version authority. Keep versions declared in the six workspace
`pyproject.toml` files and validate them against the root rather than adding
dynamic-version machinery.

The workspace version is initially synchronized at `0.1.0` for:

- `dutchmate`;
- `dutchmate-core`;
- `dutchmate-cli`;
- `dutchmate-service`;
- `dutchmate-mcp-server`;
- `dutchmate-debug-agent`.

The public `v0.1.0` release contains the first five distributions only. The
Debug Agent's first public release is planned for the coordinated `v0.2.0`
release; its workspace `0.1.0` artifacts are private CI inputs, not published
packages.

CI fails if any distribution version differs or an internal dependency lacks
the exact synchronized constraint. Future release tooling updates the root and
all six package declarations atomically.

Host release tags use:

```text
vX.Y.Z
```

### Debug Helper firmware

Add a firmware-owned `PRODUCT_VERSION` file to the RP2350 Debug Helper project,
initially `0.1.0`. It is authoritative for the firmware product version and is
not derived from the host version.

Release-grade builds pass it into `CONFIG_DUTCHMATE_FIRMWARE_VERSION`. The
existing hello `firmware` field continues to report the firmware product
version; no protocol extension is required. Diagnostic builds may add valid
Semantic Version build metadata, but the Git commit remains a separate build
identity.

Firmware release tags use:

```text
debug-helper-vX.Y.Z
```

The existing requirement that an interrupted session resume only with the same
firmware identity remains a continuity safeguard, not a general host/firmware
version compatibility rule.

### Protocol, hardware, and build identity

Record these dimensions independently:

| Dimension | Authority |
|---|---|
| Host product version | Root workspace version plus synchronized package validation |
| Debug Helper firmware version | Debug Helper `PRODUCT_VERSION` |
| Enhanced protocol version | Existing v1 schemas and host/firmware protocol contracts |
| Hardware revision | Existing revision specification and selected target configuration |
| Build identity | Full Git commit SHA and deterministic CI metadata |

Firmware may release multiple versions while retaining Enhanced protocol v1.
Protocol v2 is introduced only for an incompatible wire-contract evolution.
Known firmware limitations may produce narrow compatibility checks, but those
checks do not replace protocol and capability negotiation.

## Host CI

Create one always-running `.github/workflows/ci.yml` with four jobs:

1. `quality`;
2. `python-tests`;
3. `contracts`;
4. `package-build`.

Trigger it for pull requests, pushes to `main`, and manual dispatch. Use minimum
`contents: read` permissions and commit-pinned checkout, Python, and
`astral-sh/setup-uv` actions with caching.

Use:

```text
uv sync --locked --all-packages --dev
```

The initial gate includes:

- lock verification;
- `git diff --check`;
- Ruff checks;
- strict mypy;
- full pytest;
- architecture contracts;
- protocol schema/example contracts;
- package-version, dependency, and entry-point contracts;
- package builds and installed-artifact smoke tests.

Run the full suite on Ubuntu with Python 3.10 through 3.14. Run latest-Python
clean-artifact and process smoke tests on macOS. Do not add pytest markers: the
default suite is CI-safe, and `tests/hardware` contains host-compiled tests rather
than live HIL.

Do not initially require Ruff formatting, coverage thresholds, SBOMs,
attestations, public plugin-directory submission, or physical hardware.

Extend the existing architecture dependency test to cover the Debug Agent; do
not create a duplicate dependency checker. Extend the existing protocol schema
tests to enumerate every checked-in example.

## Clean-Artifact Acceptance

Build all six workspace distributions once with:

```text
uv build --all-packages --no-sources
```

The acceptance runner must operate outside the checkout with repository paths
and `PYTHONPATH` removed. Third-party dependencies may come from the configured
index, but all first-party DUTchMate packages must resolve from the newly built
artifact directory.

Validate the following sequence in normal CI:

1. Inspect every wheel's metadata and console entry points.
2. Reject duplicate console-script ownership across distributions.
3. Assert the exact ownership table defined above.
4. Install the base aggregator into a clean environment.
5. Run `--help` for the four public executables.
6. Verify service subprocess resolution and MCP process replacement.
7. Verify the aggregator rejects the absent `debug` command.
8. Install the standalone Debug Agent wheel from the same workspace artifact
   set and invoke `dutchmate-debug --help`.
9. Start the installed MCP server, initialize it, list the nine expected tools
   in deterministic order, and verify clean EOF.

For `v0.1.0`, copy only the five public wheel/source-distribution pairs into a
separate release directory, rerun metadata, command, and MCP acceptance against
that exact directory, and retain only those accepted artifacts for publishing.

Also run an actual isolated `uv tool install` smoke test with temporary
`UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` values. This verifies the published user
workflow rather than assuming ordinary virtual-environment behavior matches uv
tool exposure rules.

The package slice is complete only when both the installed-wheel workflow and
the normal `uv` workspace development workflow pass.

## Firmware CI and Provenance

Create `.github/workflows/firmware.yml` independently from host CI. Use
`ghcr.io/zephyrproject-rtos/ci:v0.29.4` pinned by digest; the image contains the
accepted Zephyr SDK 1.0.1.

Build:

- the RP2350 Debug Helper from a Zephyr 4.4.2 west workspace;
- the Pico fixture default 115200 configuration from Zephyr 4.4.0;
- the Pico fixture opt-in 460800 configuration from Zephyr 4.4.0.

Upload ELF, map, UF2, size output, and a machine-readable provenance manifest.
For the Debug Helper, record firmware version, Enhanced protocol version,
hardware revision, target/configuration, full commit SHA, Zephyr version, SDK
version, and artifact hashes. Record fixture product/build and protocol
identities separately rather than presenting them as Debug Helper identities.

Do not create `hil.yml` until a dedicated self-hosted runner and stable automated
fixture exist. Firmware compilation is not hardware acceptance.

## Coding-Agent Plugin

After clean installed-package MCP acceptance passes, add:

```text
plugins/dutchmate/
  plugin.json
  mcp.json
  skills/

.agents/plugins/marketplace.json
```

Use the portable root manifests and configure local stdio MCP through:

```text
dutchmate mcp
```

Validate manifest schemas, skill frontmatter, referenced files, installed
command resolution, MCP initialization, and the nine expected tools. Plugin
skills may describe workflows and evidence interpretation but must not duplicate
Device Core, backend, or firmware behavior.

Claude Code support remains MCP registration documentation until authenticated
host acceptance is possible. Do not target the public plugin directory in this
slice because DUTchMate intentionally uses local stdio while the public
submission path expects a remote HTTPS MCP endpoint.

## Public Release Gate and Publication Order

CI, private artifacts, firmware builds, and the local plugin proceed before a
public release. The owner approved Nahit Pawar as the public publisher and a
mixed-license repository policy on 2026-09-23. Apache-2.0 covers all six Python
distributions and both firmware projects; CC-BY-4.0 covers general
documentation. Future KiCad hardware design material may use CERN-OHL-P-2.0
only after a provenance audit. The legacy EAGLE design under
`hardware/pcb/debug-helper/legacy-eagle/` remains outside the new license grants
and all public release artifacts; `hardware/pcb/debug-helper/rev-a/` is reserved
for the future KiCad source.

The root `LICENSE.md` is the authoritative scope map. Each publishable Python
project declares the SPDX expression `Apache-2.0` and includes its own complete
license text in wheels and source distributions. The non-published workspace
root does not declare one project license because the repository is mixed
license. Future pull-request commits require DCO 1.1 sign-off; the repository
instructions and pull-request template must be backed by a required DCO status
check configured in GitHub.

`.github/workflows/release.yml` keeps its unprivileged build, TestPyPI publish,
TestPyPI digest verification, production publish, and production digest
verification jobs separate. The protected `testpypi` and `pypi` environments
remain the only publication environments. Do not register or publish
`dutchmate-debug-agent` until the `v0.2.0` release slice.

[PyPI permits only one pending GitHub Trusted Publisher for a given owner,
repository, workflow, and environment tuple](https://github.com/pypi/warehouse/issues/16920).
The five new monorepo projects therefore cannot all be registered as pending
publishers at once. The initial `v0.1.0` release uses the Warehouse-supported
sequential bootstrap: register one pending project, publish it so the pending
publisher becomes normal, then register the next pending project with the same
tuple. [Normal publishers may be associated with multiple
projects](https://docs.pypi.org/trusted-publishers/adding-a-publisher/). This
bootstrap is required independently on TestPyPI and production PyPI because
they are separate indexes.

The host release workflow must:

1. accept only `vX.Y.Z` tags;
2. verify the tag against the root and all six package versions;
3. build and validate all six workspace artifact pairs once;
4. select and revalidate the five `v0.1.0` public artifact pairs without
   rebuilding;
5. retain only those accepted public artifacts immutably;
6. expose one separately protected OIDC publication job per project and index;
7. publish to TestPyPI sequentially in this exact order: `dutchmate-core`,
   `dutchmate-cli`, `dutchmate-service`, `dutchmate-mcp-server`, then
   `dutchmate`;
8. require each TestPyPI job to complete before the next job can reach the
   `testpypi` environment approval gate;
9. verify every TestPyPI filename and SHA-256 digest against the retained
   artifacts;
10. prevent the first production job from starting unless the complete
    TestPyPI verification succeeds;
11. publish the same artifacts to production through separately protected
    `pypi` jobs in the same dependency order;
12. verify every production filename and SHA-256 digest against the retained
    artifacts;
13. use `uv publish` with Trusted Publishing and index checks in publishing
    jobs without rebuilding.

### Initial `v0.1.0` Trusted Publisher Bootstrap

Before pushing `v0.1.0`, register only `dutchmate-core` as a pending TestPyPI
publisher with owner `leonahi`, repository `DUTchMate`, workflow `release.yml`,
and environment `testpypi`. If a different project currently holds that pending
tuple, remove it and register `dutchmate-core` instead. Confirm that the
`testpypi` environment requires review and permits the release tag before
starting the workflow.

After the build job accepts and retains the five-package artifact set:

1. approve `publish-testpypi-core`;
2. after it succeeds and its publisher is normal, register
   `dutchmate-cli` as the sole pending publisher for the same tuple and approve
   `publish-testpypi-cli`;
3. repeat for `dutchmate-service`, `dutchmate-mcp-server`, and `dutchmate`,
   approving only the corresponding waiting job each time;
4. require `verify-testpypi` to validate all five projects and all ten retained
   files before any production action.

Only after `verify-testpypi` succeeds, register `dutchmate-core` as the sole
pending production publisher with the same repository and workflow but the
`pypi` environment. Repeat the same one-at-a-time registration and approval
sequence through `publish-pypi-dutchmate`. Every production job remains behind
the protected `pypi` environment, and `verify-pypi` validates the exact retained
files after the final upload.

Do not bypass environment protection or approve a job until its matching
pending or normal publisher is visible on the target index. Failed jobs may be
retried against the retained artifacts; the configured index check prevents an
identical existing file from being treated as a new build.

If sequential pending conversion fails because Warehouse behavior changes,
stop before publishing the next project. The contingency is a temporary
account-wide token for the affected index, exposed only through its protected
GitHub environment, to upload the missing project from the exact retained
artifact. Immediately revoke the token, remove the secret, and register the
normal `release.yml` Trusted Publisher for the newly created project before
continuing. This broader-credential path is a last resort and is not part of
the normal workflow.

Recheck project names immediately before registration because prior availability
checks are not reservations.

A future `.github/workflows/firmware-release.yml` may publish already-tested
Debug Helper binaries and provenance for `debug-helper-vX.Y.Z`. Do not create it
until public versioned UF2/ELF distribution is needed. Host and firmware release
workflows never require matching version numbers or simultaneous releases.

## Implementation Sequence

The independently testable slices are:

1. Establish host CI and extend existing architecture/protocol contracts.
2. Add the aggregator, synchronized host-version validation, and executable
   ownership migration.
3. Add clean-wheel, isolated uv-tool, Debug Agent API, and installed-MCP
   acceptance.
4. Add firmware compile CI and independent version/provenance metadata.
5. Add and validate the local coding-agent plugin.
6. Record the approved license and public publisher metadata, add the DCO
   contribution policy, and add the separately gated release workflow.
7. Limit the `v0.1.0` public artifact set to the five deterministic host
   distributions while preserving Debug Agent workspace CI.
8. Validate the retained artifacts through TestPyPI.
9. Publish the same artifacts to production PyPI.

Every completed slice runs Ruff, mypy, full pytest, and `git diff --check`, plus
its focused acceptance tests. Structural slices update architecture
documentation and Graphify once near completion.

## Initial Support Boundaries

- Linux and macOS are supported; Windows is not claimed.
- The Debug Agent is a provider-disabled workspace feature until its planned
  public `v0.2.0` release.
- Device Core HTTP endpoints, MCP tool schemas, Enhanced protocol v1, session
  formats, Basic/Enhanced backend isolation, and hardware ownership do not
  change.
- Coverage thresholds, formatting enforcement, attestations, SBOMs, automated
  HIL, public plugin submission, and public firmware binaries remain later
  hardening work.

## References

- [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/)
- [uv tool executable rules](https://docs.astral.sh/uv/concepts/tools/#tool-executables)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [OpenAI portable plugin packaging](https://developers.openai.com/plugins/build/plugins)
