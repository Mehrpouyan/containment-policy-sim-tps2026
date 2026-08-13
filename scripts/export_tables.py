from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def main(in_csv="results/knees.csv", out_dir="results"):
    df = pd.read_csv(in_csv)

    # Keep the paper's two scenarios and two detectors (D0 vs D1); oracle is optional
    keep = df["scenario_id"].isin(["A0_attack_only", "A1_grid_cap_plus_attack"]) & df["detector_id"].isin(["D0_weak", "D1_improved"])
    df = df.loc[keep].copy()

    # Create a compact table
    df_out = df[[
        "scenario_id", "detector_id",
        "knee_A", "knee_H",
        "knee_loss_mean", "knee_loss_cvar"
    ]].copy()

    # Friendly labels
    scen_map = {"A0_attack_only": "A0", "A1_grid_cap_plus_attack": "A1"}
    det_map = {"D0_weak": "D0\\_weak", "D1_improved": "D1\\_improved"}
    df_out["scenario"] = df_out["scenario_id"].map(scen_map)
    df_out["detector"] = df_out["detector_id"].map(det_map)

    df_out = df_out.rename(columns={
        "knee_A": "Abar",
        "knee_H": "Hbar",
        "knee_loss_mean": "loss_mean",
        "knee_loss_p90": "loss_p90",
    })[["scenario","detector","Abar","Hbar","loss_mean","loss_p90"]]

    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "frontier_shift_summary.csv")
    df_out.to_csv(csv_path, index=False)

    # Emit a LaTeX table snippet
    tex_path = os.path.join(out_dir, "frontier_shift_summary.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write("\\caption{Frontier-shift summary at the knee policy (means across seeds). Improved detection (D1) increases both $A$ and $H$ and reduces tail loss.}\n")
        f.write("\\label{tab:frontier_shift_summary}\n")
        f.write("\\begin{tabular}{llcccc}\n\\toprule\n")
        f.write("Scenario & Detector & $\\bar{A}$ & $\\bar{H}$ & loss$_{\\text{mean}}$ & loss$_{p90}$\\\\\n\\midrule\n")
        for _, r in df_out.iterrows():
            f.write(f"{r['scenario']} & {r['detector']} & {r['Abar']:.3f} & {r['Hbar']:.3f} & {r['loss_mean']:.3f} & {r['loss_p90']:.3f}\\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")

    print("Wrote:", csv_path)
    print("Wrote:", tex_path)


if __name__ == "__main__":
    main()
