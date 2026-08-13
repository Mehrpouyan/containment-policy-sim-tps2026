from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def pareto_filter(df: pd.DataFrame, a_col: str, h_col: str) -> pd.DataFrame:
    """Return nondominated points maximizing (A,H)."""
    pts = df[[a_col, h_col]].to_numpy(dtype=float)
    keep = np.ones(len(df), dtype=bool)
    for i in range(len(df)):
        if not keep[i]:
            continue
        ai, hi = pts[i]
        dominated = (pts[:, 0] >= ai) & (pts[:, 1] >= hi) & ((pts[:, 0] > ai) | (pts[:, 1] > hi))
        dominated[i] = False
        if np.any(dominated):
            keep[i] = False
    return df.loc[keep].copy()


def knee_point(front: pd.DataFrame, a_col: str, h_col: str):
    """Knee = max perpendicular distance to chord connecting endpoints."""
    if len(front) < 3:
        return None
    f = front.sort_values(a_col).reset_index(drop=True)
    x = f[a_col].to_numpy(dtype=float)
    y = f[h_col].to_numpy(dtype=float)

    x1, y1 = x[0], y[0]
    x2, y2 = x[-1], y[-1]

    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    denom = np.sqrt(a * a + b * b) + 1e-12

    d = np.abs(a * x + b * y + c) / denom
    j = int(np.argmax(d))
    return float(x[j]), float(y[j])


def main(summary_csv: str = "results/policy_summary.csv", out_dir: str = "figs"):
    summary_csv = str(summary_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(summary_csv):
        raise FileNotFoundError(f"Missing {summary_csv}. Run: python scripts/run_grid.py --out results")

    df = pd.read_csv(summary_csv)
    a_col, h_col = "A_mean", "H_mean"

    scenarios = [
        ("A0_attack_only", "A0: attack only"),
        ("A1_grid_cap_plus_attack", "A1: grid cap + attack"),
    ]
    detectors = ["D0_weak", "D1_improved", "D_oracle"]

    # Baseline policies (plot markers for all; label only 3 to avoid collisions)
    BASELINE_IDS = [
        "P_no_containment",
        "P_aggressive",
        "P_conservative",
        "P_availability_first",
        "P_heat_first",
        "P_balanced",
    ]

    baseline_label = {
        "P_no_containment": "NoContain",
        "P_aggressive": "Aggressive",
        "P_conservative": "Conservative",
        "P_availability_first": "A-first",
        "P_heat_first": "H-first",
        "P_balanced": "Balanced",
    }

    # Label only these three (clean, paper-ready)
    LABEL_IDS = {"P_no_containment", "P_aggressive", "P_availability_first"}

    # Offsets for the three labels we keep
    offsets = {
        "NoContain": (6, 6),
        "Aggressive": (6, -12),
        "A-first": (6, 6),
    }

    # Axis limits consistent across panels
    df_focus = df[df["scenario_id"].isin([s for s, _ in scenarios]) & df["detector_id"].isin(detectors)].copy()
    xmin, xmax = float(df_focus[a_col].min()), float(df_focus[a_col].max())
    ymin, ymax = float(df_focus[h_col].min()), float(df_focus[h_col].max())
    xlim = (max(0.0, xmin - 0.03), min(1.0, xmax + 0.03))
    ylim = (max(0.0, ymin - 0.03), min(1.02, ymax + 0.05))

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharex=True, sharey=True)

    for ax, (sid, title) in zip(axes, scenarios):
        ax.set_title(title)

        # Pareto frontiers + knee markers
        for det_id in detectors:
            g = df[(df["scenario_id"] == sid) & (df["detector_id"] == det_id)].copy()
            if len(g) == 0:
                continue
            front = pareto_filter(g, a_col, h_col).sort_values(a_col)
            ax.plot(front[a_col], front[h_col], marker="o", linewidth=1.8, markersize=4, label=det_id)

            kp = knee_point(front, a_col, h_col)
            if kp is not None:
                ax.scatter([kp[0]], [kp[1]], marker="X", s=90)

        # Baselines: D0 squares, D1 triangles; annotate only once using D1
        b0 = df[
            (df["scenario_id"] == sid)
            & (df["detector_id"] == "D0_weak")
            & (df["policy_id"].isin(BASELINE_IDS))
        ].copy()
        if len(b0):
            ax.scatter(b0[a_col], b0[h_col], marker="s", s=60)

        b1 = df[
            (df["scenario_id"] == sid)
            & (df["detector_id"] == "D1_improved")
            & (df["policy_id"].isin(BASELINE_IDS))
        ].copy()
        if len(b1):
            ax.scatter(b1[a_col], b1[h_col], marker="^", s=60)

            for _, r in b1.iterrows():
                pid = r["policy_id"]
                if pid not in LABEL_IDS:
                    continue
                lbl = baseline_label.get(pid, pid)
                dx, dy = offsets.get(lbl, (6, 6))
                ax.annotate(
                    lbl,
                    (float(r[a_col]), float(r[h_col])),
                    textcoords="offset points",
                    xytext=(dx, dy),
                    fontsize=9,
                    annotation_clip=True,
                )

        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_xlabel("Compute availability $A$ (mean)")
        ax.grid(True, linewidth=0.6)

    axes[0].set_ylabel("Heat service $H$ (mean)")

    # Legend: include baseline marker proxies
    proxy_d0 = Line2D([0], [0], marker="s", linestyle="None", markersize=7, label="Baselines (D0)")
    proxy_d1 = Line2D([0], [0], marker="^", linestyle="None", markersize=7, label="Baselines (D1)")
    handles, _ = axes[1].get_legend_handles_labels()
    axes[1].legend(handles=handles + [proxy_d0, proxy_d1], loc="lower left", frameon=True, title="Detector / Markers")

    out_png = out_dir / "frontier_shift_A0_A1.png"
    out_pdf = out_dir / "frontier_shift_A0_A1.pdf"
    fig.tight_layout()
    fig.savefig(out_png, dpi=250)
    fig.savefig(out_pdf)
    plt.close(fig)

    print("Wrote:", out_png)
    print("Wrote:", out_pdf)


if __name__ == "__main__":
    main()
