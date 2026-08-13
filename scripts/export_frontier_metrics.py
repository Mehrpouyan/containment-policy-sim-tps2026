from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


SCENARIOS = [
    ("A0_attack_only", "A0"),
    ("A1_grid_cap_plus_attack", "A1"),
]
DETECTORS = [("D0_weak", "D0"), ("D1_improved", "D1")]

A_SLICE = 0.70   # best H subject to A >= 0.70
H_SLICE = 0.95   # best A subject to H >= 0.95


def hypervolume_2d_max(points: pd.DataFrame, a_col: str, h_col: str, ref=(0.0, 0.0)) -> float:
    """
    2D hypervolume for MAXIMIZATION with reference point ref=(A_ref,H_ref).
    For Pareto points in [0,1]^2 and ref=(0,0), this equals area of the dominated region.

    Implementation:
      - sort by A ascending
      - compress duplicate A by taking max H
      - build upper envelope so H is non-increasing with A
      - area = sum_{i} (A_i - prevA) * H_env_i   starting at prevA = A_ref
    """
    if points is None or len(points) == 0:
        return 0.0

    A_ref, H_ref = ref
    df = points[[a_col, h_col]].dropna().copy()
    df = df[df[a_col] >= A_ref]
    df = df[df[h_col] >= H_ref]
    if len(df) == 0:
        return 0.0

    # sort and compress duplicates in A
    df = df.sort_values(a_col)
    df = df.groupby(a_col, as_index=False)[h_col].max()

    A = df[a_col].to_numpy(dtype=float)
    H = df[h_col].to_numpy(dtype=float)

    # upper envelope (monotone step function)
    H_env = np.maximum.accumulate(H[::-1])[::-1]

    area = 0.0
    prevA = float(A_ref)
    for a, h in zip(A, H_env):
        a = float(a)
        h = float(h)
        if a <= prevA:
            continue
        area += (a - prevA) * max(0.0, h - H_ref)
        prevA = a

    return float(area)


def slice_best_H(points: pd.DataFrame, a_col: str, h_col: str, a_min: float) -> float:
    """best H subject to A >= a_min."""
    df = points[[a_col, h_col]].dropna()
    df = df[df[a_col] >= a_min]
    if len(df) == 0:
        return float("nan")
    return float(df[h_col].max())


def slice_best_A(points: pd.DataFrame, a_col: str, h_col: str, h_min: float) -> float:
    """best A subject to H >= h_min."""
    df = points[[a_col, h_col]].dropna()
    df = df[df[h_col] >= h_min]
    if len(df) == 0:
        return float("nan")
    return float(df[a_col].max())


def main(pareto_csv: str = "results/pareto_frontiers.csv", out_dir: str = "results"):
    pareto_csv = Path(pareto_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pareto_csv.exists():
        raise FileNotFoundError(f"Missing {pareto_csv}. Run: python scripts/run_grid.py --out results")

    pf = pd.read_csv(pareto_csv)

    # column robustness
    a_col = "A_mean" if "A_mean" in pf.columns else "A"
    h_col = "H_mean" if "H_mean" in pf.columns else "H"

    rows = []
    for scen_id, scen_short in SCENARIOS:
        # collect per detector
        metrics = {}
        for det_id, det_short in DETECTORS:
            pts = pf[(pf["scenario_id"] == scen_id) & (pf["detector_id"] == det_id)].copy()
            hv = hypervolume_2d_max(pts, a_col, h_col, ref=(0.0, 0.0))
            h_at = slice_best_H(pts, a_col, h_col, a_min=A_SLICE)
            a_at = slice_best_A(pts, a_col, h_col, h_min=H_SLICE)
            metrics[det_short] = dict(hv=hv, h_at=h_at, a_at=a_at)

        hv0, hv1 = metrics["D0"]["hv"], metrics["D1"]["hv"]
        dhv = hv1 - hv0

        h0, h1 = metrics["D0"]["h_at"], metrics["D1"]["h_at"]
        dh = (h1 - h0) if (np.isfinite(h0) and np.isfinite(h1)) else float("nan")

        a0, a1 = metrics["D0"]["a_at"], metrics["D1"]["a_at"]
        da = (a1 - a0) if (np.isfinite(a0) and np.isfinite(a1)) else float("nan")

        rows.append({
            "Scenario": scen_short,
            "HV_D0": hv0,
            "HV_D1": hv1,
            "dHV": dhv,
            f"H_at_Age{A_SLICE:.2f}_D0": h0,
            f"H_at_Age{A_SLICE:.2f}_D1": h1,
            f"dH_at_Age{A_SLICE:.2f}": dh,
            f"A_at_Hge{H_SLICE:.2f}_D0": a0,
            f"A_at_Hge{H_SLICE:.2f}_D1": a1,
            f"dA_at_Hge{H_SLICE:.2f}": da,
        })

    out = pd.DataFrame(rows)
    csv_path = out_dir / "frontier_shift_metrics.csv"
    out.to_csv(csv_path, index=False)

    # LaTeX table
    tex_path = out_dir / "frontier_shift_metrics.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\\begin{table}[t]\n\\centering\\small\n")
        f.write("\\caption{Quantifying frontier shift using hypervolume (HV) and slice metrics on normalized objectives. "
                "HV is computed w.r.t. reference $(0,0)$. Slice metrics report best $H$ subject to $A\\geq %.2f$ and best $A$ subject to $H\\geq %.2f$.}\n"
                % (A_SLICE, H_SLICE))
        f.write("\\label{tab:frontier_shift_metrics}\n")
        f.write("\\begin{tabular}{lccc ccc ccc}\n")
        f.write("\\toprule\n")
        f.write("Scenario & HV(D0) & HV(D1) & $\\Delta$HV & "
                "$H|_{A\\geq %.2f}$ (D0) & (D1) & $\\Delta H$ & "
                "$A|_{H\\geq %.2f}$ (D0) & (D1) & $\\Delta A$\\\\\n"
                % (A_SLICE, H_SLICE))
        f.write("\\midrule\n")
        for _, r in out.iterrows():
            f.write(
                f"{r['Scenario']} & "
                f"{r['HV_D0']:.3f} & {r['HV_D1']:.3f} & {r['dHV']:.3f} & "
                f"{r[f'H_at_Age{A_SLICE:.2f}_D0']:.3f} & {r[f'H_at_Age{A_SLICE:.2f}_D1']:.3f} & {r[f'dH_at_Age{A_SLICE:.2f}']:.3f} & "
                f"{r[f'A_at_Hge{H_SLICE:.2f}_D0']:.3f} & {r[f'A_at_Hge{H_SLICE:.2f}_D1']:.3f} & {r[f'dA_at_Hge{H_SLICE:.2f}']:.3f}\\\\\n"
            )
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")

    print("Wrote:", csv_path)
    print("Wrote:", tex_path)


if __name__ == "__main__":
    main()
