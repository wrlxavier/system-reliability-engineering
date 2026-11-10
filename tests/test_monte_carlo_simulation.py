"""
Unit tests for Milestone 2 / Issue #3 & #4: Stochastic Discrete-Event Simulation Engine
and Statistical Inference.
"""

import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.models.analytical import (
    DEFAULT_BLOCKS,
    HOURS_PER_YEAR,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
)
from src.simulation.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_NUM_REPLICAS,
    DEFAULT_HORIZON_HOURS,
    SimulationConfig,
    SimulationMetrics,
    ScenarioSimulationResult,
    sample_exponential_variable,
    simulate_component_renewal,
    merge_outage_intervals,
    intersect_two_interval_lists,
    intersect_multiple_interval_lists,
    total_outage_duration,
    get_scenario_rates,
    compute_simulation_metrics,
    run_monte_carlo_simulation,
    run_all_scenarios_simulation,
    export_simulation_metrics_to_csv,
    compute_convergence_series,
)


def test_sample_exponential_variable():
    """Verify exponential sampling mean and variance against analytical properties."""
    rate = 2.5
    rng = np.random.default_rng(2026)
    samples = sample_exponential_variable(rate, size=50_000, rng=rng)

    expected_mean = 1.0 / rate  # 0.4
    expected_std = 1.0 / rate   # 0.4

    assert math.isclose(float(np.mean(samples)), expected_mean, rel_tol=0.02)
    assert math.isclose(float(np.std(samples)), expected_std, rel_tol=0.02)

    with pytest.raises(ValueError):
        sample_exponential_variable(0.0)
    with pytest.raises(ValueError):
        sample_exponential_variable(-1.5)


def test_merge_outage_intervals():
    """Verify that overlapping and adjacent outage intervals are merged correctly."""
    assert merge_outage_intervals([]) == []

    # Non-overlapping
    intervals = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
    assert merge_outage_intervals(intervals) == [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]

    # Overlapping and out of order
    intervals = [(3.0, 5.0), (1.0, 4.0), (7.0, 8.0), (7.5, 9.0)]
    merged = merge_outage_intervals(intervals)
    assert merged == [(1.0, 5.0), (7.0, 9.0)]
    assert total_outage_duration(merged) == (5.0 - 1.0) + (9.0 - 7.0)  # 6.0


def test_intersect_two_interval_lists():
    """Verify active parallel redundancy intersection logic."""
    assert intersect_two_interval_lists([], [(1.0, 2.0)]) == []
    assert intersect_two_interval_lists([(1.0, 2.0)], []) == []

    # Non-overlapping intervals (no simultaneous failure)
    list1 = [(1.0, 2.0), (5.0, 6.0)]
    list2 = [(2.5, 4.0), (6.5, 8.0)]
    assert intersect_two_interval_lists(list1, list2) == []

    # Partial overlap
    list1 = [(1.0, 4.0), (10.0, 15.0)]
    list2 = [(2.0, 5.0), (12.0, 13.0)]
    expected = [(2.0, 4.0), (12.0, 13.0)]
    assert intersect_two_interval_lists(list1, list2) == expected

    # Multiple intersection
    lists = [
        [(1.0, 5.0)],
        [(2.0, 6.0)],
        [(3.0, 7.0)],
    ]
    assert intersect_multiple_interval_lists(lists) == [(3.0, 5.0)]


def test_reproducibility_with_seed():
    """Verify that runs with identical seed 2026 generate identical numerical trajectories."""
    cfg1 = SimulationConfig(seed=2026, num_replicas=100, horizon_hours=1000.0)
    cfg2 = SimulationConfig(seed=2026, num_replicas=100, horizon_hours=1000.0)

    res1 = run_monte_carlo_simulation(1, config=cfg1)
    res2 = run_monte_carlo_simulation(1, config=cfg2)

    np.testing.assert_array_equal(res1.downtime_hours, res2.downtime_hours)
    np.testing.assert_array_equal(res1.failure_counts, res2.failure_counts)
    assert res1.metrics.mean_availability == res2.metrics.mean_availability


def test_monte_carlo_scenario_1_convergence():
    """Verify Scenario 1 simulation executes in <60s and converges to A_base with rel_err < 0.05%."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=10_000, horizon_hours=HOURS_PER_YEAR)
    res = run_monte_carlo_simulation(1, config=cfg)

    # Acceptance criteria: execution under 60 seconds
    assert res.execution_time_seconds < 60.0

    # Acceptance criteria: relative error < 0.05%
    rel_err = res.metrics.relative_error_availability_pct
    assert rel_err < 0.05, f"Relative error {rel_err:.5f}% exceeds 0.05%"

    # Analytical benchmark: A_base = 0.98943103
    theo_a = res.metrics.theoretical_availability
    assert math.isclose(theo_a, 0.9894310345, rel_tol=1e-5)

    # 95% Confidence Interval must contain the theoretical availability
    ci_lower = res.metrics.ci_availability_lower
    ci_upper = res.metrics.ci_availability_upper
    assert ci_lower <= theo_a <= ci_upper, (
        f"Theoretical A ({theo_a}) outside 95% CI [{ci_lower}, {ci_upper}]"
    )

    # Downtime benchmark: D_base ~ 92.58 h
    theo_d = res.metrics.theoretical_downtime_hours
    assert math.isclose(theo_d, 92.5841, rel_tol=1e-3)
    assert res.metrics.ci_downtime_lower_hours <= theo_d <= res.metrics.ci_downtime_upper_hours


def test_monte_carlo_scenario_2_convergence():
    """Verify Scenario 2 simulation converges to A_red = 0.998800 with rel_err < 0.05%."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=10_000, horizon_hours=HOURS_PER_YEAR)
    res = run_monte_carlo_simulation(2, config=cfg)

    assert res.execution_time_seconds < 60.0

    rel_err = res.metrics.relative_error_availability_pct
    assert rel_err < 0.05, f"Relative error {rel_err:.5f}% exceeds 0.05%"

    theo_a = res.metrics.theoretical_availability
    assert math.isclose(theo_a, 0.99880046, rel_tol=1e-5)

    ci_lower = res.metrics.ci_availability_lower
    ci_upper = res.metrics.ci_availability_upper
    assert ci_lower <= theo_a <= ci_upper, (
        f"Theoretical A ({theo_a}) outside 95% CI [{ci_lower}, {ci_upper}]"
    )

    # Downtime benchmark: D_red ~ 10.51 h
    theo_d = res.metrics.theoretical_downtime_hours
    assert math.isclose(theo_d, 10.5080, rel_tol=1e-3)
    assert res.metrics.ci_downtime_lower_hours <= theo_d <= res.metrics.ci_downtime_upper_hours


def test_monte_carlo_scenario_3_convergence():
    """Verify Scenario 3 simulation converges to A_scen3 = 0.999300 with rel_err < 0.05%."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=10_000, horizon_hours=HOURS_PER_YEAR)
    res = run_monte_carlo_simulation(3, config=cfg)

    assert res.execution_time_seconds < 60.0

    rel_err = res.metrics.relative_error_availability_pct
    assert rel_err < 0.05, f"Relative error {rel_err:.5f}% exceeds 0.05%"

    theo_a = res.metrics.theoretical_availability
    assert math.isclose(theo_a, 0.99929986, rel_tol=1e-5)


def test_component_parallel_mode():
    """Verify that component_parallel topology mode executes properly."""
    cfg = SimulationConfig(
        seed=DEFAULT_SEED,
        num_replicas=500,
        horizon_hours=HOURS_PER_YEAR,
        topology_mode="component_parallel",
    )
    res = run_monte_carlo_simulation(2, config=cfg)
    assert len(res.downtime_hours) == 500
    assert res.metrics.mean_availability > 0.999


def test_get_scenario_rates_defaults_and_mode_alias():
    """Verify get_scenario_rates default signature, mode alias, and SLA calibration."""
    r_default = get_scenario_rates(2)
    r_topo = get_scenario_rates(2, topology_mode="sla_subsystem")
    r_mode = get_scenario_rates(2, mode="sla_subsystem")
    assert r_default == r_topo == r_mode

    # In sla_subsystem, DB failure rate matches 99.95% SLA (mu = 1.0, A = 0.9995)
    # lambda = 1.0 * (1 - 0.9995) / 0.9995 = 0.0005 / 0.9995 ~ 0.00050025 h^-1
    assert math.isclose(r_default["DB"][0], 0.00050025, rel_tol=1e-4)

    # In component_parallel mode, baseline single-instance failure rate is retained
    r_parallel = get_scenario_rates(2, mode="component_parallel")
    assert math.isclose(r_parallel["DB"][0], DEFAULT_BLOCKS["DB"].lambda_base, rel_tol=1e-8)


def test_export_simulation_metrics_csv(tmp_path):
    """Verify automated CSV export conforming to acceptance criteria."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=500, horizon_hours=HOURS_PER_YEAR)
    res1 = run_monte_carlo_simulation(1, config=cfg)
    res2 = run_monte_carlo_simulation(2, config=cfg)

    out_file = tmp_path / "test_metrics.csv"
    saved_path = export_simulation_metrics_to_csv([res1, res2], output_path=out_file)

    assert saved_path.exists()
    df = pd.read_csv(saved_path)
    assert len(df) == 2
    assert "simulated_availability" in df.columns
    assert "ci_availability_lower_95" in df.columns
    assert "ci_availability_upper_95" in df.columns
    assert "relative_error_availability_pct" in df.columns

    # Verify all relative errors are below 0.05%
    for val in df["relative_error_availability_pct"]:
        assert val < 0.05


def test_convergence_series():
    """Verify asymptotic convergence cumulative series computation."""
    data = np.array([1.0, 0.0, 1.0, 1.0])
    series = compute_convergence_series(data)
    expected = np.array([1.0, 0.5, 2.0 / 3.0, 0.75])
    np.testing.assert_allclose(series, expected)


def test_result_to_dataframe():
    """Verify conversion of ScenarioSimulationResult to DataFrame."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=50, horizon_hours=1000.0)
    res = run_monte_carlo_simulation(1, config=cfg)
    df = res.to_dataframe()

    assert len(df) == 50
    assert "replica_id" in df.columns
    assert "availability" in df.columns
    assert "downtime_hours" in df.columns
    assert "downtime_App_hours" in df.columns
