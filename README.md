# Cyber-Attack Containment in Heat-Recovering Data Centers: Shifting the Resilience Frontier

Reproducibility artifact for the paper:

**Cyber-Attack Containment in Heat-Recovering Data Centers: Shifting the Resilience Frontier**

Accepted at **IEEE TPS 2026**.

**Authors:** Hoda Mehrpouyan
**Affiliations:** Boise State University 

## 1. Overview

This repository contains the reproducibility artifact for our study of cyber-attack containment in heat-recovering data centers coupled to district-heating services.

The artifact implements a regenerative **Dynamic Probabilistic Risk Assessment (DPRA)** simulator that models:

- attacker progression;
- detector behavior, including true-positive rate (TPR), false-positive rate (FPR), detection latency, and localization probability;
- finite-state containment and recovery;
- compute-service degradation;
- power–heat coupling;
- heat-pump operation;
- thermal storage; and
- district-heating service.

The experiments evaluate containment policies using two primary service objectives:

- **Compute availability (`A`)**
- **Heat service (`H`)**

The artifact supports reproduction of the primary empirical results reported in the paper, including:

- compute–heat Pareto frontiers;
- the D0 versus D1 detector frontier-shift experiment;
- dominated hypervolume and frontier slice metrics;
- baseline containment-policy comparisons;
- knee-policy selection;
- mean, p90, and CVaR tail-risk statistics;
- attack-template sensitivity analysis; and
- policy-parameter sensitivity analysis.

The experiment configuration, scenario definitions, detector parameters, policy family, and random seeds are frozen in `config.py`.

---

## 2. Scope of the Artifact

The Espoo-like case study used in this work is a **scale-anchored synthetic testbed**, not a calibrated digital twin of an operational facility.

Public information is used only to motivate the scale and existence of large data-center waste-heat recovery coupled to district heating.

This repository does **not** contain:

- proprietary Microsoft data;
- proprietary Fortum data;
- operational Espoo district-heating traces;
- proprietary data-center workload traces; or
- site-specific control configurations.

Cyberattack behavior, detector properties, containment policies, workload assumptions, and detailed plant parameters are research-model variables defined in the artifact.

No external dataset is required to reproduce the reported simulation results.

---

## 3. Repository Structure

```text
.
├── README.md
├── LICENSE
├── CITATION.cff
├── RELEASE_INFO.txt
├── requirements.txt
├── config.py
├── simulator.py
│
├── scripts/
│   ├── run_all.py
│   ├── run_grid.py
│   ├── frontier_metrics.py
│   ├── export_frontier_metrics.py
│   ├── export_tables.py
│   ├── export_baselines.py
│   ├── plot_frontier_panels.py
│   ├── plot_frontiers.py
│   ├── calibrate_detector_variants.py
│   ├── run_attack_template_ablation.py
│   └── run_policy_parameter_sensitivity.py
│
├── tests/
│   ├── test_sanity.py
│   ├── test_constraint_sensitivity.py
│   └── test_frontier_shift.py
│
├── results/
│   └── ...
│
└── figs/
    └── ...
```

### Main files

- `simulator.py` — core regenerative DPRA simulation engine.
- `config.py` — frozen experiment configuration, detector definitions, policy family, scenarios, seeds, and statistical settings.
- `scripts/run_grid.py` — executes the policy/detector/scenario experiment grid.
- `scripts/frontier_metrics.py` — Pareto-frontier and related metric utilities.
- `scripts/export_frontier_metrics.py` — computes hypervolume and frontier slice metrics.
- `scripts/export_baselines.py` — generates baseline-policy summaries.
- `scripts/export_tables.py` — generates knee-policy summary outputs.
- `scripts/plot_frontier_panels.py` — regenerates the paper's frontier-shift figure.
- `scripts/run_attack_template_ablation.py` — evaluates attack-template sensitivity.
- `scripts/run_policy_parameter_sensitivity.py` — evaluates selected containment-policy parameter sensitivities.
- `tests/` — functional and reproducibility checks.

---

## 4. System Requirements

The artifact requires:

- Python **3.10 or later**
- `numpy`
- `pandas`
- `matplotlib`
- `pytest`

The code is intended to run on:

- Linux
- macOS
- Windows

No GPU is required.

A system with at least **8 GB of RAM** is recommended.

---

## 5. Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/containment-policy-sim-tps2026.git
cd containment-policy-sim-tps2026
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### macOS/Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Upgrade `pip` and install the required packages:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 6. Run the Validation Tests

Before reproducing the experiments, run:

```bash
python -m pytest -q
```

The tests check the simulator's core behavior, including:

1. **No-attack sanity** — a no-attack/no-false-alarm configuration should produce near-nominal compute and heat service.
2. **Constraint sensitivity** — imposing a grid-import constraint should reduce attainable compute service relative to the unconstrained case.
3. **Frontier-shift intervention** — the improved detector should produce an outward shift of the attainable service frontier relative to the weaker detector under the frozen experiment design.

All tests should pass before running the full reproduction pipeline.

---

## 7. Reproduce the Paper Results

### Recommended: complete reproduction

From the repository root, run:

```bash
python scripts/run_all.py
```

The complete pipeline regenerates the experiment grid, Pareto frontiers, frontier-shift metrics, baseline summaries, knee-policy results, sensitivity outputs, and frontier figure.

Results are written to:

```text
results/
```

Figures are written to:

```text
figs/
```

---

## 8. Reproduce Individual Components

The individual stages can also be executed separately.

### 8.1 Main simulation grid

```bash
python scripts/run_grid.py --out results
```

Primary outputs include:

```text
results/grid_runs.csv
results/policy_summary.csv
results/pareto_frontiers.csv
results/knees.csv
```

### 8.2 Frontier-shift metrics

```bash
python scripts/export_frontier_metrics.py
```

Outputs include:

```text
results/frontier_shift_metrics.csv
results/frontier_shift_metrics.tex
```

These results include:

- hypervolume under D0 and D1;
- hypervolume gain;
- best heat service subject to a compute-availability threshold; and
- best compute availability subject to a heat-service threshold.

### 8.3 Knee-policy summary

```bash
python scripts/export_tables.py
```

Outputs include:

```text
results/frontier_shift_summary.csv
results/frontier_shift_summary.tex
```

The summary reports the knee-policy compute availability, heat service, mean episode loss, and CVaR.

### 8.4 Baseline-policy comparison

```bash
python scripts/export_baselines.py
```

Outputs include:

```text
results/baseline_summary.csv
results/baselines_A0.tex
results/baselines_A1.tex
```

The baseline set includes:

- NoContain;
- Aggressive;
- Conservative;
- Availability-first;
- Heat-first; and
- Balanced containment.

### 8.5 Frontier figure

```bash
python scripts/plot_frontier_panels.py
```

Outputs:

```text
figs/frontier_shift_A0_A1.png
figs/frontier_shift_A0_A1.pdf
```

These correspond to the D0/D1 frontier-shift experiment under:

- **A0:** cyber attack only;
- **A1:** grid-cap plus cyber attack.

### 8.6 Attack-template sensitivity

```bash
python scripts/run_attack_template_ablation.py
```

This evaluates the relative effect of the modeled attack families, including:

- telemetry manipulation/delay;
- heat-control tampering;
- compute/control-plane compromise; and
- management/OT denial of service.

### 8.7 Policy-parameter sensitivity

```bash
python scripts/run_policy_parameter_sensitivity.py
```

This reproduces the selected containment-policy parameter sensitivity analysis reported in the paper.

---

## 9. Frozen Experimental Configuration

The publication artifact uses a fixed configuration defined in:

```text
config.py
```

The configuration specifies:

- the scenario library;
- simulation horizon;
- common random-number seeds;
- detector variants;
- containment-policy parameters;
- dispatch-policy sweep;
- baseline policies;
- CVaR level; and
- bootstrap settings.

The same random seeds are reused across detector and policy comparisons to support paired comparisons and reduce Monte Carlo variance.

The frozen release should not be modified when reproducing the published results.

Researchers are encouraged to modify the configuration for additional experiments, but such modified experiments should be treated as extensions rather than reproductions of the published results.

---

## 10. Scenarios

The frozen scenario library contains five canonical operating conditions:

| ID | Description |
|---|---|
| `S0_nominal` | Nominal operation |
| `S1_grid_cap` | Grid-import constraint |
| `S2_hp_cap_peak` | Heat-pump peak-capacity constraint |
| `A0_attack_only` | Cyberattack without an additional grid constraint |
| `A1_grid_cap_plus_attack` | Cyberattack combined with a grid-import constraint |

The primary frontier-shift results use `A0_attack_only` and `A1_grid_cap_plus_attack`.

---

## 11. Detector Variants

The artifact contains three detector configurations:

- **D0 weak** — weaker detection, longer latency, and lower localization capability;
- **D1 improved** — improved detection, shorter latency, and better localization; and
- **Oracle** — an upper-bound detector used for sensitivity analysis.

The frontier-shift experiment changes detector quality while keeping the physical model, policy family, and random seeds fixed.

---

## 12. Reproducibility Notes

The artifact is designed around the following reproducibility controls:

- frozen configuration files;
- fixed random seeds;
- common random numbers across detector/policy comparisons;
- no required external dataset;
- script-generated CSV outputs;
- script-generated publication tables;
- automated figure generation; and
- functional tests of key simulator behaviors.

Small numerical differences may occur across Python/library/platform combinations because of floating-point arithmetic. Reported values should agree with the archived reference results to the precision used in the paper.

---

## 13. Expected Runtime

Runtime depends on hardware and Python environment.

Approximate expectations are:

- validation tests: seconds;
- individual plotting/table-generation steps: seconds;
- full experiment grid: several minutes.

No GPU or specialized computing infrastructure is required.

---

## 14. Reference Results

The `results/` directory contains the reference outputs associated with the frozen publication configuration.

These files are provided both to facilitate inspection and to allow users to compare regenerated results against the archived release.

For a strict reproduction, regenerate the outputs using the commands above rather than relying only on the included reference files.

---

## 15. Troubleshooting

If installation or dependency problems occur, recreate the virtual environment.

### macOS/Linux

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Then rerun:

```bash
python -m pytest -q
python scripts/run_all.py
```

All commands should be executed from the **repository root directory**.

---

## 16. Research Use and Limitations

This repository is a research artifact intended for:

- reproduction of the published experiments;
- containment-policy evaluation;
- cyber-physical resilience research; and
- extension of the modeled scenarios and policies.

It is **not** intended to serve as a production incident-response system, operational data-center controller, or site-specific digital twin.

The attack models operate at the level of containment-relevant operational effects rather than exploit implementation.

The detector variants represent operational detection characteristics rather than commercial IDS products.

---

## 17. License

This software is released under the **Apache License 2.0**.

See:

```text
LICENSE
```

for the complete license terms.

---

## 18. Citation

If you use this artifact, please cite the associated paper and software release.

### Paper

**Cyber-Attack Containment in Heat-Recovering Data Centers: Shifting the Resilience Frontier.**  
IEEE TPS 2026.

Full bibliographic information will be added after publication.

### Software

The archival software DOI will be added after the final GitHub release is deposited in Zenodo.

```text
DOI: To be added after Zenodo archival release
```

Machine-readable citation metadata is provided in:

```text
CITATION.cff
```

---

## 19. Artifact Version

This repository contains the frozen reproducibility artifact associated with the IEEE TPS 2026 paper.

```text
Artifact version: v1.0.0
```

The tagged `v1.0.0` GitHub release and corresponding Zenodo archive constitute the permanent publication artifact.

Subsequent development versions may contain extensions or additional experiments and should not be assumed to reproduce the publication configuration unless explicitly stated.
