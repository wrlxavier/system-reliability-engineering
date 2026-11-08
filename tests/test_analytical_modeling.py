"""
Unit tests for Milestone 1 / Issue #1: Analytical Modeling and RBD Formulations.
"""

import math
from pathlib import Path
import pytest

from src.models.analytical import (
    DEFAULT_BLOCKS,
    HOURS_PER_YEAR,
    calculate_series_availability,
    calculate_parallel_availability,
    calculate_downtime_hours,
    calculate_downtime_minutes,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
    get_all_scenarios_summary,
)
from src.visualization.draw_rbd import (
    draw_rbd_scenario_1,
    draw_rbd_scenario_2,
    draw_rbd_scenario_3,
    draw_rbd_comparison_all,
)


def test_nominal_blocks_definitions():
    """Verify that all four required subsystems are defined with correct nominal parameters."""
    assert set(DEFAULT_BLOCKS.keys()) == {"LB", "App", "DB", "PGW"}

    # Load Balancer
    assert DEFAULT_BLOCKS["LB"].availability_base == 0.9999
    assert math.isclose(DEFAULT_BLOCKS["LB"].annual_downtime_hours_base, 0.876, rel_tol=1e-3)

    # Application
    assert DEFAULT_BLOCKS["App"].availability_base == 0.9950
    assert DEFAULT_BLOCKS["App"].availability_redundant == 0.9999
    assert math.isclose(DEFAULT_BLOCKS["App"].annual_downtime_hours_base, 43.80, rel_tol=1e-3)

    # Database
    assert DEFAULT_BLOCKS["DB"].availability_base == 0.9950
    assert DEFAULT_BLOCKS["DB"].availability_redundant == 0.9995
    assert math.isclose(DEFAULT_BLOCKS["DB"].annual_downtime_hours_base, 43.80, rel_tol=1e-3)

    # Payment Gateway
    assert DEFAULT_BLOCKS["PGW"].availability_base == 0.9995
    assert DEFAULT_BLOCKS["PGW"].availability_redundant == 0.99999975
    assert math.isclose(DEFAULT_BLOCKS["PGW"].annual_downtime_hours_base, 4.38, rel_tol=1e-3)


def test_series_parallel_formula_primitives():
    """Test pure series and parallel mathematical helper routines."""
    # Series of 0.99 and 0.99 => 0.9801
    assert math.isclose(calculate_series_availability([0.99, 0.99]), 0.9801, rel_tol=1e-6)

    # Parallel active of two 0.99 units => 1 - (0.01)^2 = 0.9999
    assert math.isclose(calculate_parallel_availability([0.99, 0.99]), 0.9999, rel_tol=1e-6)

    # Downtime
    # 99% availability => 1% of 8760 = 87.6 hours
    assert math.isclose(calculate_downtime_hours(0.99), 87.6, rel_tol=1e-6)
    assert math.isclose(calculate_downtime_minutes(0.99), 87.6 * 60, rel_tol=1e-6)


def test_scenario_1_analytical_metrics():
    """Verify Scenario 1 (Pure Series) metrics against Issue #1 criteria.

    A_base = 0.9999 * 0.9950 * 0.9950 * 0.9995 = 98.943%
    Downtime = 92.58 h/year
    """
    s1 = evaluate_scenario_1()
    assert math.isclose(s1.system_availability, 0.989431, abs_tol=1e-5)
    assert round(s1.system_availability * 100, 3) == 98.943
    assert math.isclose(s1.annual_downtime_hours, 92.584, abs_tol=1e-2)
    assert round(s1.annual_downtime_hours, 2) == 92.58


def test_scenario_2_analytical_metrics():
    """Verify Scenario 2 (Multi-AZ Series-Parallel) metrics against Issue #1 criteria.

    A_red = 0.9999 * 0.9999 * 0.9995 * 0.9995 = 99.880%
    Downtime = 10.51 h/year
    Downtime reduction ~ 88.6%
    """
    s2 = evaluate_scenario_2()
    assert math.isclose(s2.system_availability, 0.998800, abs_tol=1e-5)
    assert round(s2.system_availability * 100, 3) == 99.880
    assert math.isclose(s2.annual_downtime_hours, 10.508, abs_tol=1e-2)
    assert round(s2.annual_downtime_hours, 2) == 10.51
    assert math.isclose(s2.relative_reduction_vs_baseline_pct, 88.65, abs_tol=0.1)


def test_scenario_3_analytical_metrics():
    """Verify Scenario 3 (Multi-Gateway Expansion) metrics.

    A_scen3 = 0.9999 * 0.9999 * 0.9995 * 0.99999975 = 99.930%
    Downtime = 6.13 h/year
    """
    s3 = evaluate_scenario_3()
    assert math.isclose(s3.system_availability, 0.999300, abs_tol=1e-5)
    assert round(s3.system_availability * 100, 3) == 99.930
    assert math.isclose(s3.annual_downtime_hours, 6.133, abs_tol=1e-2)
    assert round(s3.annual_downtime_hours, 2) == 6.13
    assert math.isclose(s3.relative_reduction_vs_baseline_pct, 93.38, abs_tol=0.1)


def test_all_scenarios_summary():
    """Verify monotonic availability increase and downtime reduction across scenarios."""
    summaries = get_all_scenarios_summary()
    assert len(summaries) == 3

    # Availability must strictly increase: A_s1 < A_s2 < A_s3
    assert summaries[0].system_availability < summaries[1].system_availability < summaries[2].system_availability

    # Downtime must strictly decrease: D_s1 > D_s2 > D_s3
    assert summaries[0].annual_downtime_hours > summaries[1].annual_downtime_hours > summaries[2].annual_downtime_hours


def test_vector_graphics_generated_files(tmp_path):
    """Verify that vector graphics (.pdf) and 300 DPI images (.png) are properly exported."""
    fig1 = draw_rbd_scenario_1(output_dir=tmp_path)
    assert (tmp_path / "rbd_scenario_1.pdf").is_file()
    assert (tmp_path / "rbd_scenario_1.png").is_file()
    assert (tmp_path / "rbd_scenario_1.png").stat().st_size > 50_000

    fig2 = draw_rbd_scenario_2(output_dir=tmp_path)
    assert (tmp_path / "rbd_scenario_2.pdf").is_file()
    assert (tmp_path / "rbd_scenario_2.png").is_file()

    fig3 = draw_rbd_scenario_3(output_dir=tmp_path)
    assert (tmp_path / "rbd_scenario_3.pdf").is_file()
    assert (tmp_path / "rbd_scenario_3.png").is_file()

    fig_all = draw_rbd_comparison_all(output_dir=tmp_path)
    assert (tmp_path / "rbd_comparison_all.pdf").is_file()
    assert (tmp_path / "rbd_comparison_all.png").is_file()
