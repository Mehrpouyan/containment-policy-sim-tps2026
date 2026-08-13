from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure repository root is importable when this file is run from scripts/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from simulator import (  # noqa: E402
    PlantParams,
    DetectorParams,
    PolicyParams,
    run_cycle,
    scenario_events,
)


def cvar(values: np.ndarray, alpha: float = 0.90) -> float:
    """Empirical CVaR using the same >= quantile-tail convention as run_grid.py."""
    values = np.asarray(values, dtype=float)
    q = np.quantile(values, alpha)
    tail = values[values >= q]
    return float(tail.mean()) if len(tail) else float(q)


def evaluate_policy(overrides: dict) -> tuple[float, float, float]:
    """
    Evaluate one policy variant under the frozen publication configuration.

    Fixed experiment:
      - scenario: A0_attack_only
      - detector: D1_improved
      - seeds: config.SEEDS
      - horizon: config.HORIZON_MIN
      - plant: default PlantParams
      - policy: config.POLICY_BASE plus one-at-a-time overrides
    """
    pp = PlantParams()
    det = DetectorParams(**config.DETECTORS["D1_improved"])

    policy_kwargs = {**config.POLICY_BASE, **overrides}
    pol = PolicyParams(**policy_kwargs)

    events, p_attack = scenario_events("A0_attack_only")

    rows = []
    for seed in config.SEEDS:
        _, metrics = run_cycle(
            seed=int(seed),
            horizon_min=int(config.HORIZON_MIN),
            pp=pp,
            det=det,
            pol=pol,
            events=events,
            p_attack=float(p_attack),
        )
        rows.append(
            {
                "A": float(metrics["A"]),
                "H": float(metrics["H"]),
                "loss": float(metrics["loss"]),
            }
        )

    df = pd.DataFrame(rows)
    return (
        float(df["A"].mean()),
        float(df["H"].mean()),
        cvar(df["loss"].to_numpy(), config.CVAR_ALPHA),
    )


def main(out_path: str) -> None:
    # Baseline used for all delta calculations.
    base_A, base_H, base_CVaR = evaluate_policy({})

    # One-at-a-time perturbations reconstructed from the archived
    # policy_parameter_sensitivity result.
    perturbations = [
        ("alert threshold -1", {"alert_threshold": config.POLICY_BASE["alert_threshold"] - 1}),
        ("alert threshold +1", {"alert_threshold": config.POLICY_BASE["alert_threshold"] + 1}),
        (
            "escalation delay -4",
            {"escalation_delay_min": config.POLICY_BASE["escalation_delay_min"] - 4},
        ),
        (
            "escalation delay +4",
            {"escalation_delay_min": config.POLICY_BASE["escalation_delay_min"] + 4},
        ),
        (
            "coarse isolation -0.10",
            {"isolate_coarse": config.POLICY_BASE["isolate_coarse"] - 0.10},
        ),
        (
            "coarse isolation +0.10",
            {"isolate_coarse": config.POLICY_BASE["isolate_coarse"] + 0.10},
        ),
        (
            "throttle level -0.10",
            {"throttle_level": config.POLICY_BASE["throttle_level"] - 0.10},
        ),
        (
            "throttle level +0.10",
            {"throttle_level": config.POLICY_BASE["throttle_level"] + 0.10},
        ),
        ("contain min -10", {"contain_min": config.POLICY_BASE["contain_min"] - 10}),
        ("contain min +10", {"contain_min": config.POLICY_BASE["contain_min"] + 10}),
        ("recover min -20", {"recover_min": config.POLICY_BASE["recover_min"] - 20}),
        ("recover min +20", {"recover_min": config.POLICY_BASE["recover_min"] + 20}),
    ]

    rows = []
    for label, overrides in perturbations:
        A_mean, H_mean, cvar_09 = evaluate_policy(overrides)
        rows.append(
            {
                "ablation": label,
                "A_mean": A_mean,
                "H_mean": H_mean,
                "CVaR_0_9": cvar_09,
                "delta_A": A_mean - base_A,
                "delta_H": H_mean - base_H,
                "delta_CVaR": cvar_09 - base_CVaR,
            }
        )

    out = Path(out_path)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    result = pd.DataFrame(
        rows,
        columns=[
            "ablation",
            "A_mean",
            "H_mean",
            "CVaR_0_9",
            "delta_A",
            "delta_H",
            "delta_CVaR",
        ],
    )
    result.to_csv(out, index=False)

    print(
        "Baseline: "
        f"A={base_A:.15f}, "
        f"H={base_H:.15f}, "
        f"CVaR_0.9={base_CVaR:.15f}"
    )
    print(result.to_string(index=False))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the one-at-a-time containment-policy sensitivity "
            "analysis used in the IEEE TPS 2026 artifact."
        )
    )
    parser.add_argument(
        "--out",
        default="results/policy_parameter_sensitivity.csv",
        help="Output CSV path relative to repository root.",
    )
    args = parser.parse_args()
    main(args.out)
