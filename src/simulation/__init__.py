"""
Stochastic Simulation Package for Systems Reliability Engineering.

This package provides discrete-event Monte Carlo simulation routines,
statistical estimators, confidence interval calculations, and convergence
analysis for cloud payment architectures (Milestone 2, Issues #3 & #4).
"""

from src.simulation.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_NUM_REPLICAS,
    DEFAULT_HORIZON_HOURS,
    SimulationConfig,
    SimulationMetrics,
    ScenarioSimulationResult,
    EmpiricalDistributionSummary,
    simulate_component_renewal,
    merge_outage_intervals,
    intersect_two_interval_lists,
    intersect_multiple_interval_lists,
    total_outage_duration,
    get_scenario_rates,
    run_monte_carlo_simulation,
    run_all_scenarios_simulation,
    compute_simulation_metrics,
    export_simulation_metrics_to_csv,
    compute_convergence_series,
    compute_running_statistics,
    compute_empirical_distribution_summary,
)

__all__ = [
    "DEFAULT_SEED",
    "DEFAULT_NUM_REPLICAS",
    "DEFAULT_HORIZON_HOURS",
    "SimulationConfig",
    "SimulationMetrics",
    "ScenarioSimulationResult",
    "EmpiricalDistributionSummary",
    "simulate_component_renewal",
    "merge_outage_intervals",
    "intersect_two_interval_lists",
    "intersect_multiple_interval_lists",
    "total_outage_duration",
    "get_scenario_rates",
    "run_monte_carlo_simulation",
    "run_all_scenarios_simulation",
    "compute_simulation_metrics",
    "export_simulation_metrics_to_csv",
    "compute_convergence_series",
    "compute_running_statistics",
    "compute_empirical_distribution_summary",
]
