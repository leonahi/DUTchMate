# Contributing to DUTchMate

Thank you for contributing. Before opening a pull request, read the repository
engineering constraints in `AGENTS.md` and the mixed-license policy in
`LICENSE.md`.

## Issues and pull requests

Use [GitHub Issues](https://github.com/leonahi/DUTchMate/issues) for substantive
bugs, features, maintenance and hardware-validation work. Search for an existing
issue first. Give each issue one clear outcome, acceptance criteria, a lead
assignee, and links to specifications, dependencies and evidence. Small mechanical
fixes can use a PR alone. Use the bug or work-item form when opening an issue.

Start from an issue that is ready and has an owner. Open a focused branch and PR;
describe the resulting behavior, validation commands/results and remaining
limitations. Link the issue, using `Closes #123` only when that PR resolves all
of its acceptance criteria. Use a normal reference for partial work. Request a
review and complete CI before merging. Keep substantive follow-up work in a
linked issue rather than hiding it in the PR description.

Issues own tasks, owners, blockers and dependencies. PRs own implementation and
validation records. Specifications and architecture retain durable contracts
and decisions; release notes describe user-visible changes. Keep measured
hardware evidence in `hardware/validation/` and link it from the issue/PR.

`docs/development_status.md` is only a milestone/acceptance overview; update it
when release scope or milestone acceptance changes. `docs/development_history.md`
is a frozen archive. Contributors do not update both files for every change.

### Team board and release planning

Use the [DUTchMate team board](https://github.com/users/leonahi/projects/1/views/2) for issues and linked PRs.
The Status values are **Backlog**, **Ready**, **In progress**, **In review** and
**Done**. Assign a lead owner before starting Ready work. Keep blocked and
unselected/deferred work in Backlog, with its prerequisite or scope decision
recorded in the issue.

Use labels **bug**, **enhancement**, **maintenance**, **hardware**, **blocked**
and **deferred** to distinguish work and prerequisites. Labels and board columns
do not replace acceptance criteria.

The [v0.2.0 milestone](https://github.com/leonahi/DUTchMate/milestone/1) covers the approved five public host
distributions; Debug Agent publication stays deferred. Add only work actually
selected for that release, not every open hardware/future task. Physical
acceptance and optional host checks retain their independent scopes.

The issue forms and PR template take effect after they are merged into the
default branch. No automatic project assignment is hard-coded; add new issues
and PRs to this project during triage. Developers who manage the board need
project **Write** access via Settings → Manage access. Project and repository
permissions are managed separately; see
[GitHub's access instructions](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects).

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
