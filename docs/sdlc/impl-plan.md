# Implementation Plan

The repository is greenfield: there are no `src/`, test, or GitHub Actions workflow files yet. Complete phases in order; each phase depends on the preceding phase.

1. **Bootstrap the feature source and test setup.** Create `src/features.py` with an ordered `features()` source and establish the `pytest` setup. This provides the source data and test foundation for subsequent work.
2. **Implement README synchronization.** Validate exactly one ordered marker pair before writing; preserve the original marker lines, `# features` heading, and all content outside generated bullets. Render features in source order and avoid writes when the result is unchanged.
3. **Add focused tests.** Cover feature ordering and deterministic output, marker validation, README preservation, and unchanged-output behavior. This validates the synchronizer before workflow integration.
4. **Add the GitHub Actions test gate.** Trigger only on pushes to `main` changing `src/features.py`, serialize runs without canceling the active run, check out the triggering event SHA, and run `pytest` before feature retrieval or README generation. A test failure must stop the workflow.
5. **Implement safe branch and PR publication.** Select only an open PR matching the exact title, `main` base, and same-repository `user/update-features-` head prefix; stop safely if selection is ambiguous. Otherwise create a UTC timestamped branch. For an existing PR, merge the tested event SHA locally before editing and stop without pushing on conflict. Commit and publish only when the target README changes; open a PR only for a changed new branch.
