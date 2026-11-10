"""
Scenario 3 Expansion and Sensitivity Modeling for External Payment Gateways.

This module provides analytical sensitivity models, parameter sweeps, failover
coverage evaluations, and common-cause failure (CCF) analyses for the
payment gateway expansion (Scenario 3) in Cloud Payment Architectures.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.models.analytical import (
    DEFAULT_BLOCKS,
    BlockParameters,
    HOURS_PER_YEAR,
    MINUTES_PER_YEAR,
    calculate_series_availability,
    calculate_parallel_availability,
    calculate_downtime_hours,
    calculate_downtime_minutes,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
    ScenarioMetrics,
)


@dataclass
class GatewaySensitivityPoint:
    """Metrics evaluated at a specific external gateway SLA availability level."""
    gateway_sla: float
    gateway_unavailability: float
    gateway_downtime_hours_single: float
    gateway_downtime_hours_dual: float
    scenario_2_availability: float
    scenario_2_downtime_hours: float
    scenario_3_availability: float
    scenario_3_downtime_hours: float
    downtime_saved_hours: float
    relative_reduction_pct: float
    downtime_ratio_s2_over_s3: float


def get_internal_redundant_availability(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> float:
    """Compute the combined availability of internal tiers (LB, App Multi-AZ, DB Multi-AZ).

    Formula:
        A_internal = A_LB * A_App,red * A_DB,red

    For default parameters:
        A_internal = 0.9999 * 0.9999 * 0.9995 = 0.99930014995 (~99.930%)
    """
    a_lb = blocks["LB"].availability_base
    a_app_red = blocks["App"].availability_redundant or blocks["App"].availability_base
    a_db_red = blocks["DB"].availability_redundant or blocks["DB"].availability_base
    return float(a_lb * a_app_red * a_db_red)


def evaluate_gateway_availability_sensitivity(
    gateway_availabilities: Optional[Union[List[float], np.ndarray]] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> pd.DataFrame:
    """Evaluate system downtime sensitivity across varying third-party Payment Gateway SLAs.

    Compares Scenario 2 (Single Gateway) vs. Scenario 3 (Dual Active Gateways) as the
    contractual SLA availability A_4 varies from 99.00% to 99.999%.

    Args:
        gateway_availabilities: Iterable of gateway availabilities A_4 to evaluate.
            Defaults to standard industry SLA range [0.990, 0.99995].
        blocks: Subsystem parameter dictionary.

    Returns:
        pd.DataFrame containing sensitivity metrics and comparative downtime columns.
    """
    if gateway_availabilities is None:
        gateway_availabilities = np.array([
            0.99000,
            0.99500,
            0.99800,
            0.99900,
            0.99950,  # Nominal baseline SLA
            0.99980,
            0.99990,
            0.99995,
        ])

    a_internal = get_internal_redundant_availability(blocks)
    rows: List[Dict[str, float]] = []

    for a_pgw in gateway_availabilities:
        u_pgw = 1.0 - a_pgw
        d_pgw_single = u_pgw * HOURS_PER_YEAR

        # Active parallel redundancy: A_4,red = 1 - (1 - A_4)^2
        a_pgw_red = 1.0 - (u_pgw ** 2)
        u_pgw_red = 1.0 - a_pgw_red
        d_pgw_red = u_pgw_red * HOURS_PER_YEAR

        # System availabilities
        a_s2 = a_internal * a_pgw
        u_s2 = 1.0 - a_s2
        d_s2 = u_s2 * HOURS_PER_YEAR

        a_s3 = a_internal * a_pgw_red
        u_s3 = 1.0 - a_s3
        d_s3 = u_s3 * HOURS_PER_YEAR

        d_saved = d_s2 - d_s3
        rel_reduction = (d_saved / d_s2) * 100.0 if d_s2 > 0 else 0.0
        ratio = d_s2 / d_s3 if d_s3 > 0 else np.nan

        rows.append({
            "gateway_sla": a_pgw,
            "gateway_sla_pct": a_pgw * 100.0,
            "gateway_downtime_single_h": d_pgw_single,
            "gateway_downtime_dual_h": d_pgw_red,
            "scenario_2_availability_pct": a_s2 * 100.0,
            "scenario_2_downtime_h": d_s2,
            "scenario_3_availability_pct": a_s3 * 100.0,
            "scenario_3_downtime_h": d_s3,
            "downtime_saved_h": d_saved,
            "relative_reduction_pct": rel_reduction,
            "downtime_ratio_s2_over_s3": ratio,
        })

    return pd.DataFrame(rows)


def evaluate_failover_coverage_sensitivity(
    coverage_probabilities: Optional[Union[List[float], np.ndarray]] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> pd.DataFrame:
    """Evaluate Scenario 3 sensitivity to imperfect failover switching coverage (C).

    In real-world distributed architectures, automatic failover between payment gateways
    is not 100% reliable due to timeout misconfigurations, circuit-breaker latencies,
    or unexpected HTTP 5xx responses.

    Formulation:
        A_4,failover(C) = A_4 + C * A_4 * (1 - A_4)
        U_4,failover(C) = (1 - A_4) * [1 - C * A_4]

    Args:
        coverage_probabilities: Iterable of failover switching coverage probabilities C in [0, 1].
            Defaults to [0.80, 0.85, 0.90, 0.95, 0.98, 0.99, 1.00].
        blocks: Subsystem parameter dictionary.

    Returns:
        pd.DataFrame containing failover sensitivity metrics.
    """
    if coverage_probabilities is None:
        coverage_probabilities = np.array([0.80, 0.85, 0.90, 0.95, 0.98, 0.99, 0.995, 1.00])

    a_pgw = blocks["PGW"].availability_base
    u_pgw = 1.0 - a_pgw
    a_internal = get_internal_redundant_availability(blocks)

    rows: List[Dict[str, float]] = []
    for c in coverage_probabilities:
        # Effective gateway unavailability under imperfect switching coverage C
        u_pgw_eff = u_pgw * (1.0 - c * a_pgw)
        a_pgw_eff = 1.0 - u_pgw_eff
        d_pgw_eff = u_pgw_eff * HOURS_PER_YEAR

        # System availability and downtime
        a_sys = a_internal * a_pgw_eff
        u_sys = 1.0 - a_sys
        d_sys = u_sys * HOURS_PER_YEAR

        # Downtime saved compared to Scenario 2 (Single Gateway, C = 0)
        u_pgw_s2 = u_pgw
        a_s2 = a_internal * (1.0 - u_pgw_s2)
        d_s2 = (1.0 - a_s2) * HOURS_PER_YEAR
        d_saved = d_s2 - d_sys

        rows.append({
            "coverage_probability": c,
            "coverage_pct": c * 100.0,
            "gateway_effective_avail_pct": a_pgw_eff * 100.0,
            "gateway_downtime_h": d_pgw_eff,
            "system_availability_pct": a_sys * 100.0,
            "system_downtime_h": d_sys,
            "downtime_saved_vs_s2_h": d_saved,
            "relative_gain_retained_pct": (d_saved / (d_s2 - (1.0 - a_internal * (1.0 - u_pgw**2)) * HOURS_PER_YEAR)) * 100.0,
        })

    return pd.DataFrame(rows)


def evaluate_common_cause_failure_sensitivity(
    beta_factors: Optional[Union[List[float], np.ndarray]] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> pd.DataFrame:
    """Evaluate Scenario 3 vulnerability to Common-Cause Failures (CCF) using the beta-factor model.

    External payment gateways share upstream dependencies (e.g., major card scheme networks
    like Visa/Mastercard, central bank instant payment rails like PIX, or global cloud DNS providers).
    The beta-factor model splits total gateway failure probability into independent (1 - beta)
    and common-cause (beta) components:

    Formulation:
        Q = 1 - A_4
        Q_I = (1 - beta) * Q
        Q_C = beta * Q
        U_4,parallel(beta) = Q_I^2 + Q_C = (1 - beta)^2 * (1 - A_4)^2 + beta * (1 - A_4)

    Args:
        beta_factors: Iterable of common-cause failure fractions beta in [0, 0.25].
            Defaults to [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20].
        blocks: Subsystem parameter dictionary.

    Returns:
        pd.DataFrame containing CCF sensitivity metrics.
    """
    if beta_factors is None:
        beta_factors = np.array([0.00, 0.01, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20])

    a_pgw = blocks["PGW"].availability_base
    q = 1.0 - a_pgw
    a_internal = get_internal_redundant_availability(blocks)

    rows: List[Dict[str, float]] = []
    for beta in beta_factors:
        # Effective unavailability under beta-factor CCF
        u_pgw_eff = ((1.0 - beta) ** 2) * (q ** 2) + beta * q
        a_pgw_eff = 1.0 - u_pgw_eff
        d_pgw_eff = u_pgw_eff * HOURS_PER_YEAR

        # System availability and downtime
        a_sys = a_internal * a_pgw_eff
        u_sys = 1.0 - a_sys
        d_sys = u_sys * HOURS_PER_YEAR

        # PGW share of system downtime
        pgw_share_pct = (d_pgw_eff / (d_sys if d_sys > 0 else 1.0)) * 100.0

        rows.append({
            "beta_ccf": beta,
            "beta_ccf_pct": beta * 100.0,
            "gateway_effective_avail_pct": a_pgw_eff * 100.0,
            "gateway_downtime_h": d_pgw_eff,
            "system_availability_pct": a_sys * 100.0,
            "system_downtime_h": d_sys,
            "gateway_share_of_downtime_pct": pgw_share_pct,
        })

    return pd.DataFrame(rows)


def compute_diminishing_returns_metrics(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> pd.DataFrame:
    """Quantify the law of diminishing returns across architectural evolutionary stages.

    Examines the transition from Baseline (S1) -> Multi-AZ (S2) -> Multi-Gateway (S3)
    and a hypothetical Zero-Downtime Database (S4).

    Returns:
        pd.DataFrame summarizing architectural progression, downtime saved, and dominant bottlenecks.
    """
    s1 = evaluate_scenario_1(blocks)
    s2 = evaluate_scenario_2(blocks)
    s3 = evaluate_scenario_3(blocks)

    # Hypothetical Scenario 4: Multi-Region Database clustering (A_DB = 99.999%)
    a_lb = blocks["LB"].availability_base
    a_app_red = blocks["App"].availability_redundant or 0.9999
    a_pgw_red = blocks["PGW"].availability_redundant or 0.99999975
    a_db_hypothetical = 0.99999  # 99.999% globally distributed database
    a_s4 = a_lb * a_app_red * a_db_hypothetical * a_pgw_red
    d_s4 = (1.0 - a_s4) * HOURS_PER_YEAR

    steps = [
        {
            "Step": "Baseline (Scenario 1)",
            "Topology": "Pure Series (SPOF at every layer)",
            "System Availability (%)": s1.system_availability * 100.0,
            "Annual Downtime (h/yr)": s1.annual_downtime_hours,
            "Downtime Saved vs Previous (h/yr)": 0.0,
            "Marginal Reduction (%)": 0.0,
            "Cumulative Reduction vs S1 (%)": 0.0,
            "Primary Bottleneck Tier": "App & DB (94.6%)",
        },
        {
            "Step": "Multi-AZ Core (Scenario 2)",
            "Topology": "Active App Multi-AZ + DB Multi-AZ Failover",
            "System Availability (%)": s2.system_availability * 100.0,
            "Annual Downtime (h/yr)": s2.annual_downtime_hours,
            "Downtime Saved vs Previous (h/yr)": s1.annual_downtime_hours - s2.annual_downtime_hours,
            "Marginal Reduction (%)": ((s1.annual_downtime_hours - s2.annual_downtime_hours) / s1.annual_downtime_hours) * 100.0,
            "Cumulative Reduction vs S1 (%)": s2.relative_reduction_vs_baseline_pct,
            "Primary Bottleneck Tier": "DB & PGW (83.4%)",
        },
        {
            "Step": "Multi-Gateway (Scenario 3)",
            "Topology": "Multi-AZ Core + Dual Active-Active Gateways",
            "System Availability (%)": s3.system_availability * 100.0,
            "Annual Downtime (h/yr)": s3.annual_downtime_hours,
            "Downtime Saved vs Previous (h/yr)": s2.annual_downtime_hours - s3.annual_downtime_hours,
            "Marginal Reduction (%)": ((s2.annual_downtime_hours - s3.annual_downtime_hours) / s2.annual_downtime_hours) * 100.0,
            "Cumulative Reduction vs S1 (%)": s3.relative_reduction_vs_baseline_pct,
            "Primary Bottleneck Tier": "DB Failover (71.4%)",
        },
        {
            "Step": "Global DB HA (Hypothetical S4)",
            "Topology": "Multi-Gateway + Multi-Region Active-Active DB",
            "System Availability (%)": a_s4 * 100.0,
            "Annual Downtime (h/yr)": d_s4,
            "Downtime Saved vs Previous (h/yr)": s3.annual_downtime_hours - d_s4,
            "Marginal Reduction (%)": ((s3.annual_downtime_hours - d_s4) / s3.annual_downtime_hours) * 100.0,
            "Cumulative Reduction vs S1 (%)": ((s1.annual_downtime_hours - d_s4) / s1.annual_downtime_hours) * 100.0,
            "Primary Bottleneck Tier": "LB & App Ingress (95.1%)",
        },
    ]

    return pd.DataFrame(steps)
