"""
Analytical Time-Dependent Reliability Modeling and MTTF Gain Derivation.

This module provides closed-form equations, mission reliability functions R(t),
analytical integrals for Mean Time to Failure (MTTF), and visualization routines
for the Systems Reliability Engineering project (Milestone 1, Issue #2).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate

from src.models.analytical import DEFAULT_BLOCKS, BlockParameters, HOURS_PER_YEAR


@dataclass
class MTTFMetrics:
    """Consolidated summary of analytical Mean Time to Failure (MTTF) metrics.

    Attributes:
        mttf_base_hours: Baseline pure series MTTF in hours (1 / sum(lambda_i)).
        mttf_red_hours: Multi-AZ series-parallel MTTF in hours (closed-form integral).
        delta_mttf_hours: Absolute MTTF increase in hours (MTTF_red - MTTF_base).
        mttf_gain_pct: Percentage MTTF improvement vs baseline ((delta / MTTF_base) * 100).
        mttf_gain_factor: Ratio of MTTF_red / MTTF_base.
        mttf_scen3_hours: Scenario 3 Multi-Gateway MTTF in hours.
        mttf_gain_scen3_pct: Percentage MTTF improvement for Scenario 3 vs baseline.
    """
    mttf_base_hours: float
    mttf_red_hours: float
    delta_mttf_hours: float
    mttf_gain_pct: float
    mttf_gain_factor: float
    mttf_scen3_hours: float
    mttf_gain_scen3_pct: float


def calculate_component_reliability(
    lambda_val: float,
    t: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """Calculate the survival probability R_i(t) under constant hazard rate lambda.

    Formula:
        R_i(t) = exp(-lambda_i * t)

    Args:
        lambda_val: Constant failure rate in failures/hour.
        t: Time horizon in hours (scalar or numpy array).

    Returns:
        Survival probability R_i(t) in [0, 1].
    """
    return np.exp(-lambda_val * t)


def calculate_parallel_reliability(
    lambda_val: float,
    t: Union[float, np.ndarray],
    n_units: int = 2,
) -> Union[float, np.ndarray]:
    """Calculate the survival probability of an active 1-out-of-n parallel subsystem.

    Assuming identical and statistically independent units:
        R_parallel(t) = 1 - (1 - R_i(t))^n

    For n = 2:
        R_parallel(t) = 2 * exp(-lambda * t) - exp(-2 * lambda * t)

    Args:
        lambda_val: Constant failure rate of an individual component in failures/hour.
        t: Time horizon in hours (scalar or numpy array).
        n_units: Number of active parallel units (default: 2).

    Returns:
        Subsystem survival probability R_parallel(t) in [0, 1].
    """
    r_single = calculate_component_reliability(lambda_val, t)
    return 1.0 - (1.0 - r_single) ** n_units


def calculate_reliability_baseline(
    t: Union[float, np.ndarray],
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Union[float, np.ndarray]:
    """Calculate Scenario 1 (Pure Series) reliability function R_base(t).

    Under independent blocks in series:
        R_base(t) = prod_{i=1}^4 R_i(t) = exp(-sum_{i=1}^4 lambda_i * t)

    Args:
        t: Time horizon in hours (scalar or numpy array).
        blocks: Dictionary of BlockParameters.

    Returns:
        Baseline system reliability R_base(t).
    """
    lambda_sum = sum(b.lambda_base for b in blocks.values())
    return np.exp(-lambda_sum * t)


def calculate_reliability_redundant(
    t: Union[float, np.ndarray],
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Union[float, np.ndarray]:
    """Calculate Scenario 2 (Multi-AZ Series-Parallel) reliability function R_red(t).

    Topology:
        LB (series) -> App (parallel 1-out-of-2) -> DB (parallel 1-out-of-2) -> PGW (series)

    Formula:
        R_red(t) = R_LB(t) * R_App,red(t) * R_DB,red(t) * R_PGW(t)
        R_red(t) = exp(-(lambda_1 + lambda_4) * t) *
                   (2 * exp(-lambda_2 * t) - exp(-2 * lambda_2 * t)) *
                   (2 * exp(-lambda_3 * t) - exp(-2 * lambda_3 * t))

    Expanded closed-form:
        R_red(t) = 4*exp(-gamma_1*t) - 2*exp(-gamma_2*t) - 2*exp(-gamma_3*t) + exp(-gamma_4*t)
        where:
            gamma_1 = lambda_1 + lambda_2 + lambda_3 + lambda_4 = lambda_base
            gamma_2 = lambda_1 + 2*lambda_2 + lambda_3 + lambda_4 = lambda_base + lambda_2
            gamma_3 = lambda_1 + lambda_2 + 2*lambda_3 + lambda_4 = lambda_base + lambda_3
            gamma_4 = lambda_1 + 2*lambda_2 + 2*lambda_3 + lambda_4 = lambda_base + lambda_2 + lambda_3

    Args:
        t: Time horizon in hours (scalar or numpy array).
        blocks: Dictionary of BlockParameters.

    Returns:
        Redundant system reliability R_red(t).
    """
    l1 = blocks["LB"].lambda_base
    l2 = blocks["App"].lambda_base
    l3 = blocks["DB"].lambda_base
    l4 = blocks["PGW"].lambda_base

    r1 = np.exp(-l1 * t)
    r2_red = 2.0 * np.exp(-l2 * t) - np.exp(-2.0 * l2 * t)
    r3_red = 2.0 * np.exp(-l3 * t) - np.exp(-2.0 * l3 * t)
    r4 = np.exp(-l4 * t)

    return r1 * r2_red * r3_red * r4


def calculate_reliability_scenario_3(
    t: Union[float, np.ndarray],
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> Union[float, np.ndarray]:
    """Calculate Scenario 3 (Multi-Gateway Expansion) reliability function R_scen3(t).

    Topology:
        LB (series) -> App (parallel) -> DB (parallel) -> PGW (parallel)

    Formula:
        R_scen3(t) = R_LB(t) * R_App,red(t) * R_DB,red(t) * R_PGW,red(t)

    Args:
        t: Time horizon in hours (scalar or numpy array).
        blocks: Dictionary of BlockParameters.

    Returns:
        Scenario 3 system reliability R_scen3(t).
    """
    l1 = blocks["LB"].lambda_base
    l2 = blocks["App"].lambda_base
    l3 = blocks["DB"].lambda_base
    l4 = blocks["PGW"].lambda_base

    r1 = np.exp(-l1 * t)
    r2_red = 2.0 * np.exp(-l2 * t) - np.exp(-2.0 * l2 * t)
    r3_red = 2.0 * np.exp(-l3 * t) - np.exp(-2.0 * l3 * t)
    r4_red = 2.0 * np.exp(-l4 * t) - np.exp(-2.0 * l4 * t)

    return r1 * r2_red * r3_red * r4_red


def calculate_mttf_baseline(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> float:
    """Calculate closed-form Mean Time to Failure (MTTF) for Scenario 1 (Pure Series).

    Formula:
        MTTF_base = integral_0^infty R_base(t) dt = 1 / sum_{i=1}^4 lambda_i

    Args:
        blocks: Dictionary of BlockParameters.

    Returns:
        MTTF in hours.
    """
    lambda_sum = sum(b.lambda_base for b in blocks.values())
    return 1.0 / lambda_sum


def calculate_mttf_redundant_closed_form(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> float:
    """Calculate exact closed-form MTTF for Scenario 2 (Multi-AZ Series-Parallel).

    By integrating the 4 exponential expansion terms:
        MTTF_red = integral_0^infty R_red(t) dt
                 = 4/gamma_1 - 2/gamma_2 - 2/gamma_3 + 1/gamma_4

    where:
        gamma_1 = lambda_1 + lambda_2 + lambda_3 + lambda_4
        gamma_2 = lambda_1 + 2*lambda_2 + lambda_3 + lambda_4
        gamma_3 = lambda_1 + lambda_2 + 2*lambda_3 + lambda_4
        gamma_4 = lambda_1 + 2*lambda_2 + 2*lambda_3 + lambda_4

    Args:
        blocks: Dictionary of BlockParameters.

    Returns:
        MTTF in hours.
    """
    l1 = blocks["LB"].lambda_base
    l2 = blocks["App"].lambda_base
    l3 = blocks["DB"].lambda_base
    l4 = blocks["PGW"].lambda_base

    g1 = l1 + l2 + l3 + l4
    g2 = l1 + 2.0 * l2 + l3 + l4
    g3 = l1 + l2 + 2.0 * l3 + l4
    g4 = l1 + 2.0 * l2 + 2.0 * l3 + l4

    return 4.0 / g1 - 2.0 / g2 - 2.0 / g3 + 1.0 / g4


def calculate_mttf_redundant_numerical(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> float:
    """Calculate Scenario 2 MTTF using adaptive Gauss-Kronrod numerical quadrature.

    Used to cross-validate the closed-form analytical expression.

    Args:
        blocks: Dictionary of BlockParameters.

    Returns:
        MTTF in hours computed numerically.
    """
    result, _ = integrate.quad(
        lambda t: calculate_reliability_redundant(t, blocks),
        0.0,
        np.inf,
        epsabs=1e-12,
        epsrel=1e-10,
    )
    return float(result)


def calculate_mttf_scenario_3_closed_form(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> float:
    """Calculate exact closed-form MTTF for Scenario 3 (Multi-Gateway Expansion).

    By integrating the 8 exponential expansion terms.

    Args:
        blocks: Dictionary of BlockParameters.

    Returns:
        MTTF in hours.
    """
    l1 = blocks["LB"].lambda_base
    l2 = blocks["App"].lambda_base
    l3 = blocks["DB"].lambda_base
    l4 = blocks["PGW"].lambda_base

    return (
        8.0 / (l1 + l2 + l3 + l4)
        - 4.0 / (l1 + 2.0 * l2 + l3 + l4)
        - 4.0 / (l1 + l2 + 2.0 * l3 + l4)
        - 4.0 / (l1 + l2 + l3 + 2.0 * l4)
        + 2.0 / (l1 + 2.0 * l2 + 2.0 * l3 + l4)
        + 2.0 / (l1 + 2.0 * l2 + l3 + 2.0 * l4)
        + 2.0 / (l1 + l2 + 2.0 * l3 + 2.0 * l4)
        - 1.0 / (l1 + 2.0 * l2 + 2.0 * l3 + 2.0 * l4)
    )


def evaluate_mttf_metrics(
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
) -> MTTFMetrics:
    """Evaluate and compile comparative MTTF metrics across all scenarios.

    Args:
        blocks: Dictionary of BlockParameters.

    Returns:
        MTTFMetrics instance containing all analytical values.
    """
    mttf_base = calculate_mttf_baseline(blocks)
    mttf_red = calculate_mttf_redundant_closed_form(blocks)
    delta_mttf = mttf_red - mttf_base
    gain_pct = (delta_mttf / mttf_base) * 100.0
    factor = mttf_red / mttf_base

    mttf_s3 = calculate_mttf_scenario_3_closed_form(blocks)
    gain_s3_pct = ((mttf_s3 - mttf_base) / mttf_base) * 100.0

    return MTTFMetrics(
        mttf_base_hours=mttf_base,
        mttf_red_hours=mttf_red,
        delta_mttf_hours=delta_mttf,
        mttf_gain_pct=gain_pct,
        mttf_gain_factor=factor,
        mttf_scen3_hours=mttf_s3,
        mttf_gain_scen3_pct=gain_s3_pct,
    )


def plot_reliability_curves(
    output_dir: Optional[Path] = None,
    t_annual: float = HOURS_PER_YEAR,
    t_detail: float = 500.0,
    num_points: int = 2000,
) -> plt.Figure:
    """Generate publication-grade comparative curves of R(t) and MTTF gain.

    Produces a high-resolution dual-panel visualization:
        - Panel 1: Full annual mission horizon t in [0, 8760 h].
        - Panel 2: Operational transition window t in [0, 500 h] detailing
          MTTF markers, survival thresholds, and the 74.74% MTTF gain.

    Args:
        output_dir: Directory to export figure files. If None, defaults to reports/figures/.
        t_annual: Annual horizon duration in hours (default: 8760.0).
        t_detail: Zoom window duration in hours (default: 500.0).
        num_points: Number of resolution points for smooth evaluation.

    Returns:
        Matplotlib Figure object.
    """
    metrics = evaluate_mttf_metrics()

    t_full = np.linspace(0.0, t_annual, num_points)
    t_zoom = np.linspace(0.0, t_detail, num_points)

    r_base_full = calculate_reliability_baseline(t_full)
    r_red_full = calculate_reliability_redundant(t_full)
    r_s3_full = calculate_reliability_scenario_3(t_full)

    r_base_zoom = calculate_reliability_baseline(t_zoom)
    r_red_zoom = calculate_reliability_redundant(t_zoom)
    r_s3_zoom = calculate_reliability_scenario_3(t_zoom)

    # Style configuration
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
        "mathtext.fontset": "dejavusans",
        "axes.edgecolor": "#2B2D42",
        "axes.linewidth": 1.0,
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    color_base = "#C05A46"  # Terracotta / Crimson
    color_red = "#3D6B8C"   # Deep Steel Blue
    color_s3 = "#3A8A76"    # Sage Green

    # -------------------------------------------------------------
    # Panel 1: Full Annual Mission Horizon t in [0, 8760 h]
    # -------------------------------------------------------------
    ax1.plot(t_full, r_base_full, label=r"Scenario 1: Baseline Series $R_{\mathrm{base}}(t)$",
             color=color_base, lw=2.2, linestyle="-")
    ax1.plot(t_full, r_red_full, label=r"Scenario 2: Multi-AZ Series-Parallel $R_{\mathrm{red}}(t)$",
             color=color_red, lw=2.4, linestyle="-")
    ax1.plot(t_full, r_s3_full, label=r"Scenario 3: Multi-Gateway Expansion $R_{\mathrm{scen3}}(t)$",
             color=color_s3, lw=1.8, linestyle="--", alpha=0.85)

    ax1.set_title("Full Mission Horizon ($T = 8760\\,\\mathrm{hours}$)", fontsize=12, fontweight="bold", pad=12)
    ax1.set_xlabel("Operational Time $t$ (hours)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Reliability $R(t)$ [Probability of Zero Failures]", fontsize=11, fontweight="bold")
    ax1.set_xlim(0, t_annual)
    ax1.set_ylim(-0.02, 1.02)
    ax1.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7")
    ax1.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#BDC3C7", fontsize=9.5)

    # Inset callout highlighting rapid decay without repairs
    ax1.annotate(
        "Unrepaired mission reliability\ndrops to $\\approx 0$ within $t < 500\\,\\mathrm{h}$\n(Repair mechanisms sustain steady-state $A$)",
        xy=(400, 0.02),
        xytext=(1500, 0.35),
        arrowprops=dict(facecolor="#2B2D42", shrink=0.08, width=1.0, headwidth=6),
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#F8F9FA", edgecolor="#BDC3C7", alpha=0.95),
    )

    # -------------------------------------------------------------
    # Panel 2: Operational Transition Window t in [0, 500 h]
    # -------------------------------------------------------------
    ax2.plot(t_zoom, r_base_zoom, label=r"Scenario 1: Baseline Series",
             color=color_base, lw=2.4, linestyle="-")
    ax2.plot(t_zoom, r_red_zoom, label=r"Scenario 2: Multi-AZ Series-Parallel",
             color=color_red, lw=2.6, linestyle="-")
    ax2.plot(t_zoom, r_s3_zoom, label=r"Scenario 3: Multi-Gateway Expansion",
             color=color_s3, lw=1.8, linestyle="--", alpha=0.85)

    # MTTF Vertical Reference Lines
    ax2.axvline(x=metrics.mttf_base_hours, color=color_base, linestyle=":", lw=1.6, alpha=0.9)
    ax2.axvline(x=metrics.mttf_red_hours, color=color_red, linestyle=":", lw=1.6, alpha=0.9)

    # MTTF Intersections
    r_at_mttf_base = float(calculate_reliability_baseline(metrics.mttf_base_hours))
    r_at_mttf_red = float(calculate_reliability_redundant(metrics.mttf_red_hours))
    ax2.plot([metrics.mttf_base_hours], [r_at_mttf_base], marker="o", markersize=6, color=color_base)
    ax2.plot([metrics.mttf_red_hours], [r_at_mttf_red], marker="s", markersize=6, color=color_red)

    # Horizontal characteristic survival lines
    ax2.axhline(y=1.0 / np.e, color="#7F8C8D", linestyle="-.", lw=1.0, alpha=0.7)
    ax2.text(t_detail * 0.72, 1.0 / np.e + 0.02, r"$R(t) = 1/e \approx 0.368$", fontsize=8.5, color="#555555")

    # Annotate MTTF Baseline
    ax2.annotate(
        f"$\\mathrm{{MTTF}}_{{\\mathrm{{base}}}} = {metrics.mttf_base_hours:.1f}\\,\\mathrm{{h}}$\n($R={r_at_mttf_base:.2f}$)",
        xy=(metrics.mttf_base_hours, r_at_mttf_base),
        xytext=(metrics.mttf_base_hours - 50, r_at_mttf_base + 0.22),
        arrowprops=dict(facecolor=color_base, shrink=0.08, width=1.0, headwidth=5),
        fontsize=8.5,
        fontweight="bold",
        color=color_base,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FDEDEC", edgecolor=color_base, alpha=0.9),
    )

    # Annotate MTTF Redundant
    ax2.annotate(
        f"$\\mathrm{{MTTF}}_{{\\mathrm{{red}}}} = {metrics.mttf_red_hours:.1f}\\,\\mathrm{{h}}$\n($R={r_at_mttf_red:.2f}$)",
        xy=(metrics.mttf_red_hours, r_at_mttf_red),
        xytext=(metrics.mttf_red_hours + 35, r_at_mttf_red + 0.20),
        arrowprops=dict(facecolor=color_red, shrink=0.08, width=1.0, headwidth=5),
        fontsize=8.5,
        fontweight="bold",
        color=color_red,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#EBF5FB", edgecolor=color_red, alpha=0.9),
    )

    # Bracket / Double-headed Arrow for MTTF Gain
    y_bracket = 0.88
    ax2.annotate(
        "",
        xy=(metrics.mttf_base_hours, y_bracket),
        xytext=(metrics.mttf_red_hours, y_bracket),
        arrowprops=dict(arrowstyle="<->", color="#2B2D42", lw=1.6),
    )
    ax2.text(
        (metrics.mttf_base_hours + metrics.mttf_red_hours) / 2.0,
        y_bracket + 0.03,
        f"+{metrics.mttf_gain_pct:.1f}% MTTF Gain\n(+{metrics.delta_mttf_hours:.1f} h)",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color="#2B2D42",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEF9E7", edgecolor="#F1C40F", alpha=0.95),
    )

    ax2.set_title(r"Operational Window & MTTF Extension ($t \leq 500\ \mathrm{hours}$)",
                  fontsize=12, fontweight="bold", pad=12)
    ax2.set_xlabel("Operational Time $t$ (hours)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Reliability $R(t)$", fontsize=11, fontweight="bold")
    ax2.set_xlim(0, t_detail)
    ax2.set_ylim(-0.02, 1.02)
    ax2.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7")
    ax2.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#BDC3C7", fontsize=9.5)

    plt.tight_layout()

    # Save outputs
    target_dirs = []
    if output_dir is not None:
        target_dirs.append(Path(output_dir))
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent
        target_dirs.append(repo_root / "reports" / "figures")

    for directory in target_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        pdf_path = directory / "reliability_curves_comparison.pdf"
        png_path = directory / "reliability_curves_comparison.png"
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
        print(f"Saved: {pdf_path} and {png_path}")

    return fig


def print_analytical_summary():
    """Print console summary of analytical reliability formulations and MTTF gain."""
    metrics = evaluate_mttf_metrics()
    print("=" * 72)
    print("ANALYTICAL TIME-DEPENDENT RELIABILITY & MTTF GAIN (ISSUE #2)")
    print("=" * 72)
    print(f"Scenario 1 MTTF (Baseline Series):        {metrics.mttf_base_hours:10.4f} hours")
    print(f"Scenario 2 MTTF (Multi-AZ Series-Parallel):{metrics.mttf_red_hours:10.4f} hours")
    print(f"Scenario 3 MTTF (Multi-Gateway Expansion):{metrics.mttf_scen3_hours:10.4f} hours")
    print("-" * 72)
    print(f"Absolute MTTF Gain (S2 vs S1):            +{metrics.delta_mttf_hours:10.4f} hours")
    print(f"Relative MTTF Improvement (S2 vs S1):     +{metrics.mttf_gain_pct:10.2f}%")
    print(f"MTTF Multiplication Factor:                {metrics.mttf_gain_factor:10.4f}x")
    print(f"Scenario 3 Improvement vs Baseline:       +{metrics.mttf_gain_scen3_pct:10.2f}%")
    print("=" * 72)


if __name__ == "__main__":
    print_analytical_summary()
    plot_reliability_curves()
