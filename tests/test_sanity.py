import numpy as np
from simulator import run_cycle, PlantParams, DetectorParams, PolicyParams

def test_no_attack_near_zero_loss():
    pp = PlantParams()
    det = DetectorParams(tpr=0.7, fpr=0.0, latency_min=5, p_localize=0.8)
    pol = PolicyParams(
        alert_window_min=10, alert_threshold=3, escalation_delay_min=8,
        throttle_level=0.8, isolate_fine=0.1, isolate_coarse=0.3,
        contain_min=20, recover_min=40, stable_min=15
    )
    df, summ = run_cycle(
        seed=1, horizon_min=24*60, pp=pp, det=det, pol=pol,
        events=[], p_attack=0.0
    )
    assert summ["A"] > 0.995
    assert summ["H"] > 0.995

def test_grid_cap_reduces_compute():
    pp = PlantParams()
    det = DetectorParams(tpr=0.7, fpr=0.0, latency_min=5, p_localize=0.8)
    pol = PolicyParams(
        alert_window_min=10, alert_threshold=3, escalation_delay_min=8,
        throttle_level=0.8, isolate_fine=0.1, isolate_coarse=0.3,
        contain_min=20, recover_min=40, stable_min=15
    )
    events = [{"start_min": 0, "end_min": 24*60, "type": "grid_cap", "params": {"P_grid_max_MW": 40.0}}]
    df, summ = run_cycle(
        seed=2, horizon_min=24*60, pp=pp, det=det, pol=pol,
        events=events, p_attack=0.0
    )
    assert summ["A"] < 0.99
