"""
Unit tests for Milestone 1 / Issue #2: Time-Dependent Reliability Functions R(t) and MTTF Gain.
"""

import math
from pathlib import Path
import numpy as np
import pytest

from src.models.analytical import DEFAULT_BLOCKS
from src.models.analytical_reliability import (
    calculate_component_reliability,
    calculate_parallel_reliability,
    calculate_reliability_baseline,
    calculate_reliability_redundant,
    calculate_reliability_scenario_3,
    calculate_mttf_baseline,
    calculate_mttf_redundant_closed_form,
    calculate_mttf_scenario_3_closed_form,
    evaluate_mttf_metrics,
    plot_reliability_curves,
)


def test_component_reliability_properties():
    """Verify component reliability R_i(t) boundary conditions and exponential decay."""
    lam = 0.01  # failure rate = 0.01 h^-1

    # Boundary conditions
    assert math.isclose(calculate_component_reliability(lam, 0.0), 1.0, abs_tol=1e-12)
    assert calculate_component_reliability(lam, 10000.0) < 1e-15

    # Characteristic lifetime t = 1/lambda => R(1/lambda) = 1/e
    assert math.isclose(
        calculate_component_reliability(lam, 1.0 / lam),
        1.0 / math.e,
        rel_tol=1e-9,
    )

    # Monotonic decrease over array
    t_arr = np.linspace(0, 100, 50)
    r_arr = calculate_component_reliability(lam, t_arr)
    assert np.all(np.diff(r_arr) <= 0)


def test_parallel_reliability_properties():
    """Verify active 1-out-of-2 parallel redundancy survival probability."""
    lam = 0.01
    t = 50.0

    r_single = calculate_component_reliability(lam, t)
    r_par = calculate_parallel_reliability(lam, t, n_units=2)

    # Analytical formula: 1 - (1 - R)^2 = 2R - R^2
    expected = 2.0 * r_single - (r_single ** 2)
    assert math.isclose(r_par, expected, rel_tol=1e-9)

    # Redundancy must strictly increase reliability for t > 0
    assert r_par > r_single
    assert math.isclose(calculate_parallel_reliability(lam, 0.0), 1.0, abs_tol=1e-12)


def test_baseline_reliability_scenario_1():
    """Verify Scenario 1 (Pure Series) reliability curve R_base(t)."""
    # At t = 0, R_base(0) = 1
    assert math.isclose(calculate_reliability_baseline(0.0), 1.0, abs_tol=1e-12)

    # At t = MTTF_base, R_base(MTTF_base) = 1/e
    mttf_base = calculate_mttf_baseline()
    r_at_mttf = float(calculate_reliability_baseline(mttf_base))
    assert math.isclose(r_at_mttf, 1.0 / math.e, rel_tol=1e-6)

    # Series reliability is product of all 4 component reliabilities
    t_test = 24.0
    r_prod = np.prod([
        calculate_component_reliability(b.lambda_base, t_test)
        for b in DEFAULT_BLOCKS.values()
    ])
    assert math.isclose(calculate_reliability_baseline(t_test), r_prod, rel_tol=1e-9)


def test_redundant_reliability_scenario_2():
    """Verify Scenario 2 (Multi-AZ Series-Parallel) reliability curve R_red(t)."""
    # At t = 0, R_red(0) = 1
    assert math.isclose(calculate_reliability_redundant(0.0), 1.0, abs_tol=1e-12)

    # For any t > 0, R_red(t) must be strictly greater than R_base(t)
    times = np.linspace(1.0, 500.0, 100)
    r_base_vals = calculate_reliability_baseline(times)
    r_red_vals = calculate_reliability_redundant(times)
    assert np.all(r_red_vals > r_base_vals)

    # Verify at t = 24h (1 day) and t = 168h (1 week)
    r_base_24 = float(calculate_reliability_baseline(24.0))
    r_red_24 = float(calculate_reliability_redundant(24.0))
    assert r_red_24 > r_base_24
    assert r_red_24 > 0.85  # Multi-AZ sustains much higher 24h reliability


def test_mttf_baseline_exact_value():
    """Verify closed-form MTTF_base = 1 / sum(lambda_i)."""
    mttf_base = calculate_mttf_baseline()

    # Theoretical sum of failure rates
    lambda_sum = sum(b.lambda_base for b in DEFAULT_BLOCKS.values())
    assert math.isclose(mttf_base, 1.0 / lambda_sum, rel_tol=1e-12)

    # Expected value around 60.69 hours
    assert math.isclose(mttf_base, 60.6946, abs_tol=1e-3)
    assert round(mttf_base, 2) == 60.69


def test_mttf_redundant_closed_form():
    """Verify algebraic expansion of R_red(t) and exact closed-form 4-term MTTF_red."""
    l1 = DEFAULT_BLOCKS["LB"].lambda_base
    l2 = DEFAULT_BLOCKS["App"].lambda_base
    l3 = DEFAULT_BLOCKS["DB"].lambda_base
    l4 = DEFAULT_BLOCKS["PGW"].lambda_base

    g1 = l1 + l2 + l3 + l4
    g2 = l1 + 2.0 * l2 + l3 + l4
    g3 = l1 + l2 + 2.0 * l3 + l4
    g4 = l1 + 2.0 * l2 + 2.0 * l3 + l4

    # Algebraic equivalence between factored R_red(t) and 4 exponential terms
    times = np.linspace(0.0, 500.0, 100)
    r_factored = calculate_reliability_redundant(times)
    r_expanded = 4.0 * np.exp(-g1 * times) - 2.0 * np.exp(-g2 * times) - 2.0 * np.exp(-g3 * times) + np.exp(-g4 * times)
    np.testing.assert_allclose(r_factored, r_expanded, rtol=1e-12, atol=1e-12)

    mttf_closed = calculate_mttf_redundant_closed_form()
    expected_mttf = 4.0 / g1 - 2.0 / g2 - 2.0 / g3 + 1.0 / g4
    assert math.isclose(mttf_closed, expected_mttf, rel_tol=1e-12)

    # Expected value around 106.06 hours
    assert math.isclose(mttf_closed, 106.0570, abs_tol=1e-3)
    assert round(mttf_closed, 2) == 106.06


def test_mttf_gain_and_multiplication_factor():
    """Verify analytical MTTF gain: ~74.74% improvement and 1.75x factor."""
    metrics = evaluate_mttf_metrics()

    # Delta MTTF
    expected_delta = metrics.mttf_red_hours - metrics.mttf_base_hours
    assert math.isclose(metrics.delta_mttf_hours, expected_delta, rel_tol=1e-12)
    assert math.isclose(metrics.delta_mttf_hours, 45.3624, abs_tol=1e-3)
    assert round(metrics.delta_mttf_hours, 2) == 45.36

    # Percentage improvement ~ 74.74%
    assert math.isclose(metrics.mttf_gain_pct, 74.7387, abs_tol=1e-2)
    assert round(metrics.mttf_gain_pct, 2) == 74.74

    # Ratio / Multiplication factor ~ 1.7474x
    assert math.isclose(metrics.mttf_gain_factor, 1.7474, abs_tol=1e-3)


def test_scenario_3_reliability_and_mttf():
    """Verify Scenario 3 (Multi-Gateway) 8-term expansion and MTTF extension."""
    l1 = DEFAULT_BLOCKS["LB"].lambda_base
    l2 = DEFAULT_BLOCKS["App"].lambda_base
    l3 = DEFAULT_BLOCKS["DB"].lambda_base
    l4 = DEFAULT_BLOCKS["PGW"].lambda_base

    # Algebraic equivalence between factored R_scen3(t) and 8 exponential terms
    times = np.linspace(0.0, 500.0, 100)
    r_factored = calculate_reliability_scenario_3(times)
    r_expanded = (
        8.0 * np.exp(-(l1 + l2 + l3 + l4) * times)
        - 4.0 * np.exp(-(l1 + 2.0 * l2 + l3 + l4) * times)
        - 4.0 * np.exp(-(l1 + l2 + 2.0 * l3 + l4) * times)
        - 4.0 * np.exp(-(l1 + l2 + l3 + 2.0 * l4) * times)
        + 2.0 * np.exp(-(l1 + 2.0 * l2 + 2.0 * l3 + l4) * times)
        + 2.0 * np.exp(-(l1 + 2.0 * l2 + l3 + 2.0 * l4) * times)
        + 2.0 * np.exp(-(l1 + l2 + 2.0 * l3 + 2.0 * l4) * times)
        - np.exp(-(l1 + 2.0 * l2 + 2.0 * l3 + 2.0 * l4) * times)
    )
    np.testing.assert_allclose(r_factored, r_expanded, rtol=1e-12, atol=1e-12)

    mttf_s3_closed = calculate_mttf_scenario_3_closed_form()

    # Expected value around 114.05 hours
    assert math.isclose(mttf_s3_closed, 114.0535, abs_tol=1e-3)
    assert round(mttf_s3_closed, 2) == 114.05

    # Hierarchy: MTTF_base < MTTF_red < MTTF_scen3
    metrics = evaluate_mttf_metrics()
    assert metrics.mttf_base_hours < metrics.mttf_red_hours < metrics.mttf_scen3_hours
    assert math.isclose(metrics.mttf_gain_scen3_pct, 87.91, abs_tol=0.1)


def test_reliability_vector_graphics_export(tmp_path: Path):
    """Verify export of publication-grade PDF and PNG (>= 300 DPI) curves."""
    fig = plot_reliability_curves(output_dir=tmp_path)
    assert fig is not None

    pdf_file = tmp_path / "reliability_curves_comparison.pdf"
    png_file = tmp_path / "reliability_curves_comparison.png"

    assert pdf_file.is_file()
    assert png_file.is_file()
    assert pdf_file.stat().st_size > 10_000
    assert png_file.stat().st_size > 50_000
