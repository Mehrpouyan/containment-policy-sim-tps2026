import numpy as np
from simulator import run_cycle, PlantParams, DetectorParams, PolicyParams

def hv_2d(points, ref=(0.0, 0.0)):
    """
    Hypervolume for 2D points (A,H) assuming both are to be maximized and ref is dominated.
    Simple sort-based HV for small N.
    """
    pts = sorted([(max(ref[0],p[0]), max(ref[1],p[1])) for p in points], key=lambda x: x[0])
    hv = 0.0
    prev_a = ref[0]
    best_h = ref[1]
    for a,h in pts:
        # when moving in A, add area of rectangle slice using current best_h
        if a > prev_a:
            hv += (a - prev_a) * best_h
            prev_a = a
        best_h = max(best_h, h)
    # include final slice to 1.0 in A (optional; keep ref-based HV only)
    return hv

def test_detection_improvement_shifts_frontier_outward():
    pp = PlantParams()
    pol = PolicyParams(
        alert_window_min=10, alert_threshold=3, escalation_delay_min=8,
        throttle_level=0.8, isolate_fine=0.1, isolate_coarse=0.3,
        contain_min=20, recover_min=40, stable_min=15
    )

    # D0 (baseline) vs D1 (improved): higher TPR, lower latency, better localization
    d0 = DetectorParams(tpr=0.55, fpr=0.01, latency_min=20, p_localize=0.55)
    d1 = DetectorParams(tpr=0.80, fpr=0.01, latency_min=8,  p_localize=0.75)

    # Keep scenario stable (no exogenous degradation here; you can add events later)
    events = []

    # Evaluate across multiple RNG seeds (each seed draws attack start/type)
    seeds = list(range(1, 31))
    pts0, pts1 = [], []
    for s in seeds:
        _, summ0 = run_cycle(seed=s, horizon_min=24*60, pp=pp, det=d0, pol=pol, events=events, p_attack=0.9)
        _, summ1 = run_cycle(seed=s, horizon_min=24*60, pp=pp, det=d1, pol=pol, events=events, p_attack=0.9)
        pts0.append((summ0["A"], summ0["H"]))
        pts1.append((summ1["A"], summ1["H"]))

    # Compare hypervolume against a dominated reference point
    hv0 = hv_2d(pts0, ref=(0.0, 0.0))
    hv1 = hv_2d(pts1, ref=(0.0, 0.0))

    # Expect improved detector to move frontier outward on average
    assert hv1 >= hv0 * 1.02  # 2% margin; adjust if you change model stochasticity
