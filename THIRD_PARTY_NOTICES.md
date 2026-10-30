# Third-party notices

Third-party material retains its own terms and is excluded from DUTchMate's
MIT and CERN-OHL-P-2.0 grants. This inventory records material found during
the 2026-10-30 licensing audit; it does not resolve unknown provenance.

## Agent Plugins schemas

`tests/packaging/schemas/plugin.schema.json` and `mcp.schema.json` are local
copies of the [Agent Plugins 1.0.0 schemas](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json).
The [upstream policy](https://github.com/agentplugins/agent-plugins-spec/blob/main/LICENSE.md)
licenses schemas under Apache-2.0. The complete license is retained in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).

The plugin schema matches the upstream JSON; the local MCP schema differs in
the `streamableHttpServer` title (`Streamable HTTP server` rather than
`Streamable HTTP MCP server`). Both local files are preserved unchanged by
this migration. Neither local file contains a separate copyright notice.

## Graphify tooling

`.codex/skills/graphify/` contains third-party Graphify tooling, identified by
its `.graphify_version` as 0.9.48. It is not relicensed. The
[upstream v0.9.48 NOTICE](https://github.com/Graphify-Labs/graphify/blob/v0.9.48/NOTICE)
reads:

> Graphify
>
> Copyright 2026 Safi Shamsi and the Graphify contributors.
>
> This product is licensed under the Apache License, Version 2.0 (see LICENSE).
>
> Portions of this software were contributed under the MIT License prior to the
> relicensing and remain available under those terms. The original MIT license
> text is retained in LICENSE-MIT.

The license texts are available here as
[Apache-2.0](LICENSES/Apache-2.0.txt) and
[Graphify's retained MIT text](LICENSES/Graphify-MIT.txt).

## Developer Certificate of Origin

[DCO](DCO) retains its Linux Foundation copyright and verbatim-copy notice.
It is a contribution certification, not DUTchMate-authored software, and is
unchanged.

## CAD assets and unresolved provenance

- `hardware/pcb/debug-helper/legacy-eagle/` remains excluded from both new
  grants. Its `.brd` and `.sch` files embed SparkFun, Adafruit, RpiPico,
  SnapEDA-linked, and Ultra Librarian material. SparkFun-Connectors carries a
  CC-BY-SA-4.0 link; Ultra Librarian attributes state “Copyright (C) 2026 Ultra
  Librarian. All rights reserved.” These notices and links remain intact.
  Complete asset origins and redistribution permissions are not established;
  no uniform replacement license is asserted for these files.
- `hardware/pcb/debug-helper/rev-a/` embeds standard KiCad symbols and
  footprints alongside project-owned definitions, and references external
  `${KICAD10_3DMODEL_DIR}` models. KiCad library data is under
  [CC-BY-SA-4.0 with the KiCad design exception](https://www.kicad.org/libraries/license/).
  The exception allows designs to use library data under their own license;
  separately redistributed library collections retain upstream terms.
  CERN-OHL-P-2.0 covers DUTchMate's design contributions, not ownership of
  these external assets. No external 3D model files are tracked here.
- The Rev-A README identifies `libraries/symbols/dutchmate.kicad_sym` as
  project-owned. Its four definitions are included in the DUTchMate grant on
  that basis. The repository does not record a complete per-asset upstream
  revision/provenance inventory for all embedded or referenced CAD data.
  Imported assets and manufacturing outputs still require that audit before
  a hardware release; no such audit or physical acceptance is claimed here.

## Firmware dependencies and generated material

DUTchMate's two firmware applications use Zephyr and its dependencies through
external build workspaces. No vendored Zephyr source tree is tracked in this
repository. Those projects retain their licenses, as do any upstream-derived
files or notices in generated build outputs. Licensing the DUTchMate-authored
applications under MIT does not change dependency licenses.

Existing ignored build/cache/evidence files, local manufacturing exports, and
`graphify-out/` are left unchanged by this migration. The retained
[CC-BY-4.0 text](LICENSES/CC-BY-4.0.txt) supports historical licensing references;
it is no longer the default for DUTchMate-authored documentation.
