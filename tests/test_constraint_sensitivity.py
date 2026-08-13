from __future__ import annotations

from simulator import (
    PlantParams,
    DetectorParams,
    PolicyParams,
    run_cycle,
    scenario_events,
)
import config


def test_grid_cap_reduces_compute_availability():
    """
    Constraint-sensitivity check used by the publication artifact.

    With attacks and false alerts disabled, apply the frozen S1 peak
    grid-import constraint and verify that attainable compute availability
    is lower than in the unconstrained S0 nominal case.

    A compute-favoring dispatch_alpha=0.90 is used so that the electrical
    grid cap becomes binding during the peak interval while nominal
    operation remains fully served.
    """
    plant = PlantParams()

    # Disable false alerts so that containment behavior cannot confound
    # the physical grid-cap comparison.
    detector = DetectorParams(
        tpr=1.0,
        fpr=0.0,
        latency_min=1,
        p_localize=1.0,
    )

    # Prevent containment and use a compute-favoring dispatch setting.
    policy = PolicyParams(
        **{
            **config.POLICY_BASE,
            "alert_threshold": 10**9,
            "dispatch_alpha": 0.90,
        }
    )

    nominal_events, nominal_p_attack = scenario_events("S0_nominal")
    capped_events, capped_p_attack = scenario_events("S1_grid_cap")

    nominal_trace, nominal = run_cycle(
        seed=0,
        horizon_min=config.HORIZON_MIN,
        pp=plant,
        det=detector,
        pol=policy,
        events=nominal_events,
        p_attack=nominal_p_attack,
    )

    capped_trace, capped = run_cycle(
        seed=0,
        horizon_min=config.HORIZON_MIN,
        pp=plant,
        det=detector,
        pol=policy,
        events=capped_events,
        p_attack=capped_p_attack,
    )

    # Both scenarios are non-attack cases.
    assert nominal_p_attack == 0.0
    assert capped_p_attack == 0.0

    # The S1 event must actually impose a lower grid cap.
    assert capped_trace["grid_cap"].min() < nominal_trace["grid_cap"].min()

    # Nominal operation should fully serve compute demand for this
    # deterministic configuration.
    assert nominal["A"] > 0.995

    # The grid constraint must reduce compute availability.
    assert capped["A"] < nominal["A"]

    # Require a non-trivial reduction so the test does not pass because
    # of floating-point noise.
    assert (nominal["A"] - capped["A"]) > 0.01
