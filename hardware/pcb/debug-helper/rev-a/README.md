# Debug Helper Revision A — KiCad source

This directory is reserved for the replacement KiCad design for the DUTchMate
Debug Helper Revision A PCB. The KiCad design has not been added yet.

The historical EAGLE design and its original Revision A design record are
preserved under `../legacy-eagle/`. Do not copy embedded EAGLE libraries or
third-party CAD assets from that directory into this KiCad project.

When the KiCad design is added, keep the editable project sources, project-owned
symbols and footprints, 3D models, provenance notes, and reviewed manufacturing
outputs in version control. KiCad local settings, locks, autosaves, backups, and
scratch export directories are excluded by the repository `.gitignore`.

Suggested ownership:

```text
rev-a/
  *.kicad_pro, *.kicad_sch, *.kicad_pcb  Editable project sources
  libraries/                             Project-owned symbols and footprints
  docs/                                  Design and third-party provenance notes
  manufacturing/                         Reviewed release-ready outputs
```

No CERN-OHL-P-2.0 grant applies to this directory until the design is present
and every symbol, footprint, model, template, imported asset, and manufacturing
output has passed the planned provenance audit.
