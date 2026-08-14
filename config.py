# Frozen experiment configuration
# Reproducibility artifact for IEEE TPS 2026

SCENARIO_LIBRARY_VERSION = "v1.0"
POLICY_GRID_VERSION = "v1.0"
DETECTOR_SET_VERSION = "v1.0"

# Scenarios used in the paper
SCENARIO_IDS = [
    "S0_nominal",
    "S1_grid_cap",
    "S2_hp_cap_peak",
    "A0_attack_only",
    "A1_grid_cap_plus_attack",
]

# Reproducibility controls
HORIZON_MIN = 1440
SEEDS = list(range(0, 40))  

# CVaR / bootstrap settings
CVAR_ALPHA = 0.90
BOOT_N = 600
BOOT_CI = 0.95
BOOT_SEED = 123

# Detector definitions (map -> DetectorParams fields in simulator.py)
DETECTORS = {
    "D0_weak":     dict(tpr=0.43, fpr=0.04, latency_min=10, p_localize=0.55),
    "D1_improved": dict(tpr=0.75, fpr=0.02, latency_min=4,  p_localize=0.80),
    "D_oracle":    dict(tpr=1.00, fpr=0.00, latency_min=1,  p_localize=1.00),
}

# Policy family:
# - Sweep dispatch_alpha to generate a real compute-vs-heat frontier
# - Include a few baselines
POLICY_BASE = dict(
    alert_window_min=10,
    alert_threshold=3,
    escalation_delay_min=8,
    throttle_level=0.8,
    isolate_fine=0.1,
    isolate_coarse=0.3,
    contain_min=20,
    recover_min=40,
    stable_min=15,
    dispatch_alpha=0.75,
)

DISPATCH_ALPHAS = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.00]

BASELINE_POLICIES = {
    "P_availability_first": dict(dispatch_alpha=1.00),
    "P_heat_first":         dict(dispatch_alpha=0.15),
    "P_balanced":           dict(dispatch_alpha=0.75),
    # practically "never contain"
    "P_no_containment":     dict(alert_threshold=10**9, dispatch_alpha=0.75),
    # aggressive containment baseline
    "P_aggressive":         dict(alert_threshold=1, escalation_delay_min=1, isolate_coarse=0.45, throttle_level=0.7),
    # conservative baseline
    "P_conservative":       dict(alert_threshold=4, escalation_delay_min=12, isolate_coarse=0.15, throttle_level=0.9),
}
