"""
Sensitivity Visualizations and Publication Diagrams for Scenario Expansion.

This module generates publication-grade vector graphics (PDF) and 300 DPI raster
images (PNG) visualizing external payment gateway sensitivity, failover switching
coverage, common-cause failure impact, and architectural diminishing returns.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.models.analytical import DEFAULT_BLOCKS, BlockParameters, HOURS_PER_YEAR
from src.models.sensitivity import (
    evaluate_gateway_availability_sensitivity,
    evaluate_failover_coverage_sensitivity,
    evaluate_common_cause_failure_sensitivity,
    compute_diminishing_returns_metrics,
)

# Publication color palette
SENSITIVITY_COLORS = {
    "scenario_1": "#D9383A",  # Crimson
    "scenario_2": "#1D76DB",  # Blue
    "scenario_3": "#27AE60",  # Emerald Green
    "scenario_4": "#8E44AD",  # Purple
    "highlight": "#E67E22",   # Amber / Orange
    "neutral": "#7F8C8D",     # Gray
    "grid": "#E2E8F0",
}


def _resolve_output_dir(output_dir: Optional[Union[str, Path]] = None) -> Path:
    """Resolve destination directory for exported figures."""
    if output_dir is not None:
        target = Path(output_dir).resolve()
    else:
        current = Path.cwd().resolve()
        while current != current.parent:
            if (current / "requirements.txt").exists():
                break
            current = current.parent
        target = current / "reports" / "figures"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _save_figure_dual_formats(
    fig: plt.Figure,
    base_name: str,
    output_dir: Path,
    dpi: int = 300,
) -> Tuple[Path, Path]:
    """Save matplotlib figure as both vector PDF and high-res 300 DPI PNG."""
    pdf_path = output_dir / f"{base_name}.pdf"
    png_path = output_dir / f"{base_name}.png"

    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=dpi, bbox_inches="tight")

    # Also save standard sensitivity_* aliases in reports/figures/
    if not base_name.startswith("sensitivity_"):
        alias_png = output_dir / f"sensitivity_{base_name}.png"
        fig.savefig(alias_png, format="png", dpi=dpi, bbox_inches="tight")
        if base_name.endswith("_sensitivity"):
            short_name = base_name[:-12]
            short_alias = output_dir / f"sensitivity_{short_name}.png"
            fig.savefig(short_alias, format="png", dpi=dpi, bbox_inches="tight")

    return pdf_path, png_path


def plot_gateway_sla_sensitivity(
    sensitivity_df: Optional[pd.DataFrame] = None,
    output_dir: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (12.0, 6.0),
) -> plt.Figure:
    """Plot system downtime sensitivity vs. third-party payment gateway SLA.

    Contrasts Scenario 2 (Single Gateway) with Scenario 3 (Dual Active Gateways)
    as the external gateway availability varies across commercial SLAs [99.0%, 99.99%].

    Args:
        sensitivity_df: Precomputed sensitivity DataFrame (or None to compute).
        output_dir: Directory to save generated figures.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if sensitivity_df is None:
        # High-resolution sweep for plotting
        grid = np.linspace(0.990, 0.9999, 100)
        sensitivity_df = evaluate_gateway_availability_sensitivity(gateway_availabilities=grid)

    fig, ax1 = plt.subplots(figsize=figsize)

    x_pct = sensitivity_df["gateway_sla_pct"]
    y_s2 = sensitivity_df["scenario_2_downtime_h"]
    y_s3 = sensitivity_df["scenario_3_downtime_h"]

    # Main downtime curves
    line2, = ax1.plot(
        x_pct,
        y_s2,
        color=SENSITIVITY_COLORS["scenario_2"],
        linewidth=2.5,
        linestyle="-",
        label="Scenario 2: Multi-AZ Core with Single Gateway",
    )
    line3, = ax1.plot(
        x_pct,
        y_s3,
        color=SENSITIVITY_COLORS["scenario_3"],
        linewidth=2.5,
        linestyle="-",
        label="Scenario 3: Multi-AZ Core with Dual Gateways",
    )

    # Highlight nominal point A_4 = 99.95%
    nominal_a4 = 99.95
    nom_s2_row = sensitivity_df.iloc[(sensitivity_df["gateway_sla_pct"] - nominal_a4).abs().argsort()[:1]].iloc[0]
    ax1.plot(
        nominal_a4,
        nom_s2_row["scenario_2_downtime_h"],
        marker="o",
        markersize=9,
        color=SENSITIVITY_COLORS["scenario_2"],
        zorder=5,
    )
    ax1.plot(
        nominal_a4,
        nom_s2_row["scenario_3_downtime_h"],
        marker="s",
        markersize=9,
        color=SENSITIVITY_COLORS["scenario_3"],
        zorder=5,
    )

    # Reference annotations
    ax1.annotate(
        f"Nominal S2: {nom_s2_row['scenario_2_downtime_h']:.2f} h/yr\n($A_4 = 99.95\\%$)",
        xy=(nominal_a4, nom_s2_row["scenario_2_downtime_h"]),
        xytext=(nominal_a4 - 0.15, nom_s2_row["scenario_2_downtime_h"] + 40.0),
        arrowprops=dict(arrowstyle="->", color=SENSITIVITY_COLORS["scenario_2"], lw=1.5),
        fontsize=10,
        fontweight="bold",
        color=SENSITIVITY_COLORS["scenario_2"],
        bbox=dict(boxstyle="round,pad=0.3", fc="#EBF5FB", ec=SENSITIVITY_COLORS["scenario_2"], lw=1),
    )

    ax1.annotate(
        f"Nominal S3: {nom_s2_row['scenario_3_downtime_h']:.2f} h/yr\n($-41.6\\%$ vs S2)",
        xy=(nominal_a4, nom_s2_row["scenario_3_downtime_h"]),
        xytext=(nominal_a4 - 0.25, nom_s2_row["scenario_3_downtime_h"] + 30.0),
        arrowprops=dict(arrowstyle="->", color=SENSITIVITY_COLORS["scenario_3"], lw=1.5),
        fontsize=10,
        fontweight="bold",
        color=SENSITIVITY_COLORS["scenario_3"],
        bbox=dict(boxstyle="round,pad=0.3", fc="#EAFAF1", ec=SENSITIVITY_COLORS["scenario_3"], lw=1),
    )

    # Shaded resilience benefit buffer
    ax1.fill_between(
        x_pct,
        y_s3,
        y_s2,
        color=SENSITIVITY_COLORS["scenario_3"],
        alpha=0.15,
        label="Downtime Saved by Multi-Gateway Redundancy",
    )

    # Asymptote floor annotation (DB bottleneck floor)
    db_floor = 6.13  # S3 asymptote
    ax1.axhline(
        db_floor,
        color=SENSITIVITY_COLORS["neutral"],
        linestyle="--",
        linewidth=1.2,
        alpha=0.7,
        label=f"Architectural Asymptote Floor (~{db_floor:.2f} h/yr)",
    )

    ax1.set_xlabel("External Payment Gateway Availability SLA: $A_4$ (%)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Expected System Annual Downtime (hours/year)", fontsize=11, fontweight="bold")
    ax1.set_title(
        "Sensitivity Analysis: System Downtime vs. External Gateway SLA ($A_4$)\n"
        "Demonstrating Architectural Shielding Against Third-Party Degradation",
        fontsize=12,
        fontweight="bold",
        pad=14,
    )
    ax1.set_xlim(99.0, 99.99)
    ax1.set_ylim(0, max(y_s2) * 1.05)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.95, fontsize=10)

    plt.tight_layout()
    _save_figure_dual_formats(fig, "gateway_sla_sensitivity", out_dir)
    return fig


def plot_failover_and_ccf_sensitivity(
    failover_df: Optional[pd.DataFrame] = None,
    ccf_df: Optional[pd.DataFrame] = None,
    output_dir: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (15.0, 5.8),
) -> plt.Figure:
    """Generate side-by-side sensitivity plots for imperfect failover switching and CCF risk.

    Args:
        failover_df: Precomputed failover coverage DataFrame (or None).
        ccf_df: Precomputed Common-Cause Failure DataFrame (or None).
        output_dir: Target directory for figure export.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if failover_df is None:
        c_grid = np.linspace(0.80, 1.00, 50)
        failover_df = evaluate_failover_coverage_sensitivity(coverage_probabilities=c_grid)

    if ccf_df is None:
        beta_grid = np.linspace(0.00, 0.20, 50)
        ccf_df = evaluate_common_cause_failure_sensitivity(beta_factors=beta_grid)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Panel 1: Failover Switching Coverage Sensitivity
    c_pct = failover_df["coverage_pct"]
    d_sys_c = failover_df["system_downtime_h"]
    d_pgw_c = failover_df["gateway_downtime_h"]

    ax1.plot(
        c_pct,
        d_sys_c,
        color=SENSITIVITY_COLORS["scenario_3"],
        linewidth=2.5,
        label="Total System Downtime",
    )
    ax1.plot(
        c_pct,
        d_pgw_c,
        color=SENSITIVITY_COLORS["highlight"],
        linewidth=2.0,
        linestyle="-.",
        label="Effective Gateway Downtime",
    )
    ax1.axhline(
        10.51,
        color=SENSITIVITY_COLORS["scenario_2"],
        linestyle="--",
        linewidth=1.5,
        alpha=0.8,
        label="Scenario 2 Benchmark (No Gateway Redundancy: 10.51 h)",
    )

    ax1.set_xlabel("Failover Switching Coverage Probability: $C$ (%)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Annual Downtime (hours/year)", fontsize=11, fontweight="bold")
    ax1.set_title(
        "(a) Impact of Imperfect Failover Switching Coverage ($C$)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax1.set_xlim(80.0, 100.0)
    ax1.set_ylim(0, 11.5)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, fontsize=9.5)

    # Panel 2: Common-Cause Failure (CCF) Beta-Factor Sensitivity
    beta_pct = ccf_df["beta_ccf_pct"]
    d_sys_beta = ccf_df["system_downtime_h"]
    d_pgw_beta = ccf_df["gateway_downtime_h"]

    ax2.plot(
        beta_pct,
        d_sys_beta,
        color=SENSITIVITY_COLORS["scenario_3"],
        linewidth=2.5,
        label="Total System Downtime",
    )
    ax2.plot(
        beta_pct,
        d_pgw_beta,
        color="#8E44AD",
        linewidth=2.0,
        linestyle="-.",
        label="Effective Gateway Downtime",
    )
    ax2.axhline(
        10.51,
        color=SENSITIVITY_COLORS["scenario_2"],
        linestyle="--",
        linewidth=1.5,
        alpha=0.8,
        label="Scenario 2 Benchmark (Complete Coupling $\\beta = 1.0$: 10.51 h)",
    )

    ax2.set_xlabel("Common-Cause Failure Fraction: $\\beta$ (%)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Annual Downtime (hours/year)", fontsize=11, fontweight="bold")
    ax2.set_title(
        "(b) Vulnerability to Common-Cause Failures ($\\beta$-Factor Model)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax2.set_xlim(0.0, 20.0)
    ax2.set_ylim(0, 11.5)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper left", frameon=True, fontsize=9.5)

    plt.tight_layout()
    _save_figure_dual_formats(fig, "failover_and_ccf_sensitivity", out_dir)
    return fig


def plot_architectural_diminishing_returns(
    diminishing_df: Optional[pd.DataFrame] = None,
    output_dir: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (14.0, 5.5),
) -> plt.Figure:
    """Plot the law of diminishing returns across architectural evolutionary tiers.

    Args:
        diminishing_df: Precomputed diminishing returns summary (or None).
        output_dir: Target export directory.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if diminishing_df is None:
        diminishing_df = compute_diminishing_returns_metrics()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    steps = ["S1 (Baseline)", "S2 (Multi-AZ)", "S3 (Multi-GW)", "S4 (Global DB)"]
    downtimes = diminishing_df["Annual Downtime (h/yr)"].values
    colors = [
        SENSITIVITY_COLORS["scenario_1"],
        SENSITIVITY_COLORS["scenario_2"],
        SENSITIVITY_COLORS["scenario_3"],
        SENSITIVITY_COLORS["scenario_4"],
    ]

    # Panel 1: Absolute Annual Downtime
    bars1 = ax1.bar(steps, downtimes, color=colors, width=0.55, edgecolor="#2C3E50", linewidth=1.2)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 2.0,
            f"{yval:.2f} h",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax1.set_ylabel("Annual Downtime (hours/year)", fontsize=11, fontweight="bold")
    ax1.set_title(
        "(a) System Downtime Across Architectural Tiers",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax1.set_ylim(0, 105)
    ax1.grid(True, axis="y", linestyle=":", alpha=0.6)

    # Panel 2: Marginal Downtime Saved
    marginal_saved = diminishing_df["Downtime Saved vs Previous (h/yr)"].values[1:]  # skip S1
    marginal_steps = ["S1 \u2192 S2\n(Compute + DB)", "S2 \u2192 S3\n(Multi-Gateway)", "S3 \u2192 S4\n(Multi-Reg DB)"]
    marginal_colors = [
        SENSITIVITY_COLORS["scenario_2"],
        SENSITIVITY_COLORS["scenario_3"],
        SENSITIVITY_COLORS["scenario_4"],
    ]

    bars2 = ax2.bar(marginal_steps, marginal_saved, color=marginal_colors, width=0.55, edgecolor="#2C3E50", linewidth=1.2)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 1.8,
            f"+{yval:.2f} h",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax2.set_ylabel("Marginal Downtime Saved (hours/year)", fontsize=11, fontweight="bold")
    ax2.set_title(
        "(b) Marginal Downtime Saved: Amdahl's Law in Reliability",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax2.set_ylim(0, 95)
    ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    _save_figure_dual_formats(fig, "scenario_3_diminishing_returns", out_dir)
    return fig


def generate_all_sensitivity_diagrams(
    output_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Path]:
    """Generate and export all sensitivity figures for Scenario 3 expansion.

    Args:
        output_dir: Target directory. Defaults to reports/figures.

    Returns:
        Dictionary mapping figure keys to exported PDF file paths.
    """
    out_dir = _resolve_output_dir(output_dir)

    fig1 = plot_gateway_sla_sensitivity(output_dir=out_dir)
    plt.close(fig1)

    fig2 = plot_failover_and_ccf_sensitivity(output_dir=out_dir)
    plt.close(fig2)

    fig3 = plot_architectural_diminishing_returns(output_dir=out_dir)
    plt.close(fig3)

    return {
        "gateway_sla_sensitivity": out_dir / "gateway_sla_sensitivity.pdf",
        "failover_and_ccf_sensitivity": out_dir / "failover_and_ccf_sensitivity.pdf",
        "scenario_3_diminishing_returns": out_dir / "scenario_3_diminishing_returns.pdf",
    }
