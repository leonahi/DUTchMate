# DUTchMate Licensing

Copyright 2026 Nahit Pawar and DUTchMate contributors.

DUTchMate is a mixed-license repository. A license applies only to the areas
listed below; the presence of a license text at the repository root does not
grant that license to every file.

| Repository material | License |
|---|---|
| Python host software in `core/`, `apps/`, and `packages/` | [Apache-2.0](LICENSES/Apache-2.0.txt) |
| Tests, CI/release automation, build scripts, protocol schemas, and the portable plugin | [Apache-2.0](LICENSES/Apache-2.0.txt) |
| DUTchMate-authored RP2350 Debug Helper and Pico fixture firmware | [Apache-2.0](LICENSES/Apache-2.0.txt) |
| General documentation and validation reports | [CC-BY-4.0](LICENSES/CC-BY-4.0.txt) |

Reusable source examples and substantial executable code samples are licensed
under Apache-2.0 even when they accompany documentation. Short illustrative
snippets embedded in documentation follow the document's CC-BY-4.0 license.

## Hardware design exception

The legacy material under `hardware/pcb/debug-helper/legacy-eagle/`, including
the EAGLE board and schematic files, is **not covered** by either of the new
repository license grants. Those files contain or refer to third-party library
material and remain subject to their embedded notices and applicable
third-party terms.

The replacement path is `hardware/pcb/debug-helper/rev-a/`, but no KiCad design
or CERN-OHL-P-2.0 grant is present yet. Before a future hardware release, the
KiCad symbols, footprints, models, templates, imported assets, design sources,
and manufacturing outputs must receive a provenance audit. Compatible
DUTchMate-owned material may then be explicitly licensed under CERN-OHL-P-2.0.

## Documentation attribution

When sharing CC-BY-4.0 material, attribute it to “Nahit Pawar and DUTchMate
contributors,” link to <https://github.com/leonahi/DUTchMate>, link to the
CC-BY-4.0 license, and indicate whether changes were made.

## Contributions and third-party material

All future pull-request commits require Developer Certificate of Origin 1.1
sign-off as described in [CONTRIBUTING.md](CONTRIBUTING.md). The DCO is a
contribution certification, not a copyright assignment.

Third-party material remains governed by its own license and attribution
notices. In particular, this policy does not relicense third-party tooling under
`.codex/` or the excluded hardware-design files.
