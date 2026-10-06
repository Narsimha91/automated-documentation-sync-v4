# Design Review: Automated Documentation Sync

## Findings

- Concurrent publisher runs could race while updating the same branch or opening duplicate pull requests. Serialize workflow runs and bind tests, feature loading, generation, and the later merge to the triggering `main` commit SHA.
- Matching pull requests by title alone could select an unrelated or ambiguous PR. Constrain lookup to the exact approved title, base branch `main`, and a same-repository head branch prefixed `user/update-features-`; stop safely if more than one open PR qualifies.
- Updating a long-lived PR branch without bringing it up to date can publish against stale `main`. Merge the tested `main` SHA into the branch normally; on conflict, stop without pushing.
- Marker recognition and replacement needed clearer boundaries. Permit trimming surrounding whitespace only when recognizing marker lines, retain their original text, require exactly one ordered start/end pair, and restrict the marked content to the `# features` heading and generated bullets.
- Publishing unchanged generated content would create unnecessary commits or pushes. Compare output on the selected target branch and skip the commit and push when it is unchanged.
- A separate token or PR-triggered validation workflow is unnecessary for the agreed gate. Run `pytest` before README generation and use the least permissions needed by `GITHUB_TOKEN`.

## Final Decisions

- Trigger only for qualifying pushes to `main`; serialize workflow publisher runs without canceling the active run. Check out the triggering event SHA and use that same revision for `pytest`, feature retrieval, README generation, and merging into an existing PR branch.
- Run `pytest` before feature retrieval or README generation. A test failure stops the workflow. No separate PR-triggered checks are required.
- Preserve the `# features` heading and original marker lines. Marker matching may trim surrounding whitespace, but the README must have exactly one ordered start/end pair enclosing that heading and the generated bullets. Replace only generated bullets and preserve all other content.
- Identify an existing PR only by the exact title `[docs-sync] Update README features`, base `main`, and same-repository head prefix `user/update-features-`. Reuse exactly one open match; if lookup is ambiguous, fail without pushing or creating another PR. If none exists, create the timestamped branch and PR; do not reuse closed or merged PRs.
- Render the feature bullets in memory after tests. Select or prepare the target branch, merging the tested `main` SHA locally into an existing PR branch before applying the bullets. A merge conflict stops the workflow without pushing. Validate and update the target README only after branch setup; identical output causes no commit or push and does not open a new PR.
- Use `GITHUB_TOKEN` with `contents: write` and `pull-requests: write`; no broader permissions or PR-triggered checks are part of this design.

## Open Issues

None identified from the approved requirements and decisions.
