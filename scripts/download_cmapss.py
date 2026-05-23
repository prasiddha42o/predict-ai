"""Download the NASA C-MAPSS Turbofan Engine Degradation Simulation Data Set.

Usage:
    python scripts/download_cmapss.py

Source is NASA's Prognostics Center of Excellence data repository. If that is
unreachable, download "6. Turbofan Engine Degradation Simulation Data Set.zip"
manually from
https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
and extract the inner `CMAPSSData.zip` into `data/raw/cmapss/`.

Expected files per subset (FD001-FD004): train_FD00x.txt, test_FD00x.txt,
RUL_FD00x.txt. Notebook 07 only uses FD001 (100 train / 100 test engines,
single operating condition, one fault mode).
"""

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.paths import CMAPSS_RAW  # noqa: E402

ZIP_URL = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
)

SUBSETS = ["FD001", "FD002", "FD003", "FD004"]
# Train-engine counts per subset. NASA's readme.txt says 248 for FD004; the
# actual data file has 249 -- the file is authoritative here.
EXPECTED_ENGINES = {"FD001": 100, "FD002": 260, "FD003": 100, "FD004": 249}


def verify() -> bool:
    """Check the FD001 files match the published dataset before anything trusts them."""
    ok = True
    for subset in SUBSETS:
        train_path = CMAPSS_RAW / f"train_{subset}.txt"
        if not train_path.exists():
            print(f"  {subset}: MISSING")
            ok = False
            continue
        train = pd.read_csv(train_path, sep=r"\s+", header=None)
        n_engines = train[0].nunique()
        want = EXPECTED_ENGINES[subset]
        status = "ok" if n_engines == want else "MISMATCH"
        if n_engines != want:
            ok = False
        print(f"  {subset}: {n_engines} train engines (expected {want})  {status}")
    return ok


def main() -> int:
    if (CMAPSS_RAW / "train_FD001.txt").exists():
        print(f"Found data in {CMAPSS_RAW}")
        return 0 if verify() else 1

    print(f"Downloading from {ZIP_URL}")
    try:
        import urllib.request

        with urllib.request.urlopen(ZIP_URL, timeout=120) as r:
            outer_bytes = r.read()
        with zipfile.ZipFile(io.BytesIO(outer_bytes)) as outer:
            inner_name = next(n for n in outer.namelist() if n.endswith("CMAPSSData.zip"))
            inner_bytes = outer.read(inner_name)
        CMAPSS_RAW.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
            for name in inner.namelist():
                if name.endswith(".txt"):
                    (CMAPSS_RAW / Path(name).name).write_bytes(inner.read(name))
    except Exception as exc:  # noqa: BLE001
        print(f"\nDownload failed: {exc}")
        print(f"Download manually and extract into: {CMAPSS_RAW}")
        return 1

    print(f"Saved to {CMAPSS_RAW}")
    return 0 if verify() else 1


if __name__ == "__main__":
    raise SystemExit(main())
