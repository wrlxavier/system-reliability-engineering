"""
Tests for Scenario 3 Expansion, Payment Gateway Redundancy, and Sensitivity Analysis.
"""

import math
from pathlib import Path
import numpy as np
import pytest

from src.models.analytical import (
    DEFAULT_BLOCKS,
    HOURS_PER_YEAR,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
)
from src.models.sensitivity import (
    get_internal_redundant_availability,
    evaluate_gateway_availability_sensitivity,
    evaluate_failover_coverage_sensitivity,
    evaluate_common_cause_failure_sensitivity,
    compute_diminishing_returns_metrics,
)
from src.visualization.plot_sensitivity import (
    plot_gateway_sla_sensitivity,
    plot_failover_and_ccf_sensitivity,
    plot_architectural_diminishing_returns,
    generate_all_sensitivity_diagrams,
)


def test_scenario_3_mathematical_equating():
    """Verify active parallel redundancy equational values for the payment gateway.

    A_4 = 0.9995
    A_4,red = 1 - (1 - A_4)^2 = 1 - (0.0005)^2 = 0.99999975 (99.999975%)
    Downtime_4,red = 0.00000025 * 8760 = 0.00219 h/yr (~7.88 seconds/year)
    """
    s3 = evaluate_scenario_3()

    # Gateway redundant availability
    a_pgw_red = s3.block_availabilities["PGW"]
    assert math.isclose(a_pgw_red, 0.99999975, abs_tol=1e-8)
    assert f"{a_pgw_red * 100:.6f}" == "99.999975"

    # Gateway redundant downtime
    d_pgw_red = (1.0 - a_pgw_red) * HOURS_PER_YEAR
    assert math.isclose(d_pgw_red, 0.00219, abs_tol=1e-4)

    # Full system availability: A_scen3 = 0.9999 * 0.9999 * 0.9995 * 0.99999975
    expected_a3 = 0.9999 * 0.9999 * 0.9995 * 0.99999975
    assert math.isclose(s3.system_availability, expected_a3, abs_tol=1e-8)
    assert math.isclose(s3.system_availability, 0.99929986, abs_tol=1e-6)
    assert round(s3.system_availability * 100, 3) == 99.930

    # System annual downtime: 6.13 h/year
    assert math.isclose(s3.annual_downtime_hours, 6.1332, abs_tol=1e-3)
    assert round(s3.annual_downtime_hours, 2) == 6.13

    # Downtime reductions
    s1 = evaluate_scenario_1()
    s2 = evaluate_scenario_2()
    saved_vs_s1 = s1.annual_downtime_hours - s3.annual_downtime_hours
    saved_vs_s2 = s2.annual_downtime_hours - s3.annual_downtime_hours

    assert math.isclose(saved_vs_s1, 86.45, abs_tol=0.05)
    assert math.isclose(saved_vs_s2, 4.37, abs_tol=0.05)
    assert math.isclose(s3.relative_reduction_vs_baseline_pct, 93.38, abs_tol=0.05)


def test_internal_redundant_availability():
    """Verify internal tier availability (LB * App_red * DB_red)."""
    a_int = get_internal_redundant_availability()
    expected = 0.9999 * 0.9999 * 0.9995
    assert math.isclose(a_int, expected, abs_tol=1e-8)
    assert math.isclose(a_int, 0.99930015, abs_tol=1e-6)


def test_gateway_sla_sensitivity_sweep():
    """Verify gateway SLA sensitivity behavior across commercial availability levels."""
    grid = [0.990, 0.995, 0.999, 0.9995, 0.9999]
    df = evaluate_gateway_availability_sensitivity(gateway_availabilities=grid)

    assert len(df) == 5
    assert list(df.columns) == [
        "gateway_sla",
        "gateway_sla_pct",
        "gateway_downtime_single_h",
        "gateway_downtime_dual_h",
        "scenario_2_availability_pct",
        "scenario_2_downtime_h",
        "scenario_3_availability_pct",
        "scenario_3_downtime_h",
        "downtime_saved_h",
        "relative_reduction_pct",
        "downtime_ratio_s2_over_s3",
    ]

    # Monotonicity checks
    # As gateway SLA increases, downtime must strictly decrease in both scenarios
    assert (df["scenario_2_downtime_h"].diff().dropna() < 0).all()
    assert (df["scenario_3_downtime_h"].diff().dropna() < 0).all()

    # Scenario 3 downtime must strictly be lower than Scenario 2 downtime
    assert (df["scenario_3_downtime_h"] < df["scenario_2_downtime_h"]).all()

    # Dual gateway downtime must be much smaller than single gateway downtime
    assert (df["gateway_downtime_dual_h"] < df["gateway_downtime_single_h"]).all()

    # At nominal point A_4 = 0.9995:
    nom_row = df[df["gateway_sla"] == 0.9995].iloc[0]
    assert math.isclose(nom_row["scenario_2_downtime_h"], 10.508, abs_tol=1e-2)
    assert math.isclose(nom_row["scenario_3_downtime_h"], 6.133, abs_tol=1e-2)
    assert math.isclose(nom_row["downtime_saved_h"], 4.375, abs_tol=1e-2)
    assert math.isclose(nom_row["relative_reduction_pct"], 41.63, abs_tol=0.1)


def test_failover_coverage_sensitivity():
    """Verify sensitivity to imperfect failover switching coverage."""
    coverages = [0.80, 0.90, 0.95, 0.99, 1.00]
    df = evaluate_failover_coverage_sensitivity(coverage_probabilities=coverages)

    assert len(df) == 5

    # As failover coverage increases:
    # Effective gateway downtime must strictly decrease
    assert (df["gateway_downtime_h"].diff().dropna() < 0).all()
    # System downtime must strictly decrease
    assert (df["system_downtime_h"].diff().dropna() < 0).all()

    # At perfect switching (C = 1.00), downtime equals nominal S3 downtime
    row_ideal = df[df["coverage_probability"] == 1.00].iloc[0]
    assert math.isclose(row_ideal["system_downtime_h"], 6.133, abs_tol=1e-2)
    assert math.isclose(row_ideal["gateway_downtime_h"], 0.00219, abs_tol=1e-3)

    # Even at 90% switching coverage, downtime saved is > 3.9 hours/year
    row_90 = df[df["coverage_probability"] == 0.90].iloc[0]
    assert row_90["downtime_saved_vs_s2_h"] > 3.9


def test_common_cause_failure_sensitivity():
    """Verify vulnerability to Common-Cause Failures (CCF) using the beta-factor model."""
    betas = [0.00, 0.02, 0.05, 0.10, 0.20]
    df = evaluate_common_cause_failure_sensitivity(beta_factors=betas)

    assert len(df) == 5

    # As beta increases, effective gateway downtime and system downtime strictly increase
    assert (df["gateway_downtime_h"].diff().dropna() > 0).all()
    assert (df["system_downtime_h"].diff().dropna() > 0).all()

    # At beta = 0 (perfect independence), system downtime matches nominal S3
    row_indep = df[df["beta_ccf"] == 0.00].iloc[0]
    assert math.isclose(row_indep["system_downtime_h"], 6.133, abs_tol=1e-2)
    assert math.isclose(row_indep["gateway_downtime_h"], 0.00219, abs_tol=1e-3)


def test_diminishing_returns_metrics():
    """Verify diminishing returns quantification and Amdahl's Law in reliability."""
    df = compute_diminishing_returns_metrics()

    assert len(df) == 4

    # Downtime saved S1 -> S2 vs S2 -> S3
    saved_s1_s2 = df.loc[df["Step"] == "Multi-AZ Core (Scenario 2)", "Downtime Saved vs Previous (h/yr)"].values[0]
    saved_s2_s3 = df.loc[df["Step"] == "Multi-Gateway (Scenario 3)", "Downtime Saved vs Previous (h/yr)"].values[0]

    assert saved_s1_s2 > 80.0  # 82.08 h
    assert 4.0 < saved_s2_s3 < 5.0  # 4.37 h
    assert saved_s1_s2 > 18 * saved_s2_s3  # More than 18x larger gain in S2 than S3


def test_sensitivity_diagrams_generation(tmp_path: Path):
    """Verify export of publication-grade PDF and PNG vector/raster graphics."""
    fig1 = plot_gateway_sla_sensitivity(output_dir=tmp_path)
    assert (tmp_path / "gateway_sla_sensitivity.pdf").is_file()
    assert (tmp_path / "gateway_sla_sensitivity.png").is_file()
    assert (tmp_path / "gateway_sla_sensitivity.png").stat().st_size > 50_000

    fig2 = plot_failover_and_ccf_sensitivity(output_dir=tmp_path)
    assert (tmp_path / "failover_and_ccf_sensitivity.pdf").is_file()
    assert (tmp_path / "failover_and_ccf_sensitivity.png").is_file()
    assert (tmp_path / "failover_and_ccf_sensitivity.png").stat().st_size > 50_000

    fig3 = plot_architectural_diminishing_returns(output_dir=tmp_path)
    assert (tmp_path / "scenario_3_diminishing_returns.pdf").is_file()
    assert (tmp_path / "scenario_3_diminishing_returns.png").is_file()
    assert (tmp_path / "scenario_3_diminishing_returns.png").stat().st_size > 30_000

    diagrams = generate_all_sensitivity_diagrams(output_dir=tmp_path)
    assert len(diagrams) == 3
