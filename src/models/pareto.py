"""
Subsystem Unavailability and Downtime Pareto Analysis.

This module quantifies individual subsystem contributions to system downtime,
computes cumulative unavailability profiles, and evaluates architectural bottleneck
shifts between baseline and redundant configurations for Milestone 3 / Issue #3 & #5.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from src.models.analytical import (
    DEFAULT_BLOCKS,
    BlockParameters,
    HOURS_PER_YEAR,
    MINUTES_PER_YEAR,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
)


@dataclass
class SubsystemDowntimeContribution:
    """Individual downtime contribution and Pareto metrics for a subsystem block.

    Attributes:
        block_code: Short identifier (LB, App, DB, PGW).
        subsystem_name: Full descriptive name of the subsystem.
        tier: Architectural tier description.
        availability: Operating steady-state availability A_i in this scenario.
        unavailability: Operating steady-state unavailability U_i = 1 - A_i.
        downtime_hours: Standalone expected annual downtime in hours (U_i * 8760).
        downtime_minutes: Standalone expected annual downtime in minutes.
        percentage_of_total: Percentage share of total subsystem downtime (%).
        cumulative_percentage: Running cumulative percentage share (%).
        allocated_downtime_hours: First-order allocated share of exact system downtime.
        rank: Descending rank by downtime contribution (1 to n).
    """
    block_code: str
    subsystem_name: str
    tier: str
    availability: float
    unavailability: float
    downtime_hours: float
    downtime_minutes: float
    percentage_of_total: float
    cumulative_percentage: float
    allocated_downtime_hours: float
    rank: int


@dataclass
class ParetoAnalysisResult:
    """Comprehensive Pareto analysis result for an architectural scenario.

    Attributes:
        scenario_id: Scenario identifier (1, 2, or 3).
        scenario_name: Name of the scenario configuration.
        system_availability: Exact analytical system availability A_sys.
        system_unavailability: Exact analytical system unavailability U_sys = 1 - A_sys.
        system_downtime_hours: Exact analytical system downtime in hours/year.
        sum_component_downtime_hours: Sum of independent subsystem downtimes (hours/year).
        contributions: List of SubsystemDowntimeContribution sorted descending by downtime.
        dominant_bottlenecks: List of block codes causing >= 80% cumulative downtime.
        top_contributor_code: Short code of the largest single downtime contributor.
        top_contributor_share_pct: Percentage share of the largest contributor (%).
        app_db_combined_share_pct: Combined percentage share of App and DB tiers (%).
        pgw_share_pct: Percentage share of the external Payment Gateway tier (%).
    """
    scenario_id: int
    scenario_name: str
    system_availability: float
    system_unavailability: float
    system_downtime_hours: float
    sum_component_downtime_hours: float
    contributions: List[SubsystemDowntimeContribution]
    dominant_bottlenecks: List[str]
    top_contributor_code: str
    top_contributor_share_pct: float
    app_db_combined_share_pct: float
    pgw_share_pct: float


def compute_subsystem_downtime_contributions(
    scenario_id: int,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> ParetoAnalysisResult:
    """Compute individual downtime contributions and Pareto ordering for a given scenario.

    Args:
        scenario_id: Architectural scenario (1 for Baseline Series, 2 for Multi-AZ, 3 for Multi-Gateway).
        blocks: Subsystem nominal parameters dictionary.

    Returns:
        ParetoAnalysisResult with sorted contributions and summary metrics.
    """
    if scenario_id == 1:
        metrics = evaluate_scenario_1(blocks)
        scenario_name = "Scenario 1 (Baseline Series)"
        active_avails = {
            "LB": blocks["LB"].availability_base,
            "App": blocks["App"].availability_base,
            "DB": blocks["DB"].availability_base,
            "PGW": blocks["PGW"].availability_base,
        }
    elif scenario_id == 2:
        metrics = evaluate_scenario_2(blocks)
        scenario_name = "Scenario 2 (Multi-AZ Series-Parallel)"
        active_avails = {
            "LB": blocks["LB"].availability_base,
            "App": blocks["App"].availability_redundant,
            "DB": blocks["DB"].availability_redundant,
            "PGW": blocks["PGW"].availability_base,
        }
    elif scenario_id == 3:
        metrics = evaluate_scenario_3(blocks)
        scenario_name = "Scenario 3 (Multi-Gateway Expansion)"
        active_avails = {
            "LB": blocks["LB"].availability_base,
            "App": blocks["App"].availability_redundant,
            "DB": blocks["DB"].availability_redundant,
            "PGW": blocks["PGW"].availability_redundant,
        }
    else:
        raise ValueError(f"Unsupported scenario_id: {scenario_id}. Must be 1, 2, or 3.")

    # Calculate standalone downtime for each block
    raw_items = []
    pipeline_order = ["LB", "App", "DB", "PGW"]
    for code in pipeline_order:
        b = blocks[code]
        a_i = float(active_avails[code])
        u_i = 1.0 - a_i
        d_h = u_i * HOURS_PER_YEAR
        d_m = d_h * 60.0
        raw_items.append({
            "code": code,
            "name": b.name,
            "tier": b.tier,
            "avail": a_i,
            "unavail": u_i,
            "d_hours": d_h,
            "d_minutes": d_m,
            "pipeline_idx": pipeline_order.index(code),
        })

    sum_d_hours = sum(item["d_hours"] for item in raw_items)

    # Sort descending by downtime; secondary sort by pipeline index for deterministic ordering
    sorted_items = sorted(
        raw_items,
        key=lambda x: (-x["d_hours"], x["pipeline_idx"]),
    )

    contributions: List[SubsystemDowntimeContribution] = []
    running_cum_pct = 0.0
    dominant_bottlenecks: List[str] = []

    for rank, item in enumerate(sorted_items, start=1):
        pct = (item["d_hours"] / sum_d_hours) * 100.0 if sum_d_hours > 0 else 0.0
        running_cum_pct += pct
        # Clip at 100.0 to prevent minor float rounding overshoot
        cum_pct = min(running_cum_pct, 100.0)

        # First-order proportional allocation of exact system downtime
        alloc_h = (item["d_hours"] / sum_d_hours) * metrics.annual_downtime_hours if sum_d_hours > 0 else 0.0

        contrib = SubsystemDowntimeContribution(
            block_code=item["code"],
            subsystem_name=item["name"],
            tier=item["tier"],
            availability=item["avail"],
            unavailability=item["unavail"],
            downtime_hours=item["d_hours"],
            downtime_minutes=item["d_minutes"],
            percentage_of_total=pct,
            cumulative_percentage=cum_pct,
            allocated_downtime_hours=alloc_h,
            rank=rank,
        )
        contributions.append(contrib)

        if cum_pct <= 80.0 or len(dominant_bottlenecks) == 0:
            dominant_bottlenecks.append(item["code"])

    # Specific shares of interest
    shares_by_code = {c.block_code: c.percentage_of_total for c in contributions}
    app_db_combined = shares_by_code.get("App", 0.0) + shares_by_code.get("DB", 0.0)
    pgw_share = shares_by_code.get("PGW", 0.0)

    return ParetoAnalysisResult(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        system_availability=metrics.system_availability,
        system_unavailability=metrics.unavailability,
        system_downtime_hours=metrics.annual_downtime_hours,
        sum_component_downtime_hours=sum_d_hours,
        contributions=contributions,
        dominant_bottlenecks=dominant_bottlenecks,
        top_contributor_code=contributions[0].block_code,
        top_contributor_share_pct=contributions[0].percentage_of_total,
        app_db_combined_share_pct=app_db_combined,
        pgw_share_pct=pgw_share,
    )


def evaluate_pareto_analysis(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Dict[str, ParetoAnalysisResult]:
    """Evaluate Pareto analysis across all three architectural scenarios.

    Returns:
        Dictionary mapping 'scenario_1', 'scenario_2', 'scenario_3' to ParetoAnalysisResult.
    """
    return {
        "scenario_1": compute_subsystem_downtime_contributions(1, blocks),
        "scenario_2": compute_subsystem_downtime_contributions(2, blocks),
        "scenario_3": compute_subsystem_downtime_contributions(3, blocks),
    }


def get_pareto_dataframe(result: ParetoAnalysisResult) -> pd.DataFrame:
    """Format a ParetoAnalysisResult into a clean pandas DataFrame for display.

    Args:
        result: ParetoAnalysisResult object.

    Returns:
        DataFrame containing formatted Pareto table.
    """
    rows = []
    for c in result.contributions:
        rows.append({
            "Rank": c.rank,
            "Block": c.block_code,
            "Subsystem Name": c.subsystem_name,
            "Tier": c.tier,
            "Availability (%)": c.availability * 100.0,
            "Unavailability (ppm)": c.unavailability * 1e6,
            "Downtime (h/yr)": c.downtime_hours,
            "Downtime (min/yr)": c.downtime_minutes,
            "Share (%)": c.percentage_of_total,
            "Cumulative (%)": c.cumulative_percentage,
            "Allocated Downtime (h/yr)": c.allocated_downtime_hours,
        })
    df = pd.DataFrame(rows)
    return df


def compute_bottleneck_shift_summary(
    results: Optional[Dict[str, ParetoAnalysisResult]] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Dict[str, float]:
    """Compute quantitative comparative metrics highlighting the architectural bottleneck shift.

    Args:
        results: Optional dictionary from evaluate_pareto_analysis. Evaluated if None.
        blocks: Block parameters dictionary.

    Returns:
        Dictionary of comparative shift metrics.
    """
    if results is None:
        results = evaluate_pareto_analysis(blocks)

    s1 = results["scenario_1"]
    s2 = results["scenario_2"]
    s3 = results["scenario_3"]

    s1_shares = {c.block_code: c for c in s1.contributions}
    s2_shares = {c.block_code: c for c in s2.contributions}
    s3_shares = {c.block_code: c for c in s3.contributions}

    app_hours_s1 = s1_shares["App"].downtime_hours
    app_hours_s2 = s2_shares["App"].downtime_hours
    app_reduction_pct = ((app_hours_s1 - app_hours_s2) / app_hours_s1) * 100.0

    db_hours_s1 = s1_shares["DB"].downtime_hours
    db_hours_s2 = s2_shares["DB"].downtime_hours
    db_reduction_pct = ((db_hours_s1 - db_hours_s2) / db_hours_s1) * 100.0

    internal_hours_s1 = app_hours_s1 + db_hours_s1
    internal_hours_s2 = app_hours_s2 + db_hours_s2
    internal_reduction_pct = ((internal_hours_s1 - internal_hours_s2) / internal_hours_s1) * 100.0

    pgw_share_s1 = s1_shares["PGW"].percentage_of_total
    pgw_share_s2 = s2_shares["PGW"].percentage_of_total
    pgw_share_increase_factor = pgw_share_s2 / pgw_share_s1 if pgw_share_s1 > 0 else 0.0

    pgw_hours_s2 = s2_shares["PGW"].downtime_hours
    pgw_hours_s3 = s3_shares["PGW"].downtime_hours
    pgw_s3_reduction_pct = ((pgw_hours_s2 - pgw_hours_s3) / pgw_hours_s2) * 100.0

    return {
        "s1_internal_share_pct": s1.app_db_combined_share_pct,
        "s2_internal_share_pct": s2.app_db_combined_share_pct,
        "s1_pgw_share_pct": pgw_share_s1,
        "s2_pgw_share_pct": pgw_share_s2,
        "s3_pgw_share_pct": s3_shares["PGW"].percentage_of_total,
        "s3_db_share_pct": s3_shares["DB"].percentage_of_total,
        "app_downtime_reduction_pct": app_reduction_pct,
        "db_downtime_reduction_pct": db_reduction_pct,
        "internal_tier_reduction_pct": internal_reduction_pct,
        "pgw_share_multiplication_factor": pgw_share_increase_factor,
        "pgw_s3_reduction_pct": pgw_s3_reduction_pct,
        "downtime_hours_saved_s2_vs_s1": s1.system_downtime_hours - s2.system_downtime_hours,
        "downtime_hours_saved_s3_vs_s2": s2.system_downtime_hours - s3.system_downtime_hours,
    }
