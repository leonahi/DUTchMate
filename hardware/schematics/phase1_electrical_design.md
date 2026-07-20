# Phase 1 Electrical Design

> Status: superseded reference
> Current source of truth: `docs/dutchmate_hardware_architecture.md`

The detailed Phase 1 electrical interface has moved to
`docs/dutchmate_hardware_architecture.md`.

That document now owns the proposed voltage-domain GPIO/UART architecture,
including:

- Four DUTchMate-to-DUT control channels: `CTRL0` to `CTRL3`
- Four DUT-to-DUTchMate event channels: `EVENT0` to `EVENT3`
- Fixed-direction UART translation
- `DUT_VIO` validity requirements
- Control-channel open-drain behavior
- User configuration mapping from physical channels to DUT signal roles

Keep schematic-capture notes and implementation-specific pin assignments in this
directory, but avoid duplicating architecture decisions here.
