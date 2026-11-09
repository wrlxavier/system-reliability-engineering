"""
Discrete-Event Monte Carlo Simulation Engine and Statistical Inference.

This module implements the stochastic discrete-event simulation engine for
cloud payment architectures over an annual mission horizon (T = 8760 hours).
It models component state transitions under alternating renewal theory with
TTF ~ Exp(lambda) and TTR ~ Exp(mu), computes point estimators (A_hat),
bilateral 95% confidence intervals, and exports automated empirical metrics
(Milestone 2, Issues #3 & #4).
"""

from dataclasses import dataclass, field
import math
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats

from src.models.analytical import (
    DEFAULT_BLOCKS,
    BlockParameters,
    HOURS_PER_YEAR,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
)

DEFAULT_SEED: int = 2026
DEFAULT_NUM_REPLICAS: int = 10_000
DEFAULT_HORIZON_HOURS: float = 8760.0


@dataclass
class SimulationConfig:
    """Configuration parameters for the Monte Carlo simulation engine.

    Attributes:
        seed: Random generator seed for reproducibility (default: 2026).
        num_replicas: Number of simulated annual mission iterations N (default: 10,000).
        horizon_hours: Mission duration horizon T in hours (default: 8760.0 h = 1 year).
        confidence_level: Bilateral confidence level for statistical estimation (default: 0.95).
        topology_mode: Topology modeling paradigm ('sla_subsystem' or 'component_parallel').
    """
    seed: int = DEFAULT_SEED
    num_replicas: int = DEFAULT_NUM_REPLICAS
    horizon_hours: float = DEFAULT_HORIZON_HOURS
    confidence_level: float = 0.95
    topology_mode: str = "sla_subsystem"


@dataclass
class SimulationMetrics:
    """Statistical estimators and validation metrics from Monte Carlo iterations.

    Attributes:
        scenario_id: Scenario identifier (1, 2, or 3).
        scenario_name: Human-readable scenario name.
        num_replicas: Number of evaluated annual replicas N.
        horizon_hours: Mission horizon duration T in hours.
        theoretical_availability: Exact analytical availability A.
        theoretical_downtime_hours: Exact analytical expected downtime D in hours.
        mean_availability: Point estimator A_hat = (1/N) * sum(A_k).
        std_availability: Sample standard deviation s_A.
        sem_availability: Standard error of the mean SE(A_hat) = s_A / sqrt(N).
        ci_availability_lower: Bilateral (1 - alpha) CI lower bound for A_hat.
        ci_availability_upper: Bilateral (1 - alpha) CI upper bound for A_hat.
        mean_downtime_hours: Point estimator D_hat = (1/N) * sum(D_k) in hours.
        std_downtime_hours: Sample standard deviation of downtime s_D in hours.
        sem_downtime_hours: Standard error of downtime SE(D_hat) in hours.
        ci_downtime_lower_hours: Bilateral CI lower bound for expected downtime.
        ci_downtime_upper_hours: Bilateral CI upper bound for expected downtime.
        relative_error_availability_pct: Percentage error |A_hat - A| / A * 100%.
        relative_error_downtime_pct: Percentage error |D_hat - D| / D * 100%.
        mean_failures_per_year: Expected count of failure/restoration events.
        margin_of_error_availability: Absolute half-width of the 95% CI for A_hat.
        margin_of_error_downtime_hours: Absolute half-width of the 95% CI for D_hat.
    """
    scenario_id: int
    scenario_name: str
    num_replicas: int
    horizon_hours: float
    theoretical_availability: float
    theoretical_downtime_hours: float
    mean_availability: float
    std_availability: float
    sem_availability: float
    ci_availability_lower: float
    ci_availability_upper: float
    mean_downtime_hours: float
    std_downtime_hours: float
    sem_downtime_hours: float
    ci_downtime_lower_hours: float
    ci_downtime_upper_hours: float
    relative_error_availability_pct: float
    relative_error_downtime_pct: float
    mean_failures_per_year: float
    margin_of_error_availability: float
    margin_of_error_downtime_hours: float


@dataclass
class ScenarioSimulationResult:
    """Full execution result holding sample distributions and summary metrics.

    Attributes:
        scenario_id: Scenario identifier (1, 2, or 3).
        name: Human-readable scenario name.
        config: SimulationConfig used for this run.
        downtime_hours: 1D array of total system downtime per replica (size N).
        availability: 1D array of operational availability per replica (size N).
        failure_counts: 1D array of system failure event counts per replica (size N).
        subsystem_downtimes: Dict mapping block codes to 1D arrays of subsystem downtime.
        metrics: Statistical estimators and confidence intervals (SimulationMetrics).
        execution_time_seconds: Elapsed wall-clock execution duration in seconds.
    """
    scenario_id: int
    name: str
    config: SimulationConfig
    downtime_hours: np.ndarray
    availability: np.ndarray
    failure_counts: np.ndarray
    subsystem_downtimes: Dict[str, np.ndarray]
    metrics: SimulationMetrics
    execution_time_seconds: float

    def to_dataframe(self) -> pd.DataFrame:
        """Convert per-replica simulated outputs into a pandas DataFrame."""
        df = pd.DataFrame({
            "replica_id": np.arange(1, len(self.downtime_hours) + 1),
            "availability": self.availability,
            "downtime_hours": self.downtime_hours,
            "operational_hours": self.config.horizon_hours - self.downtime_hours,
            "failure_count": self.failure_counts,
        })
        for code, sub_dt in self.subsystem_downtimes.items():
            df[f"downtime_{code}_hours"] = sub_dt
        return df


@dataclass
class EmpiricalDistributionSummary:
    """Empirical distribution metrics and risk quantiles for simulation outputs.

    Attributes:
        scenario_id: Scenario identifier (1, 2, or 3).
        scenario_name: Human-readable scenario name.
        sample_size: Number of evaluated iterations N.
        mean: Sample mean.
        std: Sample standard deviation (unbiased, ddof=1).
        sem: Standard error of the mean (std / sqrt(N)).
        median: 50th percentile (median).
        p90: 90th percentile.
        p95: 95th percentile (Value-at-Risk / 95% SLA boundary).
        p99: 99th percentile (extreme tail risk).
        min_val: Minimum observed sample value.
        max_val: Maximum observed sample value.
        skewness: Fisher-Pearson coefficient of skewness.
        kurtosis: Excess kurtosis (Fisher definition).
    """
    scenario_id: int
    scenario_name: str
    sample_size: int
    mean: float
    std: float
    sem: float
    median: float
    p90: float
    p95: float
    p99: float
    min_val: float
    max_val: float
    skewness: float
    kurtosis: float


def sample_exponential_variable(
    rate: float,
    size: int = 1,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Sample continuous random variables from an Exponential(rate) distribution.

    Args:
        rate: Transition rate parameter (lambda for TTF, mu for TTR).
        size: Number of samples to draw.
        rng: Optional NumPy Generator instance.

    Returns:
        Array of sampled durations.
    """
    if rate <= 0.0:
        raise ValueError(f"Transition rate must be strictly positive, got {rate}")
    generator = rng if rng is not None else np.random.default_rng()
    return generator.exponential(scale=1.0 / rate, size=size)


def simulate_component_renewal(
    lambda_rate: float,
    mu_rate: float,
    horizon_hours: float = DEFAULT_HORIZON_HOURS,
    rng: Optional[np.random.Generator] = None,
) -> List[Tuple[float, float]]:
    """Simulate alternating renewal process for a repairable unit over horizon T.

    The component starts at t = 0 in the UP (operational) state:
        - Operational duration: TTF ~ Exp(lambda)
        - Repair duration: TTR ~ Exp(mu)
        - Cycle repeats until mission horizon T is reached.
        - Outages extending past T are clipped to T.

    Args:
        lambda_rate: Constant failure rate (failures/hour).
        mu_rate: Constant repair rate (repairs/hour).
        horizon_hours: Mission duration horizon in hours.
        rng: NumPy Generator instance for reproducibility.

    Returns:
        List of disjoint (outage_start, outage_end) tuples within [0, horizon_hours].
    """
    generator = rng if rng is not None else np.random.default_rng()
    down_intervals: List[Tuple[float, float]] = []
    current_time = 0.0

    while current_time < horizon_hours:
        ttf = float(generator.exponential(1.0 / lambda_rate))
        t_fail = current_time + ttf
        if t_fail >= horizon_hours:
            break
        ttr = float(generator.exponential(1.0 / mu_rate))
        t_restored = min(t_fail + ttr, horizon_hours)
        down_intervals.append((t_fail, t_restored))
        current_time = t_fail + ttr

    return down_intervals


def merge_outage_intervals(
    intervals: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """Merge overlapping or contiguous outage intervals into disjoint intervals.

    For components in series, the system outage is the union of individual outages.
    This function computes the exact union in O(M log M) time.

    Args:
        intervals: List of (start, end) tuples.

    Returns:
        Sorted list of merged non-overlapping (start, end) tuples.
    """
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: List[Tuple[float, float]] = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def intersect_two_interval_lists(
    list1: List[Tuple[float, float]],
    list2: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """Compute the intersection of two disjoint sorted interval lists in O(N1 + N2).

    For active 1-out-of-2 parallel redundant subsystems, the subsystem is DOWN
    only when both units are simultaneously down (temporal overlap).

    Args:
        list1: Sorted disjoint (start, end) intervals of unit 1.
        list2: Sorted disjoint (start, end) intervals of unit 2.

    Returns:
        Sorted list of intersection intervals where both units are down.
    """
    intersections: List[Tuple[float, float]] = []
    i, j = 0, 0
    len1, len2 = len(list1), len(list2)

    while i < len1 and j < len2:
        s1, e1 = list1[i]
        s2, e2 = list2[j]
        start = max(s1, s2)
        end = min(e1, e2)
        if start < end:
            intersections.append((start, end))
        if e1 < e2:
            i += 1
        else:
            j += 1

    return intersections


def intersect_multiple_interval_lists(
    lists: List[List[Tuple[float, float]]],
) -> List[Tuple[float, float]]:
    """Compute the mutual intersection across multiple parallel units."""
    if not lists:
        return []
    result = lists[0]
    for nxt in lists[1:]:
        result = intersect_two_interval_lists(result, nxt)
        if not result:
            break
    return result


def total_outage_duration(intervals: List[Tuple[float, float]]) -> float:
    """Compute total accumulated downtime hours from a list of disjoint intervals."""
    return sum(end - start for start, end in intervals)


def get_scenario_rates(
    scenario_id: int,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    topology_mode: str = "sla_subsystem",
) -> Dict[str, Tuple[float, float]]:
    """Extract transition rates (lambda, mu) for each subsystem in a scenario.

    Args:
        scenario_id: 1 (Baseline), 2 (Multi-AZ), or 3 (Multi-Gateway).
        blocks: Dictionary of BlockParameters.
        topology_mode: 'sla_subsystem' uses contractual scenario SLAs;
                       'component_parallel' uses baseline component unit rates.

    Returns:
        Dict mapping subsystem code to (lambda_rate, mu_rate).
    """
    rates: Dict[str, Tuple[float, float]] = {}

    if scenario_id == 1:
        for code, b in blocks.items():
            mu = 1.0 / b.mttr_hours
            lam = b.lambda_base
            rates[code] = (lam, mu)

    elif scenario_id == 2:
        if topology_mode == "component_parallel":
            # Baseline unit rates used for explicit parallel units
            for code, b in blocks.items():
                mu = 1.0 / b.mttr_hours
                lam = b.lambda_base
                rates[code] = (lam, mu)
        else:
            # Nominal Multi-AZ contractual SLA calibrated rates
            # LB: baseline (single)
            b_lb = blocks["LB"]
            rates["LB"] = (b_lb.lambda_base, 1.0 / b_lb.mttr_hours)

            # App: Multi-AZ SLA (99.99%)
            b_app = blocks["App"]
            mu_app = 1.0 / b_app.mttr_hours
            a_app = b_app.availability_redundant or 0.9999
            lam_app = mu_app * (1.0 - a_app) / a_app
            rates["App"] = (lam_app, mu_app)

            # DB: Multi-AZ HA SLA (99.95%)
            b_db = blocks["DB"]
            mu_db = 1.0 / b_db.mttr_hours
            a_db = b_db.availability_redundant or 0.9995
            lam_db = mu_db * (1.0 - a_db) / a_db
            rates["DB"] = (lam_db, mu_db)

            # PGW: baseline (single)
            b_pgw = blocks["PGW"]
            rates["PGW"] = (b_pgw.lambda_base, 1.0 / b_pgw.mttr_hours)

    elif scenario_id == 3:
        if topology_mode == "component_parallel":
            for code, b in blocks.items():
                mu = 1.0 / b.mttr_hours
                lam = b.lambda_base
                rates[code] = (lam, mu)
        else:
            # LB: baseline
            b_lb = blocks["LB"]
            rates["LB"] = (b_lb.lambda_base, 1.0 / b_lb.mttr_hours)

            # App: Multi-AZ (99.99%)
            b_app = blocks["App"]
            mu_app = 1.0 / b_app.mttr_hours
            a_app = b_app.availability_redundant or 0.9999
            lam_app = mu_app * (1.0 - a_app) / a_app
            rates["App"] = (lam_app, mu_app)

            # DB: Multi-AZ HA (99.95%)
            b_db = blocks["DB"]
            mu_db = 1.0 / b_db.mttr_hours
            a_db = b_db.availability_redundant or 0.9995
            lam_db = mu_db * (1.0 - a_db) / a_db
            rates["DB"] = (lam_db, mu_db)

            # PGW: Multi-Gateway Dual Active-Active (99.999975%)
            b_pgw = blocks["PGW"]
            mu_pgw = 1.0 / b_pgw.mttr_hours
            a_pgw = b_pgw.availability_redundant or 0.99999975
            lam_pgw = mu_pgw * (1.0 - a_pgw) / a_pgw
            rates["PGW"] = (lam_pgw, mu_pgw)
    else:
        raise ValueError(f"Unknown scenario_id: {scenario_id}. Expected 1, 2, or 3.")

    return rates


def compute_simulation_metrics(
    downtimes: np.ndarray,
    horizon_hours: float,
    theoretical_availability: float,
    theoretical_downtime_hours: float,
    scenario_id: int,
    scenario_name: str,
    failure_counts: np.ndarray,
    confidence_level: float = 0.95,
) -> SimulationMetrics:
    """Compute statistical estimators, confidence intervals, and error metrics.

    Mathematical Formulations:
        - Operational availability per replica: A_k = 1 - (D_k / T)
        - Mean availability estimator: A_hat = (1/N) * sum(A_k)
        - Sample standard deviation: s_A = sqrt(sum((A_k - A_hat)^2) / (N - 1))
        - Standard error of the mean: SE(A_hat) = s_A / sqrt(N)
        - Bilateral 95% Confidence Interval (Student's t / Normal):
            CI_95(A_hat) = [A_hat - z * SE(A_hat), A_hat + z * SE(A_hat)]
        - Relative percentage error:
            eps_A = |A_hat - A_theoretical| / A_theoretical * 100%

    Args:
        downtimes: 1D array of system annual downtime per replica in hours.
        horizon_hours: Horizon duration T in hours.
        theoretical_availability: Analytical benchmark A.
        theoretical_downtime_hours: Analytical benchmark D in hours.
        scenario_id: Scenario identifier.
        scenario_name: Scenario name string.
        failure_counts: 1D array of failure event counts per replica.
        confidence_level: Bilateral confidence level (default: 0.95).

    Returns:
        Populated SimulationMetrics dataclass.
    """
    n = len(downtimes)
    if n < 2:
        raise ValueError("At least 2 simulation replicas required for variance estimation.")

    availabilities = (horizon_hours - downtimes) / horizon_hours
    mean_a = float(np.mean(availabilities))
    std_a = float(np.std(availabilities, ddof=1))
    sem_a = std_a / np.sqrt(n)

    mean_d = float(np.mean(downtimes))
    std_d = float(np.std(downtimes, ddof=1))
    sem_d = std_d / np.sqrt(n)

    # Critical value from Student's t distribution with df = N - 1
    alpha = 1.0 - confidence_level
    crit_val = float(stats.t.ppf(1.0 - alpha / 2.0, df=n - 1))

    moe_a = crit_val * sem_a
    ci_a_lower = float(mean_a - moe_a)
    ci_a_upper = float(mean_a + moe_a)

    moe_d = crit_val * sem_d
    ci_d_lower = float(mean_d - moe_d)
    ci_d_upper = float(mean_d + moe_d)

    # Relative errors
    rel_err_a = float(abs(mean_a - theoretical_availability) / theoretical_availability * 100.0)
    rel_err_d = float(
        abs(mean_d - theoretical_downtime_hours) / theoretical_downtime_hours * 100.0
        if theoretical_downtime_hours > 0.0 else 0.0
    )

    mean_failures = float(np.mean(failure_counts))

    return SimulationMetrics(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        num_replicas=n,
        horizon_hours=horizon_hours,
        theoretical_availability=theoretical_availability,
        theoretical_downtime_hours=theoretical_downtime_hours,
        mean_availability=mean_a,
        std_availability=std_a,
        sem_availability=sem_a,
        ci_availability_lower=ci_a_lower,
        ci_availability_upper=ci_a_upper,
        mean_downtime_hours=mean_d,
        std_downtime_hours=std_d,
        sem_downtime_hours=sem_d,
        ci_downtime_lower_hours=ci_d_lower,
        ci_downtime_upper_hours=ci_d_upper,
        relative_error_availability_pct=rel_err_a,
        relative_error_downtime_pct=rel_err_d,
        mean_failures_per_year=mean_failures,
        margin_of_error_availability=moe_a,
        margin_of_error_downtime_hours=moe_d,
    )


def run_monte_carlo_simulation(
    scenario_id: int,
    config: Optional[SimulationConfig] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> ScenarioSimulationResult:
    """Execute stochastic discrete-event Monte Carlo simulation for a scenario.

    Workflow:
        1. Initialize random number generator with fixed seed (e.g. 2026).
        2. Set up component failure and repair parameters.
        3. For each of the N annual mission horizons (T = 8760 h):
           - Sample alternating renewal trajectories TTF ~ Exp(lambda), TTR ~ Exp(mu).
           - Apply topological state evaluation:
             * Pure series (Scenario 1): Union of all component outages.
             * Series-parallel (Scenario 2): Active redundancy intersection / SLA rates.
             * Multi-gateway (Scenario 3): Dual-gateway redundancy / SLA rates.
           - Record system downtime, availability, and failure event count.
        4. Compute statistical estimators, bilateral 95% CIs, and relative error.

    Args:
        scenario_id: 1, 2, or 3.
        config: SimulationConfig instance (default: seed=2026, N=10,000, T=8760 h).
        blocks: Subsystem nominal parameters dictionary.

    Returns:
        ScenarioSimulationResult containing distributions and summary metrics.
    """
    cfg = config if config is not None else SimulationConfig()
    rng = np.random.default_rng(cfg.seed)

    # Also synchronize global seed for reproducibility
    np.random.seed(cfg.seed)

    # Theoretical benchmarks
    if scenario_id == 1:
        s_eval = evaluate_scenario_1(blocks)
    elif scenario_id == 2:
        s_eval = evaluate_scenario_2(blocks)
    elif scenario_id == 3:
        s_eval = evaluate_scenario_3(blocks)
    else:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")

    theo_a = s_eval.system_availability
    theo_d = s_eval.annual_downtime_hours
    name = s_eval.name

    rates = get_scenario_rates(scenario_id, blocks, cfg.topology_mode)
    subsystem_names = list(rates.keys())

    n_reps = cfg.num_replicas
    t_horiz = cfg.horizon_hours

    downtimes = np.empty(n_reps, dtype=np.float64)
    failure_counts = np.empty(n_reps, dtype=np.int64)
    sub_downtimes: Dict[str, np.ndarray] = {
        code: np.empty(n_reps, dtype=np.float64) for code in subsystem_names
    }

    t0 = time.perf_counter()

    if cfg.topology_mode == "component_parallel" and scenario_id in (2, 3):
        # Explicit component-level parallel simulation
        for k in range(n_reps):
            # LB: single unit
            lb_down = simulate_component_renewal(rates["LB"][0], rates["LB"][1], t_horiz, rng)
            sub_downtimes["LB"][k] = total_outage_duration(lb_down)

            # App: 2 parallel units
            app1_down = simulate_component_renewal(rates["App"][0], rates["App"][1], t_horiz, rng)
            app2_down = simulate_component_renewal(rates["App"][0], rates["App"][1], t_horiz, rng)
            app_tier_down = intersect_two_interval_lists(app1_down, app2_down)
            sub_downtimes["App"][k] = total_outage_duration(app_tier_down)

            # DB: 2 parallel units
            db1_down = simulate_component_renewal(rates["DB"][0], rates["DB"][1], t_horiz, rng)
            db2_down = simulate_component_renewal(rates["DB"][0], rates["DB"][1], t_horiz, rng)
            db_tier_down = intersect_two_interval_lists(db1_down, db2_down)
            sub_downtimes["DB"][k] = total_outage_duration(db_tier_down)

            # PGW: single unit in S2, 2 parallel units in S3
            if scenario_id == 2:
                pgw_down = simulate_component_renewal(rates["PGW"][0], rates["PGW"][1], t_horiz, rng)
                sub_downtimes["PGW"][k] = total_outage_duration(pgw_down)
                all_down = lb_down + app_tier_down + db_tier_down + pgw_down
            else:
                pgw1_down = simulate_component_renewal(rates["PGW"][0], rates["PGW"][1], t_horiz, rng)
                pgw2_down = simulate_component_renewal(rates["PGW"][0], rates["PGW"][1], t_horiz, rng)
                pgw_tier_down = intersect_two_interval_lists(pgw1_down, pgw2_down)
                sub_downtimes["PGW"][k] = total_outage_duration(pgw_tier_down)
                all_down = lb_down + app_tier_down + db_tier_down + pgw_tier_down

            merged_sys = merge_outage_intervals(all_down)
            downtimes[k] = total_outage_duration(merged_sys)
            failure_counts[k] = len(merged_sys)
    else:
        # Standard SLA-calibrated discrete-event simulation
        for k in range(n_reps):
            all_down: List[Tuple[float, float]] = []
            for code, (lam, mu) in rates.items():
                comp_down = simulate_component_renewal(lam, mu, t_horiz, rng)
                sub_downtimes[code][k] = total_outage_duration(comp_down)
                all_down.extend(comp_down)

            merged_sys = merge_outage_intervals(all_down)
            downtimes[k] = total_outage_duration(merged_sys)
            failure_counts[k] = len(merged_sys)

    exec_time = time.perf_counter() - t0
    availabilities = (t_horiz - downtimes) / t_horiz

    metrics = compute_simulation_metrics(
        downtimes=downtimes,
        horizon_hours=t_horiz,
        theoretical_availability=theo_a,
        theoretical_downtime_hours=theo_d,
        scenario_id=scenario_id,
        scenario_name=name,
        failure_counts=failure_counts,
        confidence_level=cfg.confidence_level,
    )

    return ScenarioSimulationResult(
        scenario_id=scenario_id,
        name=name,
        config=cfg,
        downtime_hours=downtimes,
        availability=availabilities,
        failure_counts=failure_counts,
        subsystem_downtimes=sub_downtimes,
        metrics=metrics,
        execution_time_seconds=exec_time,
    )


def run_all_scenarios_simulation(
    config: Optional[SimulationConfig] = None,
    scenarios: Tuple[int, ...] = (1, 2, 3),
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Dict[int, ScenarioSimulationResult]:
    """Execute stochastic Monte Carlo simulation across all architectural scenarios.

    Args:
        config: SimulationConfig instance.
        scenarios: Tuple of scenario IDs to run (default: 1, 2, 3).
        blocks: Subsystem BlockParameters dictionary.

    Returns:
        Dict mapping scenario ID to ScenarioSimulationResult.
    """
    results: Dict[int, ScenarioSimulationResult] = {}
    cfg = config if config is not None else SimulationConfig()

    for s_id in scenarios:
        results[s_id] = run_monte_carlo_simulation(
            scenario_id=s_id,
            config=cfg,
            blocks=blocks,
        )

    return results


def export_simulation_metrics_to_csv(
    results: Union[
        ScenarioSimulationResult,
        Dict[int, ScenarioSimulationResult],
        List[ScenarioSimulationResult],
    ],
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Export statistical metrics to automated CSV summary in data/processed/.

    Args:
        results: Single ScenarioSimulationResult, dict, or list of results.
        output_path: Target CSV path (default: data/processed/simulation_metrics.csv).

    Returns:
        Resolved Path to the saved CSV file.
    """
    if isinstance(results, ScenarioSimulationResult):
        results_list = [results]
    elif isinstance(results, dict):
        results_list = list(results.values())
    else:
        results_list = list(results)

    rows = []
    for r in results_list:
        m = r.metrics
        rows.append({
            "scenario_id": m.scenario_id,
            "scenario_name": m.scenario_name,
            "num_replicas": m.num_replicas,
            "horizon_hours": m.horizon_hours,
            "theoretical_availability": m.theoretical_availability,
            "theoretical_availability_pct": m.theoretical_availability * 100.0,
            "simulated_availability": m.mean_availability,
            "simulated_availability_pct": m.mean_availability * 100.0,
            "ci_availability_lower_95": m.ci_availability_lower,
            "ci_availability_upper_95": m.ci_availability_upper,
            "margin_of_error_availability": m.margin_of_error_availability,
            "theoretical_downtime_hours": m.theoretical_downtime_hours,
            "simulated_downtime_hours": m.mean_downtime_hours,
            "ci_downtime_lower_95_hours": m.ci_downtime_lower_hours,
            "ci_downtime_upper_95_hours": m.ci_downtime_upper_hours,
            "margin_of_error_downtime_hours": m.margin_of_error_downtime_hours,
            "std_downtime_hours": m.std_downtime_hours,
            "sem_downtime_hours": m.sem_downtime_hours,
            "relative_error_availability_pct": m.relative_error_availability_pct,
            "relative_error_downtime_pct": m.relative_error_downtime_pct,
            "mean_failures_per_year": m.mean_failures_per_year,
            "execution_time_seconds": r.execution_time_seconds,
        })

    df = pd.DataFrame(rows)

    if output_path is None:
        # Determine root directory
        current = Path.cwd().resolve()
        while current != current.parent:
            if (current / "requirements.txt").exists():
                break
            current = current.parent
        target_path = current / "data" / "processed" / "simulation_metrics.csv"
    else:
        target_path = Path(output_path).resolve()

    target_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target_path, index=False)
    return target_path


def compute_convergence_series(availabilities: np.ndarray) -> np.ndarray:
    """Compute running cumulative mean sequence for asymptotic convergence analysis.

    Formula:
        A_cum(n) = (1 / n) * sum_{k=1}^n A_k, for n in [1, N]

    Args:
        availabilities: 1D array of availability values per replica.

    Returns:
        1D array of cumulative mean values of length N.
    """
    n = len(availabilities)
    indices = np.arange(1, n + 1, dtype=np.float64)
    return np.cumsum(availabilities) / indices


def compute_running_statistics(
    samples: np.ndarray,
    confidence_level: float = 0.95,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute running cumulative sample mean, standard deviation, and confidence half-width.

    Formulas:
        mean(n) = (1 / n) * sum_{k=1}^n x_k
        var(n) = (1 / (n - 1)) * [sum x_k^2 - n * mean(n)^2]  (for n >= 2)
        margin(n) = z_{1 - alpha/2} * std(n) / sqrt(n)

    Args:
        samples: 1D array of sample values of length N.
        confidence_level: Two-sided confidence level (default: 0.95).

    Returns:
        Tuple of (cumulative_mean, running_std, margin_of_error), each of length N.
    """
    n = len(samples)
    if n == 0:
        return np.array([]), np.array([]), np.array([])

    indices = np.arange(1, n + 1, dtype=np.float64)
    cum_mean = np.cumsum(samples) / indices

    cum_sq_sum = np.cumsum(samples ** 2)
    cum_var = np.zeros(n, dtype=np.float64)
    if n > 1:
        cum_var[1:] = (cum_sq_sum[1:] - indices[1:] * (cum_mean[1:] ** 2)) / (indices[1:] - 1.0)
        cum_var = np.maximum(cum_var, 0.0)

    cum_std = np.sqrt(cum_var)
    if n > 0:
        cum_std[0] = 0.0

    z_critical = stats.norm.ppf(1.0 - (1.0 - confidence_level) / 2.0)
    sem = np.zeros(n, dtype=np.float64)
    sem[1:] = cum_std[1:] / np.sqrt(indices[1:])
    margin_of_error = z_critical * sem

    return cum_mean, cum_std, margin_of_error


def compute_empirical_distribution_summary(
    samples: np.ndarray,
    scenario_id: int = 1,
    scenario_name: str = "",
) -> EmpiricalDistributionSummary:
    """Compute empirical distribution metrics and risk percentiles for sample array.

    Args:
        samples: 1D array of sample values (e.g. annual downtime hours).
        scenario_id: Scenario identifier.
        scenario_name: Human-readable scenario name.

    Returns:
        EmpiricalDistributionSummary with mean, std, quantiles, and higher moments.
    """
    n = len(samples)
    if n == 0:
        raise ValueError("Cannot compute empirical distribution summary for empty samples.")
    mean_val = float(np.mean(samples))
    std_val = float(np.std(samples, ddof=1)) if n > 1 else 0.0
    sem_val = std_val / math.sqrt(n) if n > 0 else 0.0
    median_val = float(np.percentile(samples, 50.0))
    p90_val = float(np.percentile(samples, 90.0))
    p95_val = float(np.percentile(samples, 95.0))
    p99_val = float(np.percentile(samples, 99.0))
    min_val = float(np.min(samples))
    max_val = float(np.max(samples))
    skew_val = float(stats.skew(samples)) if n > 2 else 0.0
    kurt_val = float(stats.kurtosis(samples)) if n > 3 else 0.0

    return EmpiricalDistributionSummary(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        sample_size=n,
        mean=mean_val,
        std=std_val,
        sem=sem_val,
        median=median_val,
        p90=p90_val,
        p95=p95_val,
        p99=p99_val,
        min_val=min_val,
        max_val=max_val,
        skewness=skew_val,
        kurtosis=kurt_val,
    )
