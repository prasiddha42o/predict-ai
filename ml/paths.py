"""Canonical project paths.

Every notebook and module resolves paths through this file so that nothing
depends on the current working directory (notebooks run from `notebooks/`,
scripts run from the repo root, Docker runs from `/app`).
"""

from pathlib import Path

# ml/paths.py -> ml/ -> project root
ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
DATA_RAW = DATA / "raw"
DATA_PROCESSED = DATA / "processed"

MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
METRICS = REPORTS / "metrics"

RAW_CSV = DATA_RAW / "ai4i2020.csv"
CLEAN_PARQUET = DATA_PROCESSED / "ai4i_clean.parquet"
SPLIT_JSON = DATA_PROCESSED / "split_indices.json"

CMAPSS_RAW = DATA_RAW / "cmapss"

for _p in (DATA_RAW, DATA_PROCESSED, MODELS, FIGURES, METRICS, CMAPSS_RAW):
    _p.mkdir(parents=True, exist_ok=True)
