from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure repo root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from simulator import PlantParams, DetectorParams, PolicyParams, run_cycle, scenario_events  # noqa: E402


def cvar(losses: np.ndarray, alpha: float) -> float:
    losses = np.asarray(losses, dtype=float)
    q = np.quantile(losses, alpha)
    tail = losses[losses >= q]
    return float(tail.mean()) if len(tail) else float(q)


def bootstrap_ci(samples: np.ndarray, stat_fn, n_boot: int, ci: float, seed: int):
    rng = np.random.default_rng(seed)
    samples = np.asarray(samples, dtype=float)
    n = len(samples)
    stat = float(stat_fn(samples))
    boots = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[b] = float(stat_fn(samples[idx]))
    lo = float(np.quantile(boots, (1.0 - ci) / 2.0))
    hi = float(np.quantile(boots, 1.0 - (1.0 - ci) / 2.0))
    return stat, lo, hi


def pareto_filter(df: pd.DataFrame, a_col: str, h_col: str) -> pd.DataFrame:
    pts = df[[a_col, h_col]].to_numpy()
    keep = np.ones(len(df), dtype=bool)
    for i in range(len(df)):
        if not keep[i]:
            continue
        ai, hi = pts[i]
        dom = (pts[:, 0] >= ai) & (pts[:, 1] >= hi) & ((pts[:, 0] > ai) | (pts[:, 1] > hi))
        dom[i] = False
        if np.any(dom):
            keep[i] = False
    return df.loc[keep].copy()


def knee_point(front: pd.DataFrame, a_col: str, h_col: str) -> dict:
    if len(front) < 3:
        row = front.sort_values(a_col).head(1)
        return row.iloc[0].to_dict() | {"knee_distance": 0.0} if len(row) else {}

    f = front.sort_values(a_col).reset_index(drop=True)
    x = f[a_col].to_numpy()
    y = f[h_col].to_numpy()
    x1, y1 = x[0], y[0]
    x2, y2 = x[-1], y[-1]

    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    denom = np.sqrt(a * a + b * b) + 1e-12
    d = np.abs(a * x + b * y + c) / denom

    j = int(np.argmax(d))
    out = f.iloc[j].to_dict()
    out["knee_distance"] = float(d[j])
    return out


def build_detectors():
    dets = {}
    for det_id, kwargs in config.DETECTORS.items():
        dets[det_id] = DetectorParams(**kwargs)
    return dets


def build_policies():
    base = PolicyParams(**config.POLICY_BASE)

    policies = []
    # grid sweep (frontier knob)
    for alpha in config.DISPATCH_ALPHAS:
        p = PolicyParams(**{**base.__dict__, "dispatch_alpha": float(alpha)})
        policies.append((f"P_alpha{alpha:.2f}", p))

    # baselines
    for pid, overrides in config.BASELINE_POLICIES.items():
        merged = {**base.__dict__, **overrides}
        policies.append((pid, PolicyParams(**merged)))

    # de-dup by id
    seen = set()
    uniq = []
    for pid, p in policies:
        if pid not in seen:
            uniq.append((pid, p))
            seen.add(pid)
    return uniq


def main(out_dir: str, seeds: list[int], horizon_min: int):
    os.makedirs(out_dir, exist_ok=True)

    pp = PlantParams()
    dets = build_detectors()
    policies = build_policies()

    runs = []
    for scenario_id in config.SCENARIO_IDS:
        events, p_attack = scenario_events(scenario_id)
        for det_id, det in dets.items():
            for pol_id, pol in policies:
                for seed in seeds:
                    _, summ = run_cycle(
                        seed=int(seed),
                        horizon_min=int(horizon_min),
                        pp=pp,
                        det=det,
                        pol=pol,
                        events=events,
                        p_attack=float(p_attack),
                    )
                    runs.append({
                        "scenario_version": config.SCENARIO_LIBRARY_VERSION,
                        "policy_grid_version": config.POLICY_GRID_VERSION,
                        "detector_set_version": config.DETECTOR_SET_VERSION,
                        "scenario_id": scenario_id,
                        "detector_id": det_id,
                        "policy_id": pol_id,
                        "seed": int(seed),
                        "A": float(summ["A"]),
                        "H": float(summ["H"]),
                        "loss": float(summ["loss"]),
                        "loss_p90_term": float(summ.get("loss_p90_term", np.nan)),
                        "contain_frac": float(summ.get("contain_frac", np.nan)),
                        "breach_frac": float(summ.get("breach_frac", np.nan)),
                        "false_alerts": float(summ.get("false_alerts", np.nan)),
                    })

    df = pd.DataFrame(runs)
    df.to_csv(os.path.join(out_dir, "grid_runs.csv"), index=False)

    # Aggregate per (scenario, detector, policy)
    rows = []
    for (sid, did, pid), g in df.groupby(["scenario_id", "detector_id", "policy_id"], sort=False):
        A = g["A"].to_numpy()
        H = g["H"].to_numpy()
        L = g["loss"].to_numpy()

        A_mean, A_lo, A_hi = bootstrap_ci(A, np.mean, config.BOOT_N, config.BOOT_CI, config.BOOT_SEED + 1)
        H_mean, H_lo, H_hi = bootstrap_ci(H, np.mean, config.BOOT_N, config.BOOT_CI, config.BOOT_SEED + 2)
        loss_mean = float(np.mean(L))
        loss_p90 = float(np.quantile(L, 0.90))

        cvar_stat = cvar(L, config.CVAR_ALPHA)
        cvar_mean, cvar_lo, cvar_hi = bootstrap_ci(
            L,
            lambda x: cvar(x, config.CVAR_ALPHA),
            config.BOOT_N,
            config.BOOT_CI,
            config.BOOT_SEED + 3,
        )

        rows.append({
            "scenario_id": sid,
            "detector_id": did,
            "policy_id": pid,
            "n_seeds": int(len(g)),
            "A_mean": A_mean, "A_ci_lo": A_lo, "A_ci_hi": A_hi,
            "H_mean": H_mean, "H_ci_lo": H_lo, "H_ci_hi": H_hi,
            "loss_mean": loss_mean,
            "loss_p90": loss_p90,
            "loss_cvar": cvar_stat,
            "loss_cvar_ci_lo": cvar_lo,
            "loss_cvar_ci_hi": cvar_hi,
        })

    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(out_dir, "policy_summary.csv"), index=False)

    # Pareto + knee per (scenario, detector)
    pareto_rows = []
    knee_rows = []
    for (sid, did), g in summ.groupby(["scenario_id", "detector_id"], sort=False):
        front = pareto_filter(g, "A_mean", "H_mean").sort_values("A_mean").reset_index(drop=True)
        for _, r in front.iterrows():
            pareto_rows.append({
                "scenario_id": sid,
                "detector_id": did,
                "policy_id": r["policy_id"],
                "A_mean": r["A_mean"],
                "H_mean": r["H_mean"],
                "loss_mean": r["loss_mean"],
                "loss_p90": r["loss_p90"],
                "loss_cvar": r["loss_cvar"],
            })
        kp = knee_point(front, "A_mean", "H_mean")
        if kp:
            knee_rows.append({
                "scenario_id": sid,
                "detector_id": did,
                "knee_policy_id": kp["policy_id"],
                "knee_A": kp["A_mean"],
                "knee_H": kp["H_mean"],
                "knee_loss_mean": kp["loss_mean"],
                "knee_loss_p90": kp["loss_p90"],
                "knee_loss_cvar": kp["loss_cvar"],
                "knee_distance": kp["knee_distance"],
            })

    pd.DataFrame(pareto_rows).to_csv(os.path.join(out_dir, "pareto_frontiers.csv"), index=False)
    pd.DataFrame(knee_rows).to_csv(os.path.join(out_dir, "knees.csv"), index=False)

    print("Wrote:", os.path.join(out_dir, "grid_runs.csv"))
    print("Wrote:", os.path.join(out_dir, "policy_summary.csv"))
    print("Wrote:", os.path.join(out_dir, "pareto_frontiers.csv"))
    print("Wrote:", os.path.join(out_dir, "knees.csv"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--horizon_min", type=int, default=config.HORIZON_MIN)
    ap.add_argument("--seeds", type=int, default=len(config.SEEDS))
    args = ap.parse_args()

    # Use the first N seeds from config.SEEDS
    seeds = config.SEEDS[: int(args.seeds)]
    main(out_dir=args.out, seeds=seeds, horizon_min=args.horizon_min)
