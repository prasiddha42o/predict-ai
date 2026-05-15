# backend

FastAPI inference service. Not yet implemented — the project is still in the ML
research phase (see root [README](../README.md)).

Planned responsibilities once the notebooks in `notebooks/05`–`10` land a selected
model:

- Load `models/*/model.json` + `feature_config.json` and reproduce the exact
  preprocessing pipeline from `ml/preprocessing/` — no re-derivation of feature
  logic in application code.
- Serve failure probability, anomaly score, and RUL predictions over REST.
- Stream simulated sensor readings and live predictions over WebSockets.
- Persist alerts and maintenance history to PostgreSQL/Supabase.

Target stack: FastAPI, PostgreSQL/Supabase, Redis.
