
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SCENARIOS = ["A0_attack_only", "A1_grid_cap_plus_attack"]
DETECTORS = ["D0_weak", "D1_improved"]  # extend if you want oracle too

def hv_2d_max(points: pd.DataFrame, a_col="A_mean", h_col="H_mean") -> float:
    """
    2D hypervolume for maximization objectives (A,H) w.r.t reference (0,0).
    Assumes points are Pareto-ish. We enforce an upper envelope to be safe.

    HV = area of union of rectangles [0,A]x[0,H] over all points.
    For a monotone frontier, HV = sum_i (A_i - A_{i-1}) * H_i (after envelope).
    """
    if points.empty:
        return 0.0

    pts = points[[a_col, h_col]].dropna().copy()
    pts = pts.sort_values(a_col).drop_duplicates(subset=[a_col], keep="last")
    A = pts[a_col].to_numpy()
    H = pts[h_col].to_numpy()

    # Upper envelope from the right: ensure H is non-increasing as A increases
    H_env = np.maximum.accumulate(H[::-1])[::-1]

    hv = 0.0
    prev_a = 0.0
    for a, h in zip(A, H_env):
        a = float(np.clip(a, 0.0, 1.0))
        h = float(np.clip(h, 0.0, 1.0))
        if a > prev_a:
            hv += (a - prev_a) * h
            prev_a = a
    return float(hv)

def slice_best_H(points: pd.DataFrame, a_thresh: float, a_col="A_mean", h_col="H_mean") -> float:
    pts = points[[a_col, h_col]].dropna()
    pts = pts[pts[a_col] >= a_thresh]
    return float(pts[h_col].max()) if not pts.empty else float("nan")

def slice_best_A(points: pd.DataFrame, h_thresh: float, a_col="A_mean", h_col="H_mean") -> float:
    pts = points[[a_col, h_col]].dropna()
    pts = pts[pts[h_col] >= h_thresh]
    return float(pts[a_col].max()) if not pts.empty else float("nan")

def to_tex(df: pd.DataFrame, out_path: Path):
    # Format for LaTeX table body (you can wrap with your own \begin{table})
    # Columns: Scenario, HV(D0), HV(D1), ΔHV, H|A>=0.70 D0/D1/Δ, A|H>=0.95 D0/D1/Δ
    lines = []
    for _, r in df.iterrows():
        lines.append(
            f"{r['Scenario']} & "
            f"{r['HV_D0']:.3f} & {r['HV_D1']:.3f} & {r['dHV']:.3f} & "
            f"{r['H_Age070_D0']:.3f} & {r['H_Age070_D1']:.3f} & {r['dH_Age070']:.3f} & "
            f"{r['A_Hge095_D0']:.3f} & {r['A_Hge095_D1']:.3f} & {r['dA_Hge095']:.3f} \\\\"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pareto", default="results/pareto_frontiers.csv")
    ap.add_argument("--out_csv", default="results/frontier_shift_metrics.csv")
    ap.add_argument("--out_tex", default="results/frontier_shift_metrics.tex")
    ap.add_argument("--a_thresh", type=float, default=0.70)
    ap.add_argument("--h_thresh", type=float, default=0.95)
    args = ap.parse_args()

    pareto = pd.read_csv(args.pareto)
    rows = []

    for scen in SCENARIOS:
        sub = pareto[pareto["scenario_id"] == scen].copy()

        # D0
        p0 = sub[sub["detector_id"] == "D0_weak"]
        hv0 = hv_2d_max(p0)
        h0 = slice_best_H(p0, args.a_thresh)
        a0 = slice_best_A(p0, args.h_thresh)

        # D1
        p1 = sub[sub["detector_id"] == "D1_improved"]
        hv1 = hv_2d_max(p1)
        h1 = slice_best_H(p1, args.a_thresh)
        a1 = slice_best_A(p1, args.h_thresh)

        rows.append(dict(
            Scenario="A0" if scen.startswith("A0") else "A1",
            HV_D0=hv0, HV_D1=hv1, dHV=hv1-hv0,
            H_Age070_D0=h0, H_Age070_D1=h1, dH_Age070=h1-h0,
            A_Hge095_D0=a0, A_Hge095_D1=a1, dA_Hge095=a1-a0,
        ))

    df = pd.DataFrame(rows)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    to_tex(df, Path(args.out_tex))

    print(f"Wrote: {args.out_csv}")
    print(f"Wrote: {args.out_tex}")
    print(df)

if __name__ == "__main__":
    main()
