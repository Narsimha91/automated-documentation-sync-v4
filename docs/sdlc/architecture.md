# Architecture: Automated Documentation Sync

## Stack

- Python standard library for feature loading, README marker validation and generation, Git operations, and GitHub REST API calls.
- `pytest` for the test gate and focused unit tests.
- GitHub Actions to run the sync workflow and provide the repository token.

## Components

- **Workflow trigger and runner:** Run on pushes to `main` that change `src/features.py`. Serialize workflow runs with a shared concurrency group and do not cancel the active run. Check out the triggering `main` commit by its event SHA, then run `pytest` before feature retrieval or README generation. Tests, feature retrieval, and generation all use that same SHA. A failing test ends the run without changing the README.
- **Feature and README synchronizer:** After tests pass, call `features()` in `src/features.py`, preserving the returned order. Recognize marker lines after trimming surrounding whitespace, but preserve the original marker lines. Require exactly one ordered start/end pair, with the marked region consisting of the existing `# features` heading followed by generated bullets. Reject invalid structure before writing. Replace only the generated bullet lines, preserving the heading and all README content outside the marked region. Deterministic formatting produces the same README for the same feature list. If the resulting README is identical to the existing file, do not create a commit or push.
- **Branch and pull-request publisher:** Find open pull requests by the exact title `[docs-sync] Update README features`, base branch `main`, and a same-repository head branch whose name starts with `user/update-features-`. Reuse the matching PR and branch when exactly one qualifies. If multiple PRs qualify, fail safely without pushing or creating another PR. If none qualifies, prepare a branch named `user/update-features-<UTC timestamp>` using `YYYYMMDDTHHmmssZ` from the tested `main` SHA. Closed and merged pull requests are not reused. For an existing PR, fetch its branch and merge the tested `main` event SHA locally using a normal merge. Apply the generated bullets to the target branch's README only after this merge. If the merge conflicts, stop without pushing any changes to the PR branch. Commit and push only when the target README changes; open a PR only for a new branch with a change to publish.

## Data Flow

1. A qualifying push starts the workflow; changes to unrelated paths do not. The concurrency group prevents publisher runs from executing simultaneously.
2. Check out the triggering `main` event SHA and execute `pytest` against that revision. On failure, stop before importing `features()` or writing the README.
3. Load the ordered feature list from the same checked-out SHA and render its bullet lines in memory. Do not write the README yet.
4. Look up open PRs using the stable exact title, base `main`, and same-repository head prefix. Reuse exactly one match; stop without publishing if the result is ambiguous. For an existing PR, fetch its branch and merge the tested event SHA locally using a normal merge; a conflict stops the workflow without pushing. Otherwise, prepare a UTC-timestamped branch from the tested event SHA.
5. On the target branch, validate the single ordered marker pair (allowing surrounding whitespace only when recognizing marker lines), then replace only the generated bullets in the `# features` section. Preserve the original marker lines, heading, and all content outside the generated bullets. Invalid structure causes a failure with no README write. If the target README is unchanged, do not commit or push; for a new branch, do not push or open a PR. Otherwise, commit and push the README change, updating the existing PR or opening a new one.

## GitHub Permissions

Use the built-in `GITHUB_TOKEN` with only `contents: write` and `pull-requests: write`. These permissions allow pushing the generated README branch and listing or creating pull requests. This is sufficient because `pytest` is the required pre-generation gate and no PR-triggered checks are required. Do not grant write access to unrelated repository resources.

## Targeted Tests

- Workflow filtering and serialization: changes to `src/features.py` on `main` run the workflow; unrelated paths and other branches do not. Publisher runs do not execute concurrently.
- Revision consistency and test gate: tests, feature retrieval, and generation use the triggering `main` SHA; failing `pytest` prevents feature retrieval and all README writes.
- Feature generation: returned order is retained and identical input yields identical bullets.
- Marker validation: missing, duplicated, or reversed markers are rejected without a README write; surrounding whitespace is ignored for recognition and original marker lines are preserved. The region contains the `# features` heading and generated bullets.
- README preservation and no-op: the heading, marker lines, and content outside generated bullets remain unchanged. Identical output causes no commit or push and does not open a new PR.
- PR selection and publication: only open same-repository PRs with the exact title, base `main`, and required head prefix qualify. One match is reused; ambiguous matches fail without publishing; no match causes a new correctly formatted timestamped branch and PR. A normal merge of the tested main SHA precedes updating an existing PR, and a merge conflict prevents a push.
- Token scope: the built-in `GITHUB_TOKEN` with contents and pull-request write permissions supports the flow; no PR-triggered checks are required.
