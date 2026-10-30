# DUTchMate Licensing

Copyright 2026 Nahit Pawar and DUTchMate contributors.

DUTchMate is a mixed-license repository. Unless otherwise noted,
DUTchMate-authored software, firmware, protocol definitions, documentation,
scripts, and supporting tools are licensed under the [MIT License](LICENSE).

| Repository material | License |
|---|---|
| Python host software in `core/`, `apps/`, and `packages/` | [MIT](LICENSE) |
| DUTchMate-authored tests, CI/release automation, scripts, protocol definitions, schemas, examples, and portable plugin | [MIT](LICENSE) |
| DUTchMate-authored RP2350 Debug Helper and Pico fixture firmware | [MIT](LICENSE) |
| DUTchMate-authored documentation and validation reports | [MIT](LICENSE) |
| DUTchMate-authored hardware design files and accompanying design metadata under `hardware/pcb/`, subject to the exceptions below | [CERN-OHL-P-2.0](LICENSES/CERN-OHL-P-2.0.txt) |

The MIT default includes DUTchMate-authored executable examples and snippets
embedded in documentation. It does not cover hardware design files or
third-party material. Previously published releases retain their original
license notices; this policy describes the current checkout.

## Hardware design exception

Hardware design files under `hardware/pcb/` are licensed under CERN-OHL-P-2.0
to the extent authored by DUTchMate. The grant includes the current KiCad
design in `hardware/pcb/debug-helper/rev-a/` and its project-owned symbol
definitions. It does not relicense embedded or referenced third-party symbols,
footprints, models, or other assets.

The legacy material under `hardware/pcb/debug-helper/legacy-eagle/`, including
the EAGLE board and schematic files, is **not covered** by the MIT or
CERN-OHL-P-2.0 grants. It contains third-party library material whose full
provenance and redistribution terms are not established; its embedded notices
and applicable third-party terms remain intact.

See the [hardware licensing scope](hardware/pcb/README.md) and
[third-party notices](THIRD_PARTY_NOTICES.md) for the asset exceptions and
remaining provenance uncertainties. No hardware acceptance or completed
manufacturing-output provenance audit is implied by this grant.

## Branding

The DUTchMate name, logo, and associated branding are excluded from these
license grants. The MIT License and CERN-OHL-P-2.0 do not grant permission to
use them to identify or promote derivative products as official DUTchMate
products.

## Contributions and third-party material

All future pull-request commits require Developer Certificate of Origin 1.1
sign-off as described in [CONTRIBUTING.md](CONTRIBUTING.md). The DCO is a
contribution certification, not a copyright assignment.

Third-party components retain their respective licenses and attribution
notices, including Zephyr and other firmware dependencies. No Zephyr source or
dependency license is changed by licensing DUTchMate-authored firmware under
MIT. The copied Agent Plugins schemas, Graphify tooling under `.codex/`, DCO,
and external CAD assets are exceptions to the repository default; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
