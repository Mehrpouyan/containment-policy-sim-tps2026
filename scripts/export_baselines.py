from __future__ import annotations

from pathlib import Path
import pandas as pd


BASELINE_IDS = [
    "P_no_containment",
    "P_aggressive",
    "P_conservative",
    "P_availability_first",
    "P_heat_first",
    "P_balanced",
]

BASELINE_NAME = {
    "P_no_containment": "NoContain",
    "P_aggressive": "Aggressive",
    "P_conservative": "Conservative",
    "P_availability_first": "A-first",
    "P_heat_first": "H-first",
    "P_balanced": "Balanced",
}

SCENARIOS = [
    ("A0_attack_only", "A0"),
    ("A1_grid_cap_plus_attack", "A1"),
]

DET_ORDER = ["D0_weak", "D1_improved"]
BASELINE_ORDER = ["NoContain", "Aggressive", "Conservative", "A-first", "H-first", "Balanced"]


def _write_table(df_out: pd.DataFrame, tex_path: Path, caption: str, label: str):
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\\begin{table}[t]\n")
        f.write("\\centering\\scriptsize\n")
        f.write(f"\\caption{{{caption}}}\n")
        f.write(f"\\label{{{label}}}\n")
        f.write("\\begin{tabular}{llccccc}\n")
        f.write("\\toprule\n")
        f.write("Detector & Baseline & $\\bar{A}$ & $\\bar{H}$ & loss$_{\\text{mean}}$ & loss$_{p90}$ & CVaR$_{0.9}$\\\\\n")
        f.write("\\midrule\n")
        for _, r in df_out.iterrows():
            det = str(r["Detector"]).replace("_", "\\_")
            base = str(r["Baseline"]).replace("_", "\\_")
            f.write(
                f"{det} & {base} & {r['A_mean']:.3f} & {r['H_mean']:.3f} & "
                f"{r['loss_mean']:.3f} & {r['loss_p90']:.3f} & {r['loss_cvar']:.3f}\\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")


def main(summary_csv: str = "results/policy_summary.csv", out_dir: str = "results"):
    summary_csv = Path(summary_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing {summary_csv}. Run: python scripts/run_grid.py --out results")

    df = pd.read_csv(summary_csv)

    df = df[
        df["scenario_id"].isin([s for s, _ in SCENARIOS])
        & df["detector_id"].isin(DET_ORDER)
        & df["policy_id"].isin(BASELINE_IDS)
    ].copy()

    if len(df) == 0:
        raise RuntimeError("No baseline rows found. Ensure BASELINE_POLICIES exist in config.py and rerun run_grid.py.")

    df["Scenario"] = df["scenario_id"].map({s: short for s, short in SCENARIOS})
    df["Detector"] = df["detector_id"]
    df["Baseline"] = df["policy_id"].map(BASELINE_NAME)

    out = df[[
        "Scenario", "Detector", "Baseline",
        "A_mean", "H_mean", "loss_mean", "loss_p90", "loss_cvar",
        "loss_cvar_ci_lo", "loss_cvar_ci_hi",
    ]].copy()

    out["Detector"] = pd.Categorical(out["Detector"], categories=DET_ORDER, ordered=True)
    out["Baseline"] = pd.Categorical(out["Baseline"], categories=BASELINE_ORDER, ordered=True)
    out = out.sort_values(["Scenario", "Detector", "Baseline"]).reset_index(drop=True)

    # CSV for reference
    csv_path = out_dir / "baseline_summary.csv"
    out.to_csv(csv_path, index=False)

    # Two one-column LaTeX tables
    for scen_id, scen_short in SCENARIOS:
        df_s = out[out["Scenario"] == scen_short].copy()
        tex_path = out_dir / f"baselines_{scen_short}.tex"
        caption = f"Baseline containment policies under {scen_short} (means across seeds)."
        label = f"tab:baselines_{scen_short.lower()}"
        _write_table(df_s, tex_path, caption, label)

    print("Wrote:", csv_path)
    print("Wrote:", out_dir / "baselines_A0.tex")
    print("Wrote:", out_dir / "baselines_A1.tex")


if __name__ == "__main__":
    main()
