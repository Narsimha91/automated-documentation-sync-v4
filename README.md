# Automated Documentation Sync

A small Python project that maintains a deterministic, generated Features list in this README from an explicitly maintained Python module.

The synchronizer updates only the generated section and rejects malformed markers before writing.

## Features List
<!-- docs-sync: start --> 
# features
- Maintains an ordered Python source for README features
- Validates README markers before changing generated content
- Preserves README content outside generated feature bullets
- Skips writes when generated content is unchanged
<!-- docs-sync: end -->