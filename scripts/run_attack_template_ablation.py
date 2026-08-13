
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import HORIZON_MIN, SEEDS, DETECTORS, POLICY_BASE
from simulator import (
    PlantParams,
    DetectorParams,
    PolicyParams,
    run_cycle,
    SCENARIO_LIBRARY,
)

ATTACK_TEMPLATES = {
    "Control-plane compromise": dict(latency_mult=1.2, p_localize_mult=0.75, compute_mult=0.70, hp_mult=0.90, heat_mult=0.90),
    "Heat-control tampering": dict(latency_mult=1.2, p_localize_mult=0.80, compute_mult=1.00, hp_mult=0.65, heat_mult=0.75),
    "Management/OT DoS": dict(latency_mult=1.5, p_localize_mult=0.50, compute_mult=0.85, hp_mult=0.80, heat_mult=0.85),
    "Telemetry delay/spoofing": dict(latency_mult=1.8, p_localize_mult=0.60, compute_mult=1.00, hp_mult=1.00, heat_mult=1.00),
}

def cvar(values, alpha=0.90):
    values = np.asarray(values, dtype=float)
    q = np.quantile(values, alpha)
    return float(values[values >= q].mean())

def main():
    outdir = ROOT / "results"
    outdir.mkdir(exist_ok=True)

    base_pp = PlantParams()
    base_det = DetectorParams(**DETECTORS["D1_improved"])
    base_pol = PolicyParams(**POLICY_BASE)

    scenario = SCENARIO_LIBRARY["A0_attack_only"]
    events = scenario["events"]
    p_attack = scenario["p_attack"]

    rows = []

    for template_name, p in ATTACK_TEMPLATES.items():
        for seed in SEEDS:
            pp = PlantParams(**base_pp.__dict__)
            det = DetectorParams(**base_det.__dict__)
            pol = PolicyParams(**base_pol.__dict__)

            det.latency_min = max(1, int(round(det.latency_min * p["latency_mult"])))
            det.p_localize = min(1.0, max(0.0, det.p_localize * p["p_localize_mult"]))

            pp.P_it_max_MW *= p["compute_mult"]
            pp.P_it_demand_MW *= p["compute_mult"]
            pp.P_hp_max_MW *= p["hp_mult"]
            pp.waste_heat_eff *= p["heat_mult"]

            _, metrics = run_cycle(
                seed=int(seed),
                horizon_min=HORIZON_MIN,
                pp=pp,
                det=det,
                pol=pol,
                events=events,
                p_attack=p_attack,
            )

            rows.append({
                "template": template_name,
                "seed": seed,
                "A": metrics["A"],
                "H": metrics["H"],
                "loss": metrics["loss"],
                "breach_frac": metrics["breach_frac"],
            })

    df = pd.DataFrame(rows)

    summary = (
        df.groupby("template")
        .agg(
            A_mean=("A", "mean"),
            H_mean=("H", "mean"),
            loss_mean=("loss", "mean"),
            loss_p90=("loss", lambda x: x.quantile(0.90)),
            CVaR_0_9=("loss", cvar),
            breach_frac=("breach_frac", "mean"),
        )
        .reset_index()
    )

    summary.to_csv(outdir / "attack_template_ablation_summary.csv", index=False)
    print(summary)

if __name__ == "__main__":
    main()
