"""
Publication-Grade Visualizations for Subsystem Unavailability Pareto Analysis.

This module generates publication-grade vector graphics (PDF) and high-resolution raster
images (PNG, 300 DPI) illustrating the Pareto distribution of annual downtime across
cloud payment subsystems for Milestone 3 / Issue #3 & #5.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from src.models.pareto import (
    DEFAULT_BLOCKS,
    BlockParameters,
    ParetoAnalysisResult,
    compute_subsystem_downtime_contributions,
    evaluate_pareto_analysis,
    compute_bottleneck_shift_summary,
)

# Publication styling palette
BLOCK_COLORS: Dict[str, str] = {
    "LB": "#1D76DB",   # Managed Ingress Blue
    "App": "#D9383A",  # Compute Logic Crimson
    "DB": "#E67E22",   # Database Amber / Orange
    "PGW": "#8E44AD",  # Payment Gateway Purple
}

PARETO_LINE_COLOR: str = "#2B2D42"   # Dark Slate
PARETO_THRESHOLD_COLOR: str = "#B7791F" # Dark Gold / Ochre


def _plot_pareto_axis(
    ax: plt.Axes,
    result: ParetoAnalysisResult,
    title: str,
    max_downtime_y: Optional[float] = None,
    annotation_text: Optional[str] = None,
    annotation_xy: Optional[Tuple[float, float]] = None,
) -> plt.Axes:
    """Helper to render a dual-axis Pareto chart onto a Matplotlib Axes."""
    blocks = [c.block_code for c in result.contributions]
    downtimes = [c.downtime_hours for c in result.contributions]
    cum_pcts = [c.cumulative_percentage for c in result.contributions]
    shares = [c.percentage_of_total for c in result.contributions]
    colors = [BLOCK_COLORS.get(b, "#34495E") for b in blocks]

    x_indices = np.arange(len(blocks))

    # Primary Y-axis: Downtime Bars
    bars = ax.bar(
        x_indices,
        downtimes,
        color=colors,
        alpha=0.88,
        edgecolor="#1A252C",
        linewidth=1.2,
        width=0.55,
        zorder=3,
    )

    ax.set_xlabel("Architectural Subsystem", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Annual Downtime (hours/year)", fontsize=11, fontweight="bold", color="#1A252C")
    ax.set_xticks(x_indices)
    ax.set_xticklabels(
        #[f"{c.block_code}\n({c.subsystem_name})" for c in result.contributions],
        [f"{c.block_code}" for c in result.contributions],
        fontsize=9.5,
        fontweight="bold",
    )
    ax.tick_params(axis="y", labelsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#BDC3C7", zorder=0)

    # Set appropriate Y-limit for bars
    if max_downtime_y is not None:
        ax.set_ylim(0, max_downtime_y)
    else:
        top_val = max(downtimes) if downtimes else 1.0
        ax.set_ylim(0, top_val * 1.25)

    # Label bars with exact values and share
    for bar, d_val, share_val in zip(bars, downtimes, shares):
        height = bar.get_height()
        if d_val >= 1.0:
            label_text = f"{d_val:.2f} h\n({share_val:.1f}%)"
        elif d_val >= 0.01:
            label_text = f"{d_val:.3f} h\n({share_val:.2f}%)"
        else:
            # Display in seconds if very small
            d_sec = d_val * 3600.0
            label_text = f"{d_sec:.1f} s\n({share_val:.2f}%)"

        ax.annotate(
            label_text,
            xy=(bar.get_x() + bar.get_width() / 2.0, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color="#2C3E50",
        )

    # Secondary Y-axis: Cumulative Percentage Line
    ax_sec = ax.twinx()
    ax_sec.plot(
        x_indices,
        cum_pcts,
        color=PARETO_LINE_COLOR,
        marker="o",
        markersize=6.5,
        linewidth=2.4,
        linestyle="-",
        label="Cumulative Unavailability (%)",
        zorder=4,
    )
    ax_sec.set_ylabel("Cumulative Unavailability Share (%)", fontsize=11, fontweight="bold", color=PARETO_LINE_COLOR)
    ax_sec.set_ylim(0, 110)
    ax_sec.tick_params(axis="y", labelcolor=PARETO_LINE_COLOR, labelsize=10)
    ax_sec.grid(False)

    # 80% Pareto Reference Cut-Off Line
    ax_sec.axhline(
        y=80.0,
        color=PARETO_THRESHOLD_COLOR,
        linestyle="--",
        linewidth=1.6,
        alpha=0.9,
        zorder=2,
    )
    ax_sec.text(
        2.5,
        81.5,
        "80% Pareto Threshold",
        fontsize=8.5,
        fontweight="bold",
        color=PARETO_THRESHOLD_COLOR,
    )

    # Annotate cumulative percentages on markers
    offsets_s1 = [(0, -15), (0, 20), (0, 10), (0, 10)]
    offsets_s2 = [(0, -15), (0, 25), (0, 12), (0, 12)]
    for idx, cum_val in enumerate(cum_pcts):
        offset_y = offsets_s1[idx][1] if result.scenario_id == 1 else offsets_s2[idx][1]
        ax_sec.annotate(
            f"{cum_val:.1f}%",
            xy=(idx, cum_val),
            xytext=(0, offset_y),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color=PARETO_LINE_COLOR,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor=PARETO_LINE_COLOR, alpha=0.85, lw=0.8),
        )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)

    # Optional highlight annotation box
    if annotation_text and annotation_xy:
        ax.annotate(
            annotation_text,
            xy=annotation_xy,
            xytext=(annotation_xy[0], annotation_xy[1]),
            fontsize=9.0,
            fontweight="bold",
            color="#1A252C",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="#FFF9E6",
                edgecolor=PARETO_THRESHOLD_COLOR,
                linewidth=1.2,
                alpha=0.95,
            ),
        )

    return ax_sec


def plot_pareto_analysis(
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (15.0, 6.2),
) -> plt.Figure:
    """Generate side-by-side dual-axis Pareto charts comparing Scenario 1 and Scenario 2.

    Highlights the quantitative bottleneck shift from internal tiers (App/DB)
    to the external Payment Gateway (PGW) following Multi-AZ migration.

    Args:
        output_dir: Destination directory for figures. Defaults to reports/figures/.
        blocks: Subsystem parameters dictionary.
        figsize: Matplotlib figure dimensions (width, height) in inches.

    Returns:
        The generated Matplotlib Figure instance.
    """
    results = evaluate_pareto_analysis(blocks)
    s1 = results["scenario_1"]
    s2 = results["scenario_2"]
    shifts = compute_bottleneck_shift_summary(results, blocks)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Scenario 1 (Baseline Pure Series)
    ann1 = (
        f"Internal SPOFs Dominant\n"
        f"App + DB = {s1.app_db_combined_share_pct:.1f}% of downtime\n"
        f"Total: {s1.system_downtime_hours:.2f} h/year ({s1.system_availability*100:.3f}% A)"
    )
    _plot_pareto_axis(
        ax=ax1,
        result=s1,
        title=r"$\mathbf{Scenario\ 1:\ Baseline\ Series\ (Pure\ SPOF)}$",
        max_downtime_y=54.0,
        annotation_text=ann1,
        annotation_xy=(1.5, 32.0),
    )

    # Scenario 2 (Multi-AZ Series-Parallel)
    ann2 = (
        f"Architectural Shift\n"
        f"Internal downtime: -{shifts['internal_tier_reduction_pct']:.1f}%\n"
        f"PGW & DB: {s2.pgw_share_pct + s2.contributions[0].percentage_of_total:.1f}% of downtime\n"
        f"Total: {s2.system_downtime_hours:.2f} h/year ({s2.system_availability*100:.3f}% A)"
    )
    _plot_pareto_axis(
        ax=ax2,
        result=s2,
        title=r"$\mathbf{Scenario\ 2:\ Multi-AZ\ Series-Parallel\ (HA)}$",
        max_downtime_y=6.0,
        annotation_text=ann2,
        annotation_xy=(1.5, 3.35),
    )

    plt.suptitle(
        "Pareto Analysis of Subsystem Unavailability: Architectural Bottleneck Shift",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    _save_figure(fig, "pareto_analysis", output_dir)
    return fig


def plot_pareto_single_scenario(
    scenario_id: int,
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (8.0, 5.5),
) -> plt.Figure:
    """Generate an individual publication-grade Pareto chart for a single scenario."""
    result = compute_subsystem_downtime_contributions(scenario_id, blocks)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    title = f"Pareto Distribution of Downtime - {result.scenario_name}"
    _plot_pareto_axis(ax=ax, result=result, title=title)

    plt.tight_layout()
    filename = f"pareto_scenario_{scenario_id}"
    _save_figure(fig, filename, output_dir)
    return fig


def plot_pareto_all_scenarios_3panel(
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (20.0, 5.8),
) -> plt.Figure:
    """Generate a comprehensive 3-panel Pareto figure covering Scenarios 1, 2, and 3."""
    results = evaluate_pareto_analysis(blocks)
    s1 = results["scenario_1"]
    s2 = results["scenario_2"]
    s3 = results["scenario_3"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=figsize)

    _plot_pareto_axis(
        ax=ax1,
        result=s1,
        title=r"$\mathbf{Scenario\ 1:\ Baseline\ Series}$",
        max_downtime_y=54.0,
    )
    _plot_pareto_axis(
        ax=ax2,
        result=s2,
        title=r"$\mathbf{Scenario\ 2:\ Multi-AZ\ Series-Parallel}$",
        max_downtime_y=6.0,
    )
    _plot_pareto_axis(
        ax=ax3,
        result=s3,
        title=r"$\mathbf{Scenario\ 3:\ Multi-Gateway\ Expansion}$",
        max_downtime_y=6.0,
    )

    plt.suptitle(
        "Evolution of Subsystem Unavailability Across Cloud Architecture Scenarios",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.93])

    _save_figure(fig, "pareto_comparison_all", output_dir)
    return fig


def generate_all_pareto_diagrams(output_dir: Optional[Path] = None) -> None:
    """Generate all Pareto figures (individual and combined) in PDF and PNG formats."""
    plot_pareto_analysis(output_dir=output_dir)
    plot_pareto_single_scenario(scenario_id=1, output_dir=output_dir)
    plot_pareto_single_scenario(scenario_id=2, output_dir=output_dir)
    plot_pareto_single_scenario(scenario_id=3, output_dir=output_dir)
    plot_pareto_all_scenarios_3panel(output_dir=output_dir)


def _save_figure(fig: plt.Figure, base_name: str, output_dir: Optional[Path]) -> None:
    """Save figure in both vector PDF and 300 DPI PNG formats."""
    if output_dir is not None:
        target_dir = Path(output_dir)
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent
        target_dir = repo_root / "reports" / "figures"

    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = target_dir / f"{base_name}.pdf"
    png_path = target_dir / f"{base_name}.png"

    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    print(f"Generated: {pdf_path.name} and {png_path.name}")


if __name__ == "__main__":
    generate_all_pareto_diagrams()
