"""
Unit tests for Subsystem Percentage Unavailability Contribution and Bottleneck Identification.
"""

import math
from pathlib import Path
import pytest

from src.models.subsystem_contribution import (
    SubsystemDowntimeContribution,
    SubsystemContributionResult,
    compute_subsystem_downtime_contributions,
    evaluate_subsystem_contributions,
    get_subsystem_contribution_dataframe,
    compute_bottleneck_shift_summary,
)
from src.visualization.plot_subsystem_contribution import (
    plot_subsystem_downtime_contribution,
    plot_subsystem_contribution_single_scenario,
    plot_subsystem_contribution_all_scenarios,
    generate_all_subsystem_contribution_diagrams,
)


def test_subsystem_contribution_scenario_1():
    """Verify subsystem ordering, downtime values, and percentage shares for Scenario 1."""
    res = compute_subsystem_downtime_contributions(1)

    assert isinstance(res, SubsystemContributionResult)
    assert res.scenario_id == 1
    assert len(res.contributions) == 4
    assert isinstance(res.contributions[0], SubsystemDowntimeContribution)

    # Baseline pure series system downtime: ~92.58 h/yr
    assert math.isclose(res.system_downtime_hours, 92.584138, rel_tol=1e-4)

    # Sum of component downtime: 43.8 + 43.8 + 4.38 + 0.876 = 92.856 h/yr
    assert math.isclose(res.sum_component_downtime_hours, 92.856, rel_tol=1e-5)

    # Top contributors are App and DB (each 43.8 h)
    codes = [c.block_code for c in res.contributions]
    assert set(codes[:2]) == {"App", "DB"}
    assert set(res.primary_bottlenecks) == {"App", "DB"}
    assert codes[2] == "PGW"
    assert codes[3] == "LB"

    c_app = next(c for c in res.contributions if c.block_code == "App")
    c_db = next(c for c in res.contributions if c.block_code == "DB")
    c_pgw = next(c for c in res.contributions if c.block_code == "PGW")
    c_lb = next(c for c in res.contributions if c.block_code == "LB")

    assert math.isclose(c_app.downtime_hours, 43.800, rel_tol=1e-4)
    assert math.isclose(c_db.downtime_hours, 43.800, rel_tol=1e-4)
    assert math.isclose(c_pgw.downtime_hours, 4.380, rel_tol=1e-4)
    assert math.isclose(c_lb.downtime_hours, 0.876, rel_tol=1e-4)

    assert math.isclose(c_app.percentage_of_total, (43.8 / 92.856) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_db.percentage_of_total, (43.8 / 92.856) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_pgw.percentage_of_total, (4.38 / 92.856) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_lb.percentage_of_total, (0.876 / 92.856) * 100.0, rel_tol=1e-4)

    # Combined App + DB accounts for > 94% of downtime
    assert res.app_db_combined_share_pct > 94.0
    assert math.isclose(res.app_db_combined_share_pct, 94.3396, rel_tol=1e-2)

    # Cumulative sum reaches exactly 100%
    assert math.isclose(res.contributions[-1].cumulative_percentage, 100.0, abs_tol=1e-5)

    # Proportional allocated downtime sums to exact system downtime
    allocated_sum = sum(c.allocated_downtime_hours for c in res.contributions)
    assert math.isclose(allocated_sum, res.system_downtime_hours, rel_tol=1e-6)


def test_subsystem_contribution_scenario_2():
    """Verify subsystem ordering, downtime values, and percentage shares for Scenario 2."""
    res = compute_subsystem_downtime_contributions(2)

    assert res.scenario_id == 2
    assert len(res.contributions) == 4

    # Multi-AZ redundant system downtime: ~10.51 h/yr
    assert math.isclose(res.system_downtime_hours, 10.507971, rel_tol=1e-4)

    # Sum of component downtime: 4.38 (DB) + 4.38 (PGW) + 0.876 (LB) + 0.876 (App) = 10.512 h/yr
    assert math.isclose(res.sum_component_downtime_hours, 10.512, rel_tol=1e-5)

    # Top contributors in Scenario 2 are DB and PGW
    codes = [c.block_code for c in res.contributions]
    assert set(codes[:2]) == {"DB", "PGW"}
    assert set(res.primary_bottlenecks) == {"DB", "PGW"}
    assert set(codes[2:]) == {"LB", "App"}

    c_db = next(c for c in res.contributions if c.block_code == "DB")
    c_pgw = next(c for c in res.contributions if c.block_code == "PGW")
    c_app = next(c for c in res.contributions if c.block_code == "App")
    c_lb = next(c for c in res.contributions if c.block_code == "LB")

    assert math.isclose(c_db.downtime_hours, 4.380, rel_tol=1e-4)
    assert math.isclose(c_pgw.downtime_hours, 4.380, rel_tol=1e-4)
    assert math.isclose(c_app.downtime_hours, 0.876, rel_tol=1e-4)
    assert math.isclose(c_lb.downtime_hours, 0.876, rel_tol=1e-4)

    # Shares: DB and PGW each represent ~41.67% of downtime
    assert math.isclose(c_db.percentage_of_total, (4.38 / 10.512) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_pgw.percentage_of_total, (4.38 / 10.512) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_app.percentage_of_total, (0.876 / 10.512) * 100.0, rel_tol=1e-4)
    assert math.isclose(c_lb.percentage_of_total, (0.876 / 10.512) * 100.0, rel_tol=1e-4)

    # DB + PGW combined account for > 83% of remaining downtime
    assert (c_db.percentage_of_total + c_pgw.percentage_of_total) > 83.0

    # Cumulative percentage reaches 100%
    assert math.isclose(res.contributions[-1].cumulative_percentage, 100.0, abs_tol=1e-5)

    # Proportional allocated downtime sums to exact system downtime
    allocated_sum = sum(c.allocated_downtime_hours for c in res.contributions)
    assert math.isclose(allocated_sum, res.system_downtime_hours, rel_tol=1e-6)


def test_subsystem_contribution_scenario_3():
    """Verify Scenario 3 downtime contributions with multi-gateway redundancy."""
    res = compute_subsystem_downtime_contributions(3)

    assert res.scenario_id == 3
    assert len(res.contributions) == 4
    assert res.primary_bottlenecks == ["DB"]

    # System downtime: ~6.13 h/yr
    assert math.isclose(res.system_downtime_hours, 6.133225, rel_tol=1e-4)

    c_pgw = next(c for c in res.contributions if c.block_code == "PGW")
    c_db = next(c for c in res.contributions if c.block_code == "DB")

    # Dual-active PGW downtime is negligible (~7.88 seconds/year = 0.00219 h)
    assert math.isclose(c_pgw.downtime_hours, 0.00219, rel_tol=1e-3)
    assert c_pgw.percentage_of_total < 0.1

    # DB is the primary bottleneck (~71.4% of downtime)
    assert c_db.percentage_of_total > 70.0
    assert math.isclose(c_db.percentage_of_total, (4.38 / res.sum_component_downtime_hours) * 100.0, rel_tol=1e-4)


def test_bottleneck_shift_metrics():
    """Verify quantitative metrics of architectural bottleneck shift."""
    summary = compute_bottleneck_shift_summary()

    # App downtime reduction: 43.8h -> 0.876h (-98.0%)
    assert math.isclose(summary["app_downtime_reduction_pct"], 98.0, rel_tol=1e-3)

    # DB downtime reduction: 43.8h -> 4.38h (-90.0%)
    assert math.isclose(summary["db_downtime_reduction_pct"], 90.0, rel_tol=1e-3)

    # Internal tiers (App + DB) reduction: 87.6h -> 5.256h (-94.0%)
    assert math.isclose(summary["internal_tier_reduction_pct"], 94.0, rel_tol=1e-3)

    # PGW share of downtime increases ~8.8x in relative terms (from 4.7% to 41.7%)
    assert summary["pgw_share_multiplication_factor"] > 8.0
    assert math.isclose(summary["s2_pgw_share_pct"], 41.6666, rel_tol=1e-2)

    # Downtime hours saved S2 vs S1: ~82.08 hours
    assert math.isclose(summary["downtime_hours_saved_s2_vs_s1"], 82.076, rel_tol=1e-3)


def test_subsystem_contribution_dataframe_generation():
    """Verify that get_subsystem_contribution_dataframe creates valid table structures."""
    res = compute_subsystem_downtime_contributions(1)
    df = get_subsystem_contribution_dataframe(res)

    assert len(df) == 4
    expected_cols = [
        "Rank", "Block", "Subsystem Name", "Tier", "Availability (%)",
        "Unavailability (ppm)", "Downtime (h/yr)", "Downtime (min/yr)",
        "Share (%)", "Cumulative (%)", "Allocated Downtime (h/yr)"
    ]
    assert list(df.columns) == expected_cols
    assert df["Cumulative (%)"].iloc[-1] == 100.0


def test_invalid_scenario_id_raises():
    """Verify that invalid scenario IDs raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        compute_subsystem_downtime_contributions(0)
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        compute_subsystem_downtime_contributions(4)


def test_subsystem_contribution_figures_generation(tmp_path: Path):
    """Verify all subsystem contribution figures export cleanly to PDF and PNG."""
    generate_all_subsystem_contribution_diagrams(output_dir=tmp_path)

    expected_files = [
        "subsystem_downtime_contribution.pdf",
        "subsystem_downtime_contribution.png",
        "subsystem_contribution_scenario_1.pdf",
        "subsystem_contribution_scenario_1.png",
        "subsystem_contribution_scenario_2.pdf",
        "subsystem_contribution_scenario_2.png",
        "subsystem_contribution_scenario_3.pdf",
        "subsystem_contribution_scenario_3.png",
        "subsystem_contribution_comparison_all.pdf",
        "subsystem_contribution_comparison_all.png",
    ]

    for fname in expected_files:
        fpath = tmp_path / fname
        assert fpath.exists(), f"File {fname} was not created."
        assert fpath.stat().st_size > 0, f"File {fname} is empty."
