"""Consistent figure styling across every notebook."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

from .paths import FIGURES

# Colour-blind safe, high contrast, and stable across notebooks so that
# "failure" is the same colour everywhere in the final report.
OK = "#2a9d8f"
WARN = "#e9c46a"
BAD = "#e76f51"
NEUTRAL = "#264653"
ACCENT = "#5c6bc0"

PALETTE = [NEUTRAL, BAD, OK, WARN, ACCENT]


def set_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "figure.figsize": (9, 4.5),
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "legend.frameon": False,
            "grid.alpha": 0.3,
        }
    )


def save_fig(name: str, fig=None, tight: bool = True) -> None:
    """Save to reports/figures/<name>.png for reuse in the README and report."""
    fig = fig or plt.gcf()
    if tight:
        fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight")
