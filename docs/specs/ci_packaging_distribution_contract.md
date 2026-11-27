# CI, Packaging and Distribution Contract

**Scope:** package ownership, version authorities, CI and release acceptance.
Tasks and follow-up work live in GitHub Issues and PRs; approved release scope
is summarized in the [milestone overview](../development_status.md).

## Purpose

Define repeatable CI, installable Python distributions, independently versioned
firmware artifacts, gated public releases, and local coding-agent integration
without changing DUTchMate's Device Core, backend, protocol, or hardware-control
boundaries.

Delivery infrastructure is independent of Debug Agent analysis and Phase 1
hardware acceptance. Normal pull-request CI remains independent of physical
hardware. Implementation evidence belongs in PRs; publication evidence belongs
with the release and retained artifact records.

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
- GitHub Issues own work tracking and PRs own implementation/validation records.
  The milestone overview summarizes release scope and acceptance; the previous
  development history is archived.

## Python Distribution Model

### Current distribution graph

The workspace has five component distributions:

```text
dutchmate-core
├── dutchmate-cli
├── dutchmate-service
├── dutchmate-mcp-server
└── dutchmate-debug-agent
```

The sixth workspace distribution, `dutchmate`, lives under `packages/dutchmate`.
It is the normal user installation target and depends on:

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

Normal-user executable ownership belongs to the aggregator:

| Executable | Authoritative owner |
|---|---|
| `dutchmate` | `dutchmate` |
| `dm` | `dutchmate` |
| `dutchmate-service` | `dutchmate` |
| `dutchmate-mcp` | `dutchmate` |
| `dutchmate-debug` | `dutchmate-debug-agent` |

The aggregator's scripts call the component entry functions. CLI, service and
MCP component distributions do not declare competing console scripts.

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

The Debug Agent remains excluded until a public distribution is explicitly
approved; a host version bump alone does not add it. That future slice must
confirm its coding-agent access model and public command surface before adding
any aggregator extra or launcher. If
`dutchmate debug` is introduced, it must invoke the installed Debug Agent's
Python API directly rather than locating the dependency-owned executable on
`PATH`, because `uv tool install` does not expose dependency executables by
default.

Any Debug Agent public-distribution acceptance must preserve import failures
raised inside the installed Debug Agent rather than converting them into misleading
missing-feature errors.

Executable-ownership changes must update metadata, runtime callers, tests and
current documentation together. Never give two distributions ownership of the
same command. Preserve historical validation records as recorded.

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
Debug Agent remains a private CI input until its publication is approved;
current release scope is recorded in development status.

CI fails if any distribution version differs or an internal dependency lacks
the exact synchronized constraint. Release version changes update the root and
all six package declarations atomically.

Host release tags use:

```text
vX.Y.Z
```

### Debug Helper firmware

The RP2350 Debug Helper owns `PRODUCT_VERSION`, initially `0.1.0`.
It is authoritative for the firmware product version and is
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

`.github/workflows/ci.yml` defines four host CI jobs:

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

Architecture contracts cover the Debug Agent alongside the other delivery
packages. Protocol schema tests enumerate every checked-in example; do not add
duplicate boundary checkers.

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
9. Start the installed MCP server over stdio, perform modern discovery, list the
   [twelve v2 tools](mcp_adapter_contract.md#target-tool-catalog) in deterministic
   order, verify bounded unavailable-service errors and clean EOF.

While Debug Agent publication remains deferred, copy only the five public
wheel/source-distribution pairs into a separate release directory, rerun
metadata, command, and MCP acceptance against
that exact directory, and retain only those accepted artifacts for publishing.

Also run an actual isolated `uv tool install` smoke test with temporary
`UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` values. This verifies the published user
workflow rather than assuming ordinary virtual-environment behavior matches uv
tool exposure rules.

The package slice is complete only when both the installed-wheel workflow and
the normal `uv` workspace development workflow pass.

## Firmware CI and Provenance

`.github/workflows/firmware.yml` is independent from host CI. It uses
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

The local coding-agent plugin has this layout:

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
command resolution, modern MCP discovery, and the twelve-tool v2 catalog. Plugin
skills may describe workflows and evidence interpretation but must not duplicate
Device Core, backend, or firmware behavior.

Claude Code support remains MCP registration documentation until authenticated
host acceptance is possible. Do not target the public plugin directory in this
slice because DUTchMate intentionally uses local stdio while the public
submission path expects a remote HTTPS MCP endpoint.

## Public Release Gate and Publication Order

CI, private artifacts, firmware builds, and the local plugin proceed before a
public release. The owner approved Nahit Pawar as the public publisher on
2026-09-23. The current [licensing policy](../../LICENSE.md) applies MIT to all six
Python distributions, DUTchMate-authored firmware, protocol definitions,
documentation, scripts, and supporting tools. DUTchMate-authored hardware
design files under `hardware/pcb/`, including the current Rev-A KiCad source,
use CERN-OHL-P-2.0. Third-party assets retain their own terms. The legacy EAGLE
design under `hardware/pcb/debug-helper/legacy-eagle/` remains outside the new
grants and all public release artifacts; unresolved CAD provenance is recorded
in the [third-party notices](../../THIRD_PARTY_NOTICES.md).

The root `LICENSE.md` is the authoritative scope map. Each publishable Python
project declares the SPDX expression `MIT` and includes its own complete
license text in wheels and source distributions. The non-published workspace
root does not declare one project license because the repository is mixed
license. Future pull-request commits require DCO 1.1 sign-off; the repository
instructions and pull-request template must be backed by a required DCO status
check configured in GitHub.

`.github/workflows/release.yml` keeps its unprivileged build, TestPyPI publish,
TestPyPI digest verification, production publish, and production digest
verification jobs separate. The protected `testpypi` and `pypi` environments
remain the only publication environments. Do not register or publish
`dutchmate-debug-agent` without explicit public-distribution approval.

The host release workflow must:

1. accept only `vX.Y.Z` tags;
2. verify the tag against the root and all six package versions;
3. build and validate all six workspace artifact pairs once;
4. select and revalidate the five public artifact pairs while Debug Agent is
   deferred, without rebuilding;
5. retain only those accepted public artifacts immutably;
6. expose one separately protected OIDC publication job per project and index;
7. publish to TestPyPI sequentially in this exact order: `dutchmate-core`,
   `dutchmate-cli`, `dutchmate-service`, `dutchmate-mcp-server`, then
   `dutchmate`;
8. require each TestPyPI job to complete before the next job can run, without
   assuming that GitHub will request a separate environment review for every
   job using the same environment in one workflow run;
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

### Publisher configuration and historical bootstrap

Existing projects use their registered Trusted Publishers and protected index
environments. Register a new project only when the approved public artifact set
adds it; verify the repository, workflow and environment binding separately on
TestPyPI and PyPI. Never bypass environment protection or rebuild the accepted
artifacts during publication.

The completed first-release register-and-rerun procedure and implementation
sequence are historical records, not instructions to bootstrap every version.
Their full text is retained in Git:

```text
git show eff9d67cd1828c3233308c061da4968fbd4509a0:docs/ci_packaging_distribution_plan.md
```

Public firmware binaries, if separately approved, use independent
`debug-helper-vX.Y.Z` tags and retained tested artifacts/provenance. Host and
firmware versions and release dates need not match.

## Initial Support Boundaries

- Linux and macOS are supported; Windows is not claimed.
- The Debug Agent is a provider-disabled workspace feature until separately
  approved for public distribution.
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
