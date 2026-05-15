"""Download the AI4I 2020 Predictive Maintenance Dataset.

Usage:
    python scripts/download_data.py

Primary source is the UCI Machine Learning Repository. If that is unreachable,
download `ai4i2020.csv` manually from
https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
and place it at `data/raw/ai4i2020.csv`.

Expected file: 10,000 rows, 14 columns, 339 machine failures.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.paths import RAW_CSV  # noqa: E402

UCI_URL = (
    "https://archive.ics.uci.edu/static/public/601/"
    "ai4i+2020+predictive+maintenance+dataset.zip"
)

EXPECTED_ROWS = 10_000
EXPECTED_FAILURES = 339
EXPECTED_COLUMNS = 14


def verify(path: Path) -> bool:
    """Check the file matches the published dataset before anything trusts it."""
    df = pd.read_csv(path)
    checks = {
        "rows": (len(df), EXPECTED_ROWS),
        "columns": (df.shape[1], EXPECTED_COLUMNS),
        "failures": (int(df["Machine failure"].sum()), EXPECTED_FAILURES),
    }
    ok = True
    for name, (got, want) in checks.items():
        status = "ok" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  {name:9s} {got:>6,}  (expected {want:,})  {status}")
    return ok


def main() -> int:
    if RAW_CSV.exists():
        print(f"Found {RAW_CSV}")
        return 0 if verify(RAW_CSV) else 1

    print(f"Downloading from {UCI_URL}")
    try:
        import io
        import zipfile
        import urllib.request

        with urllib.request.urlopen(UCI_URL, timeout=60) as r:
            payload = r.read()
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            name = next(n for n in z.namelist() if n.endswith(".csv"))
            RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
            RAW_CSV.write_bytes(z.read(name))
    except Exception as exc:  # noqa: BLE001
        print(f"\nDownload failed: {exc}")
        print(f"Download manually and save to: {RAW_CSV}")
        print("https://archive.ics.uci.edu/dataset/601/"
              "ai4i+2020+predictive+maintenance+dataset")
        return 1

    print(f"Saved to {RAW_CSV}")
    return 0 if verify(RAW_CSV) else 1


if __name__ == "__main__":
    raise SystemExit(main())
