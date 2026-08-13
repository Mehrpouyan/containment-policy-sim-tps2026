import pandas as pd
from pathlib import Path

detector_variants = pd.DataFrame([
    {
        "detector": "D0_weak",
        "description": "Single-signal threshold detector",
        "window_min": 10,
        "threshold": 0.30,
        "min_hits": 4,
        "TPR": 0.45,
        "FPR": 0.04,
        "latency_min": 10,
        "p_localize": 0.55,
    },
    {
        "detector": "D1_improved",
        "description": "Multi-signal residual detector",
        "window_min": 5,
        "threshold": 0.20,
        "min_hits": 2,
        "TPR": 0.75,
        "FPR": 0.02,
        "latency_min": 4,
        "p_localize": 0.80,
    },
    {
        "detector": "D_oracle",
        "description": "Upper bound",
        "window_min": 1,
        "threshold": 0.0,
        "min_hits": 1,
        "TPR": 1.00,
        "FPR": 0.00,
        "latency_min": 1,
        "p_localize": 1.00,
    },
])

Path("results").mkdir(exist_ok=True)
detector_variants.to_csv("results/detector_variants.csv", index=False)

print(detector_variants)
