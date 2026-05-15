"""Metrics and the persistent experiment leaderboard.

Every model in this project is scored by exactly one function, `evaluate`, and
written to `reports/metrics/` by exactly one function, `record`. Notebook 08
then reads the directory back to build the comparison table, so no result can
end up in the table without having gone through the same evaluation code.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)

from ..paths import METRICS

#: Cost model used for threshold selection. An unplanned stoppage on a
#: production line costs roughly two orders of magnitude more than sending a
#: technician to inspect a machine that turns out to be fine. The exact ratio is
#: a business input, not a modelling one -- it is stated here so it can be
#: challenged rather than buried inside a notebook cell.
COST_FALSE_NEGATIVE = 500.0  # missed failure: unplanned downtime
COST_FALSE_POSITIVE = 10.0  # false alarm: wasted inspection


def evaluate(y_true, y_prob, threshold: float = 0.5) -> dict:
    """Full metric set for a binary classifier at a given decision threshold."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "threshold": float(threshold),
        "accuracy": float((tp + tn) / len(y_true)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "cost": float(fn * COST_FALSE_NEGATIVE + fp * COST_FALSE_POSITIVE),
    }


def threshold_for_recall(y_true, y_prob, target_recall: float = 0.90) -> float:
    """Lowest-alarm-rate threshold that still reaches `target_recall`.

    Operating point selection belongs to the business, not to sklearn's default
    of 0.5. Maintenance teams normally state a requirement as "catch at least
    90% of failures", then ask what that costs in false alarms.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    # precision_recall_curve returns len(thresholds) == len(recall) - 1
    ok = np.where(recall[:-1] >= target_recall)[0]
    if len(ok) == 0:
        return 0.0
    return float(thresholds[ok[-1]])


def threshold_for_min_cost(y_true, y_prob) -> tuple[float, float]:
    """Threshold minimising expected cost under the FN/FP cost model."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=float)
    candidates = np.unique(np.round(y_prob, 4))
    best_t, best_cost = 0.5, float("inf")
    for t in candidates:
        y_pred = (y_prob >= t).astype(int)
        fn = int(((y_true == 1) & (y_pred == 0)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        cost = fn * COST_FALSE_NEGATIVE + fp * COST_FALSE_POSITIVE
        if cost < best_cost:
            best_t, best_cost = float(t), float(cost)
    return best_t, best_cost


def record(name: str, split: str, metrics: dict, notes: str = "", **extra) -> dict:
    """Persist one experiment result to reports/metrics/<name>__<split>.json."""
    payload = {
        "model": name,
        "split": split,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": notes,
        **metrics,
        **extra,
    }
    safe = name.lower().replace(" ", "_").replace("/", "-").replace("+", "plus")
    (METRICS / f"{safe}__{split}.json").write_text(json.dumps(payload, indent=2))
    return payload


def leaderboard(split: str | None = None) -> pd.DataFrame:
    """Read every recorded experiment back into one table."""
    rows = [json.loads(p.read_text()) for p in sorted(METRICS.glob("*.json"))]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if split:
        df = df[df["split"] == split]
    cols = [
        "model",
        "split",
        "pr_auc",
        "roc_auc",
        "recall",
        "precision",
        "f1",
        "threshold",
        "fn",
        "fp",
        "cost",
        "notes",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].sort_values("pr_auc", ascending=False).reset_index(drop=True)
