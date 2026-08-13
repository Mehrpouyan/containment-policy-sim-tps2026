
import os, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def plot_frontiers(out_dir: str = "results"):
    out_dir = str(ROOT/out_dir)
    summ = pd.read_csv(os.path.join(out_dir, "policy_summary.csv"))
    pareto = pd.read_csv(os.path.join(out_dir, "pareto_frontiers.csv"))
    knees = pd.read_csv(os.path.join(out_dir, "knees.csv"))

    for (sid, det_id), g in summ.groupby(["scenario_id","detector_id"]):
        gP = pareto[(pareto["scenario_id"] == sid) & (pareto["detector_id"] == det_id)]
        gK = knees[(knees["scenario_id"] == sid) & (knees["detector_id"] == det_id)]

        fig = plt.figure()
        ax = plt.gca()

        ax.errorbar(
            g["A_mean"], g["H_mean"],
            xerr=[g["A_mean"] - g["A_ci_lo"], g["A_ci_hi"] - g["A_mean"]],
            yerr=[g["H_mean"] - g["H_ci_lo"], g["H_ci_hi"] - g["H_mean"]],
            fmt="o", markersize=3, capsize=2, linewidth=0.8
        )

        ax.plot(gP["A_mean"], gP["H_mean"], marker="o", linestyle="-", linewidth=1.5)

        if len(gK) == 1:
            knee_pid = gK["knee_policy_id"].iloc[0]
            kp = g[g["policy_id"] == knee_pid]
            if len(kp) == 1:
                ax.scatter(kp["A_mean"], kp["H_mean"], marker="X", s=80)

        ax.set_xlabel("Compute availability A (mean)")
        ax.set_ylabel("Heat service H (mean)")
        ax.set_title(f"{sid} / {det_id}")
        ax.set_xlim(0.0, 1.01)
        ax.set_ylim(0.0, 1.01)

        out_path = os.path.join(out_dir, f"frontier_{sid}_{det_id}.png")
        fig.tight_layout()
        fig.savefig(out_path, dpi=200)
        plt.close(fig)

if __name__ == "__main__":
    plot_frontiers("results")
    print("Wrote frontier_*.png into results/")
