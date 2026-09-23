# Contributing to DUTchMate

Thank you for contributing. Before opening a pull request, read the repository
engineering constraints in `AGENTS.md` and the mixed-license policy in
`LICENSE.md`.

## Developer Certificate of Origin

Every new pull-request commit must certify the
[Developer Certificate of Origin 1.1](DCO). Add the certification with:

```shell
git commit -s
```

Git adds a trailer in this form, using the identity configured for the commit:

```text
Signed-off-by: Your Name <your.email@example.com>
```

The sign-off certifies that you have the right to contribute the change under
the license indicated for the affected files. It is not a copyright assignment.
If a pull request contains unsigned commits, amend or rebase those commits and
force-push the corrected branch. Do not add one blanket sign-off in the pull
request description.

## Validation

Run the focused tests for your change, followed by the repository gate:

```shell
uv lock --check
uv run --frozen ruff check .
uv run --frozen mypy
uv run --frozen pytest
git diff --check
```

Do not add or replace hardware-design assets without recording their origin and
license. The legacy EAGLE design remains outside the repository's new license
grants pending replacement by an audited KiCad design.
