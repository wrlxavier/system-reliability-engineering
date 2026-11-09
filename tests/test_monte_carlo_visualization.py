"""
Unit tests for Milestone 3 / Issue #5: Monte Carlo Convergence Curves, Empirical
Downtime Distribution Histograms, and Pareto Subsystem Cross-Validation.
"""

import math
from pathlib import Path
import numpy as np
import pytest
import matplotlib.pyplot as plt

from src.simulation.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_NUM_REPLICAS,
    SimulationConfig,
    ScenarioSimulationResult,
    run_monte_carlo_simulation,
    run_all_scenarios_simulation,
    compute_running_statistics,
    compute_empirical_distribution_summary,
    compute_convergence_series,
)
from src.visualization.plot_monte_carlo import (
    plot_monte_carlo_convergence,
    plot_downtime_histograms,
    plot_simulation_subsystem_breakdown,
    generate_all_monte_carlo_diagrams,
)


def test_running_statistics_mathematical_properties():
    """Verify running mean, running standard deviation, and confidence half-width."""
    rng = np.random.default_rng(2026)
    samples = rng.normal(loc=92.58, scale=11.55, size=2000)

    cum_mean, cum_std, margin = compute_running_statistics(samples, confidence_level=0.95)

    assert len(cum_mean) == 2000
    assert len(cum_std) == 2000
    assert len(margin) == 2000

    # First point equals first sample
    assert math.isclose(cum_mean[0], samples[0])

    # Final running mean equals sample mean
    assert math.isclose(cum_mean[-1], float(np.mean(samples)), rel_tol=1e-7)

    # Final running std equals sample standard deviation with ddof=1
    assert math.isclose(cum_std[-1], float(np.std(samples, ddof=1)), rel_tol=1e-7)

    # Margin of error should decrease approximately as 1 / sqrt(n)
    assert margin[-1] < margin[10]
    expected_last_margin = 1.959964 * (cum_std[-1] / math.sqrt(2000))
    assert math.isclose(margin[-1], expected_last_margin, rel_tol=1e-3)

    # Edge cases
    empty_mean, empty_std, empty_margin = compute_running_statistics(np.array([]))
    assert len(empty_mean) == 0


def test_empirical_distribution_summary():
    """Verify computation of sample mean, quantiles, and higher moments."""
    rng = np.random.default_rng(2026)
    data = rng.exponential(scale=10.0, size=5000)

    summary = compute_empirical_distribution_summary(data, scenario_id=1, scenario_name="Test")

    assert summary.sample_size == 5000
    assert math.isclose(summary.mean, float(np.mean(data)), rel_tol=1e-5)
    assert math.isclose(summary.std, float(np.std(data, ddof=1)), rel_tol=1e-5)
    assert summary.median == float(np.percentile(data, 50.0))
    assert summary.p90 == float(np.percentile(data, 90.0))
    assert summary.p95 == float(np.percentile(data, 95.0))
    assert summary.p99 == float(np.percentile(data, 99.0))
    assert summary.min_val == float(np.min(data))
    assert summary.max_val == float(np.max(data))

    # Quantiles must be monotonically non-decreasing
    assert summary.min_val <= summary.median <= summary.p90 <= summary.p95 <= summary.p99 <= summary.max_val

    # Exponential distribution has positive skewness (~2.0)
    assert summary.skewness > 1.0

    with pytest.raises(ValueError):
        compute_empirical_distribution_summary(np.array([]))


def test_plot_monte_carlo_convergence_runs_and_exports(tmp_path: Path):
    """Verify convergence plot generates valid figure and exports dual formats."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=200, horizon_hours=1000.0)
    res1 = run_monte_carlo_simulation(1, config=cfg)
    res2 = run_monte_carlo_simulation(2, config=cfg)
    results = {1: res1, 2: res2}

    fig = plot_monte_carlo_convergence(results, output_dir=tmp_path, save_individual=True)

    assert isinstance(fig, plt.Figure)
    assert (tmp_path / "monte_carlo_convergence.pdf").exists()
    assert (tmp_path / "monte_carlo_convergence.png").exists()
    assert (tmp_path / "monte_carlo_convergence_scenario_1.pdf").exists()
    assert (tmp_path / "monte_carlo_convergence_scenario_2.pdf").exists()

    plt.close(fig)


def test_plot_downtime_histograms_runs_and_exports(tmp_path: Path):
    """Verify downtime histogram generates valid figure and exports dual formats."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=200, horizon_hours=1000.0)
    res1 = run_monte_carlo_simulation(1, config=cfg)
    res2 = run_monte_carlo_simulation(2, config=cfg)
    results = {1: res1, 2: res2}

    fig = plot_downtime_histograms(results, output_dir=tmp_path, save_individual=True)

    assert isinstance(fig, plt.Figure)
    assert (tmp_path / "downtime_histogram.pdf").exists()
    assert (tmp_path / "downtime_histogram.png").exists()
    assert (tmp_path / "downtime_histogram_scenario_1.pdf").exists()
    assert (tmp_path / "downtime_histogram_scenario_2.pdf").exists()

    plt.close(fig)


def test_plot_subsystem_breakdown_runs_and_exports(tmp_path: Path):
    """Verify subsystem downtime breakdown Pareto chart generation."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=100, horizon_hours=1000.0)
    res1 = run_monte_carlo_simulation(1, config=cfg)
    res2 = run_monte_carlo_simulation(2, config=cfg)
    results = {1: res1, 2: res2}

    fig = plot_simulation_subsystem_breakdown(results, output_dir=tmp_path)

    assert isinstance(fig, plt.Figure)
    assert (tmp_path / "monte_carlo_pareto_validation.pdf").exists()
    assert (tmp_path / "monte_carlo_pareto_validation.png").exists()

    plt.close(fig)


def test_generate_all_monte_carlo_diagrams(tmp_path: Path):
    """Verify that generate_all_monte_carlo_diagrams produces all required publication artifacts."""
    cfg = SimulationConfig(seed=DEFAULT_SEED, num_replicas=150, horizon_hours=1000.0)
    res1 = run_monte_carlo_simulation(1, config=cfg)
    res2 = run_monte_carlo_simulation(2, config=cfg)
    res3 = run_monte_carlo_simulation(3, config=cfg)
    results = {1: res1, 2: res2, 3: res3}

    files = generate_all_monte_carlo_diagrams(results, output_dir=tmp_path)

    # Acceptance criteria: monte_carlo_convergence.pdf and downtime_histogram.pdf
    assert "monte_carlo_convergence.pdf" in files
    assert "downtime_histogram.pdf" in files
    assert "monte_carlo_pareto_validation.pdf" in files

    for name, path in files.items():
        assert path.exists(), f"File {name} does not exist."
        assert path.stat().st_size > 0, f"File {name} is empty."
