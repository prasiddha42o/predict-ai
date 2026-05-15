# tests

Test suite. Not yet implemented.

Planned coverage, added alongside the code it tests rather than after the fact:

- `ml/` — preprocessing determinism, feature engineering, split integrity, metric
  correctness against hand-computed cases.
- `backend/` — inference pipeline reproduces training-time preprocessing exactly,
  API contract tests.
- `frontend/` — component and integration tests for the dashboard.
