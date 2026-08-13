from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd


# ============================================================
# Parameters (match your existing API/tests)
# ============================================================

@dataclass
class PlantParams:
    # Electrical (MW)
    P_it_max_MW: float = 60.0          # IT max draw
    P_grid_nom_MW: float = 70.0        # nominal grid limit
    P_base_MW: float = 6.0             # non-flex base load

    # Heat conversion
    waste_heat_eff: float = 0.75       # MW_th per MW IT (useful export)
    hp_COP: float = 3.2                # MW_th per MW_e
    P_hp_max_MW: float = 14.0          # heat pump electrical cap (MW_e)

    # Thermal storage
    E_store_max_MWh: float = 120.0     # thermal storage capacity
    P_store_MW: float = 20.0           # max charge/discharge rate (MW_th)
    E_store_init_MWh: float = 60.0     # initial energy

    # Demand profiles (baseline)
    P_it_demand_MW: float = 55.0       # baseline compute demand (MW)
    Q_heat_base_MW: float = 44.0       # baseline heat demand (MW_th)
    Q_heat_peak_add_MW: float = 18.0   # added heat during peak window (MW_th)
    peak_start_hour: int = 17
    peak_end_hour: int = 21


@dataclass
class DetectorParams:
    tpr: float = 0.7
    # NOTE: fpr is interpreted as "false alerts per hour" (approx), but we cap it per-minute.
    fpr: float = 0.02
    latency_min: int = 5
    p_localize: float = 0.8


@dataclass
class PolicyParams:
    # alert logic
    alert_window_min: int = 10
    alert_threshold: int = 3
    escalation_delay_min: int = 8

    # response intensity
    throttle_level: float = 0.8
    isolate_fine: float = 0.1
    isolate_coarse: float = 0.3

    contain_min: int = 20
    recover_min: int = 40
    stable_min: int = 15

    # dispatch knob for frontier (0=heat first, 1=compute first)
    dispatch_alpha: float = 0.75


# ============================================================
# Scenario library (used by run_grid.py)
# ============================================================

SCENARIO_LIBRARY: Dict[str, Dict[str, Any]] = {
    "S0_nominal": dict(p_attack=0.0, events=[]),
    "S1_grid_cap": dict(
        p_attack=0.0,
        events=[{"type": "grid_cap_peak", "params": {"mult": 0.78}}]
    ),
    "S2_hp_cap_peak": dict(
        p_attack=0.0,
        events=[{"type": "hp_cap_peak", "params": {"mult": 0.60}}]
    ),
    "A0_attack_only": dict(p_attack=1.0, events=[]),
    "A1_grid_cap_plus_attack": dict(
        p_attack=1.0,
        events=[{"type": "grid_cap_peak", "params": {"mult": 0.78}}]
    ),
}

def scenario_events(scenario_id: str) -> Tuple[List[Dict[str, Any]], float]:
    cfg = SCENARIO_LIBRARY[scenario_id]
    return cfg["events"], cfg["p_attack"]


# ============================================================
# Core helpers
# ============================================================

def _is_peak(minute: int, pp: PlantParams) -> bool:
    h = (minute // 60) % 24
    return (h >= pp.peak_start_hour) and (h < pp.peak_end_hour)

def _heat_demand(minute: int, pp: PlantParams) -> float:
    q = pp.Q_heat_base_MW
    if _is_peak(minute, pp):
        q += pp.Q_heat_peak_add_MW
    return q

def _grid_cap(minute: int, pp: PlantParams, events: List[Dict[str, Any]]) -> float:
    cap = pp.P_grid_nom_MW
    for ev in events:
        if ev["type"] == "grid_cap":
            cap = min(cap, float(ev["params"]["P_grid_max_MW"]))
        elif ev["type"] == "grid_cap_peak":
            if _is_peak(minute, pp):
                cap = min(cap, pp.P_grid_nom_MW * float(ev["params"]["mult"]))
    return cap

def _hp_cap(minute: int, pp: PlantParams, events: List[Dict[str, Any]]) -> float:
    cap = pp.P_hp_max_MW
    for ev in events:
        if ev["type"] == "hp_cap":
            cap = min(cap, float(ev["params"]["P_hp_max_MW"]))
        elif ev["type"] == "hp_cap_peak":
            if _is_peak(minute, pp):
                cap = min(cap, pp.P_hp_max_MW * float(ev["params"]["mult"]))
    return cap

def _mean_service(served: np.ndarray, demand: np.ndarray, eps: float = 1e-12) -> float:
    served = np.maximum(np.nan_to_num(served, nan=0.0), 0.0)
    demand = np.maximum(np.nan_to_num(demand, nan=0.0), 0.0)
    mask = demand > eps
    if not np.any(mask):
        return 1.0
    return float(np.clip(np.mean(served[mask] / demand[mask]), 0.0, 1.0))


# ============================================================
# Attack + detector + containment policy (FIXED)
# ============================================================

def _simulate_attack_tape(rng: np.random.Generator, horizon_min: int, p_attack: float):
    # attack states: 0 none, 1 initial, 2 persistent, 3 disruptive
    attack = np.zeros(horizon_min, dtype=int)
    if rng.random() >= p_attack:
        return attack

    start = int(rng.integers(low=60, high=max(61, min(horizon_min - 1, 6 * 60))))
    stage_len = 75  # minutes per stage (slightly faster escalation than before)
    for t in range(start, horizon_min):
        dt = t - start
        stage = 1 + dt // stage_len
        attack[t] = int(min(stage, 3))
    return attack

def _alerts_from_detector(rng: np.random.Generator, attack_state: int, det: DetectorParams) -> bool:
    # Interpret fpr as approx false alerts per hour -> per-minute probability, but cap to avoid runaway false containment
    p_fp = min(0.0015, float(det.fpr) / 60.0)  # <= 0.15% per minute

    if attack_state == 0:
        return rng.random() < p_fp

    # True-positive hazard tied to latency and TPR; stronger stages more detectable
    p_tp = min(1.0, float(det.tpr) / max(1.0, float(det.latency_min)))
    if attack_state == 2:
        p_tp = min(1.0, p_tp * 1.35)
    if attack_state == 3:
        p_tp = min(1.0, p_tp * 1.75)
    return rng.random() < p_tp

def _policy_step(
    t: int,
    alert_hist: np.ndarray,
    pol: PolicyParams,
    rng: np.random.Generator,
    det: DetectorParams,
    state: str,
    state_left: int,
    attack_state: int,
):
    # State machine:
    # NORMAL -> THROTTLE -> ISOLATE_(FINE/COARSE) -> RECOVER -> STABLE -> NORMAL

    # count alerts in window
    w = pol.alert_window_min
    start = max(0, t - w + 1)
    n_alerts = int(alert_hist[start:t + 1].sum())

    if state == "NORMAL":
        if n_alerts >= pol.alert_threshold:
            return "THROTTLE", pol.escalation_delay_min
        return state, state_left

    if state == "THROTTLE":
        if state_left > 1:
            return state, state_left - 1

        # localization is more likely for real incidents and better detectors; reduces coarse-isolation harm
        fine_prob = float(det.p_localize)
        if attack_state >= 2:
            fine_prob = min(1.0, fine_prob + 0.20)
        fine = (rng.random() < fine_prob)
        return ("ISOLATE_FINE" if fine else "ISOLATE_COARSE"), pol.contain_min

    if state in ("ISOLATE_FINE", "ISOLATE_COARSE"):
        if state_left > 1:
            return state, state_left - 1
        return "RECOVER", pol.recover_min

    if state == "RECOVER":
        if state_left > 1:
            return state, state_left - 1
        return "STABLE", pol.stable_min

    if state == "STABLE":
        if state_left > 1:
            return state, state_left - 1
        return "NORMAL", 0

    return "NORMAL", 0


# ============================================================
# Main simulation (minute step)
# ============================================================

def run_cycle(
    seed: int,
    horizon_min: int,
    pp: PlantParams,
    det: DetectorParams,
    pol: PolicyParams,
    events: Optional[List[Dict[str, Any]]] = None,
    p_attack: float = 0.0,
) -> Tuple[pd.DataFrame, Dict[str, float]]:

    rng = np.random.default_rng(seed)
    events = events or []

    dt_h = 1.0 / 60.0

    # exogenous baseline demands (used for A/H denominators)
    compute_demand = np.full(horizon_min, pp.P_it_demand_MW, dtype=float)
    heat_demand = np.array([_heat_demand(t, pp) for t in range(horizon_min)], dtype=float)

    # scenario caps
    grid_cap = np.array([_grid_cap(t, pp, events) for t in range(horizon_min)], dtype=float)
    hp_cap = np.array([_hp_cap(t, pp, events) for t in range(horizon_min)], dtype=float)

    # attack tape
    attack_state = _simulate_attack_tape(rng, horizon_min, p_attack)

    # logs
    P_it = np.zeros(horizon_min)
    P_hp = np.zeros(horizon_min)
    Q_served = np.zeros(horizon_min)
    storage = np.zeros(horizon_min)
    state_log = np.empty(horizon_min, dtype=object)
    alerts = np.zeros(horizon_min, dtype=int)

    E = float(pp.E_store_init_MWh)

    state = "NORMAL"
    state_left = 0

    contain_minutes = 0
    false_alerts = 0
    breach_minutes = 0

    for t in range(horizon_min):
        a = int(attack_state[t])

        # detection
        alarm = _alerts_from_detector(rng, a, det)
        alerts[t] = 1 if alarm else 0
        if alarm and a == 0:
            false_alerts += 1

        # policy update (NOTE: pass attack_state to improve fine isolation under real incidents)
        state, state_left = _policy_step(t, alerts, pol, rng, det, state, state_left, a)
        state_log[t] = state

        contained = (state != "NORMAL")
        if contained:
            contain_minutes += 1

        # -----------------------------------------------
        # FIXED: Attack now imposes meaningful damage when not contained,
        # so better detection (earlier containment) improves outcomes.
        # -----------------------------------------------
        extra_base = 0.0
        grid_mult = 1.0
        heat_mult = 1.0
        it_drop_mult = 1.0

        if (a >= 1) and (not contained):
            extra_base += 2.5

        if (a >= 2) and (not contained):
            grid_mult *= 0.80
            it_drop_mult *= 0.90

        if (a >= 3) and (not contained):
            grid_mult *= 0.75
            heat_mult *= 0.55
            it_drop_mult *= 0.80

        # available electrical power
        P_grid = grid_cap[t] * grid_mult
        P_avail = max(0.0, P_grid - (pp.P_base_MW + extra_base))

        # dispatch knob: alpha share to compute, (1-alpha) share to HP
        alpha = float(np.clip(pol.dispatch_alpha, 0.0, 1.0))

        # response multipliers (containment costs)
        compute_mult = 1.0
        if state == "THROTTLE":
            compute_mult *= pol.throttle_level
        elif state == "ISOLATE_FINE":
            compute_mult *= (1.0 - pol.isolate_fine)
        elif state == "ISOLATE_COARSE":
            compute_mult *= (1.0 - pol.isolate_coarse)
        elif state == "RECOVER":
            # ramp back to 1
            frac = 1.0 - (state_left / max(1.0, float(pol.recover_min)))
            compute_mult *= float(np.clip(frac, 0.0, 1.0))
        elif state == "STABLE":
            compute_mult *= 1.0

        # apply disruptive drop (only non-contained)
        compute_mult *= it_drop_mult

        # allocate budgets
        P_it_budget = alpha * P_avail
        P_hp_budget = (1.0 - alpha) * P_avail

        # compute served
        P_it[t] = min(pp.P_it_max_MW, compute_demand[t] * compute_mult, P_it_budget)

        # hp served
        P_hp[t] = min(hp_cap[t], P_hp_budget)

        # if leftover power exists, fill compute up to demand
        leftover = P_avail - (P_it[t] + P_hp[t])
        if leftover > 1e-9:
            add = min(leftover, max(0.0, compute_demand[t] * compute_mult - P_it[t]))
            P_it[t] += add

        # heat supply (waste + hp)
        Q_waste = pp.waste_heat_eff * P_it[t] * heat_mult
        Q_hp = pp.hp_COP * P_hp[t]
        Q_total = Q_waste + Q_hp

        # storage dynamics
        demand = heat_demand[t]
        if Q_total >= demand:
            served = demand
            surplus = Q_total - demand
            charge_MW = min(surplus, pp.P_store_MW, max(0.0, (pp.E_store_max_MWh - E) / dt_h))
            E += charge_MW * dt_h
        else:
            deficit = demand - Q_total
            discharge_MW = min(deficit, pp.P_store_MW, max(0.0, E / dt_h))
            E -= discharge_MW * dt_h
            served = Q_total + discharge_MW

        Q_served[t] = served
        storage[t] = E

        # "breach" minutes: worst-stage attack not contained
        if (a >= 3) and (not contained):
            breach_minutes += 1

    # metrics: use baseline demands (not post-policy "requested")
    A = _mean_service(P_it, compute_demand)
    H = _mean_service(Q_served, heat_demand)

    # loss includes service loss + containment fraction + breach penalty + (small) false-alarm penalty
    loss = (
        (1.0 - A)
        + 1.2 * (1.0 - H)
        + 0.10 * (contain_minutes / horizon_min)
        + 0.35 * (breach_minutes / horizon_min)
        + 0.002 * false_alerts
    )

    df = pd.DataFrame({
        "t_min": np.arange(horizon_min),
        "P_it": P_it,
        "P_hp": P_hp,
        "Q_served": Q_served,
        "Q_demand": heat_demand,
        "P_demand": compute_demand,
        "grid_cap": grid_cap,
        "hp_cap": hp_cap,
        "attack_state": attack_state,
        "alert": alerts,
        "state": state_log,
        "E_store": storage,
    })

    summ = {
        "A": float(A),
        "H": float(H),
        "loss": float(loss),
        "contain_frac": float(contain_minutes / horizon_min),
        "false_alerts": float(false_alerts),
        "breach_frac": float(breach_minutes / horizon_min),
    }
    return df, summ
