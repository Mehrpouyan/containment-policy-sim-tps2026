from __future__ import annotations

import os
import sys
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))

def main():
    os.makedirs(ROOT / "results", exist_ok=True)
    os.makedirs(ROOT / "figs", exist_ok=True)

    run([sys.executable, "scripts/run_grid.py", "--out", "results"])
    run([sys.executable, "scripts/plot_frontier_panels.py"])
    run([sys.executable, "scripts/export_tables.py"])
    run([sys.executable, "scripts/export_baselines.py"])

    print("[OK] All outputs generated.")
    print(" - figs/frontier_shift_A0_A1.png/.pdf")
    print(" - results/frontier_shift_summary.tex/.csv")
    print(" - results/baselines_A0.tex, results/baselines_A1.tex")
    print(" - results/grid_runs.csv, policy_summary.csv, pareto_frontiers.csv, knees.csv")

if __name__ == "__main__":
    main()
