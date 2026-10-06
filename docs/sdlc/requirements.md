# Requirements: Automated Documentation Sync

## Functional Requirements

1. Run the workflow only for pushes to `main` that change `src/features.py`. Ignore changes to unrelated files.
2. Run `pytest` before feature retrieval or README generation. If any test fails, stop the workflow and report the failure.
3. After tests pass, call `features()` in `src/features.py` and use its returned list as the source of the README Features content, preserving the list's order.
4. Preserve the existing `# features` heading and replace only the generated bullet lines with a bullet list of the returned features.
5. The README must contain exactly one `docs-sync: start` marker and exactly one `docs-sync: end` marker, with the start marker before the end marker. Reject malformed or duplicated markers before writing.
6. Update only the generated bullet lines inside the marker pair; preserve the `# features` heading and all README content outside the marker pair.
7. Create a feature branch named `user/update-features-<UTC timestamp>` for the workflow. If an open pull request for this workflow exists, reuse its branch and update that same pull request. Otherwise, create a new timestamped branch and pull request.
8. When updating an existing pull request, merge the tested `main` revision into its branch using a normal merge. If the merge conflicts, stop the workflow without pushing changes to the PR branch.

## Non-Functional Requirements

1. Given the same returned feature list, generation must produce deterministic README content.
2. Invalid marker structure must not result in a README write.

## Assumptions

- Use the UTC time when creating the branch, formatted as `YYYYMMDDTHHmmssZ` (for example, `20261006T142530Z`) so the timestamp is valid in a branch name.
- Only an open pull request counts as an existing workflow pull request. Merged or closed pull requests are not reused; create a new timestamped branch and pull request.
