# docs

Project documentation beyond the notebooks and root README.

Planned:

- `architecture.md` — system diagram: sensor simulator → message queue →
  inference service → dashboard.
- `model_cards/` — one card per production model (training data, metrics, known
  limits, intended use), sourced from `models/*/model_metadata.json`.
- API reference for the backend once it exists.
