"""
Visualizations for Subsystem Unavailability Contribution and Bottleneck Identification.

This module generates vector graphics (PDF) and high-resolution raster images
(PNG, 300 DPI) illustrating individual and cumulative percentage contributions of
each subsystem to annual system downtime across cloud payment scenarios.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

from src.models.analytical import DEFAULT_BLOCKS, BlockParameters
from src.models.subsystem_contribution import (
    SubsystemContributionResult,
    compute_subsystem_downtime_contributions,
    evaluate_subsystem_contributions,
    compute_bottleneck_shift_summary,
)

BLOCK_COLORS: Dict[str, str] = {
    "LB": "#1D76DB",   # Managed Ingress Blue
    "App": "#D9383A",  # Compute Logic Crimson
    "DB": "#E67E22",   # Database Amber / Orange
    "PGW": "#8E44AD",  # Payment Gateway Purple
}

CUMULATIVE_LINE_COLOR: str = "#2B2D42"  # Dark Slate
CALLOUT_EDGE_COLOR: str = "#B7791F"     # Dark Gold / Ochre


def _plot_subsystem_contribution_axis(
    ax: plt.Axes,
    result: SubsystemContributionResult,
    title: str,
    max_downtime_y: Optional[float] = None,
    annotation_text: Optional[str] = None,
) -> plt.Axes:
    """Render subsystem downtime bars alongside a cumulative share curve."""
    blocks = [c.block_code for c in result.contributions]
    downtimes = [c.downtime_hours for c in result.contributions]
    cum_pcts = [c.cumulative_percentage for c in result.contributions]
    shares = [c.percentage_of_total for c in result.contributions]
    colors = [BLOCK_COLORS.get(b, "#34495E") for b in blocks]

    x_indices = np.arange(len(blocks))

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
    ax.set_xlim(-0.55, len(blocks) - 0.45)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(blocks, fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#BDC3C7", zorder=0)

    if max_downtime_y is not None:
        ax.set_ylim(0, max_downtime_y)
    else:
        default_limits = {1: 72.0, 2: 8.4, 3: 5.8}
        top_val = max(downtimes) if downtimes else 1.0
        ax.set_ylim(0, default_limits.get(result.scenario_id, top_val * 1.55))

    # Label bars with absolute downtime and individual percentage contribution
    for bar, d_val, share_val in zip(bars, downtimes, shares):
        height = bar.get_height()
        if d_val >= 1.0:
            label_text = f"{d_val:.2f} h ({share_val:.1f}%)"
        elif d_val >= 0.01:
            label_text = f"{d_val:.3f} h ({share_val:.2f}%)"
        else:
            d_sec = d_val * 3600.0
            label_text = f"{d_sec:.1f} s ({share_val:.2f}%)"

        ax.annotate(
            label_text,
            xy=(bar.get_x() + bar.get_width() / 2.0, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.3,
            fontweight="bold",
            color="#2C3E50",
        )

    # Secondary Y-axis: Cumulative Percentage Share Curve (without any 80% cut-off rule)
    ax_sec = ax.twinx()
    ax_sec.plot(
        x_indices,
        cum_pcts,
        color=CUMULATIVE_LINE_COLOR,
        marker="o",
        markersize=6.5,
        linewidth=2.4,
        linestyle="-",
        label="Cumulative Share (%)",
        zorder=4,
    )
    ax_sec.set_ylabel(
        "Cumulative Unavailability Share (%)",
        fontsize=11,
        fontweight="bold",
        color=CUMULATIVE_LINE_COLOR,
    )
    ax_sec.set_ylim(0, 118)
    ax_sec.set_yticks([0, 20, 40, 60, 80, 100])
    ax_sec.tick_params(axis="y", labelcolor=CUMULATIVE_LINE_COLOR, labelsize=10)
    ax_sec.grid(False)

    # Position cumulative labels clearly above/below markers to prevent bar-label collisions
    for idx, cum_val in enumerate(cum_pcts):
        offset_y = -18 if idx == 0 else 13
        ax_sec.annotate(
            f"{cum_val:.1f}%",
            xy=(idx, cum_val),
            xytext=(0, offset_y),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=8.3,
            fontweight="bold",
            color=CUMULATIVE_LINE_COLOR,
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="#FFFFFF",
                edgecolor=CUMULATIVE_LINE_COLOR,
                alpha=0.92,
                lw=0.8,
            ),
            zorder=5,
        )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)

    if annotation_text:
        ax.text(
            0.97,
            0.44,
            annotation_text,
            transform=ax.transAxes,
            ha="right",
            va="center",
            fontsize=8.8,
            fontweight="bold",
            color="#1A252C",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="#FFF9E6",
                edgecolor=CALLOUT_EDGE_COLOR,
                linewidth=1.2,
                alpha=0.95,
            ),
            zorder=6,
        )

    return ax_sec


def plot_subsystem_downtime_contribution(
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (15.0, 6.2),
) -> plt.Figure:
    """Generate side-by-side subsystem downtime contribution charts for Scenarios 1 and 2.

    Highlights the bottleneck shift from internal tiers (App/DB) to the external
    Payment Gateway (PGW) and Database failover following Multi-AZ redundancy.

    Args:
        output_dir: Destination directory for figures. Defaults to reports/figures/.
        blocks: Subsystem parameters dictionary.
        figsize: Matplotlib figure dimensions (width, height) in inches.

    Returns:
        The generated Matplotlib Figure instance.
    """
    results = evaluate_subsystem_contributions(blocks)
    s1 = results["scenario_1"]
    s2 = results["scenario_2"]
    shifts = compute_bottleneck_shift_summary(results, blocks)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    ann1 = (
        f"Internal Bottlenecks Dominant\n"
        f"App + DB = {s1.app_db_combined_share_pct:.1f}% of downtime\n"
        f"Total: {s1.system_downtime_hours:.2f} h/year ({s1.system_availability * 100:.3f}% A)"
    )
    _plot_subsystem_contribution_axis(
        ax=ax1,
        result=s1,
        title=r"$\mathbf{Scenario\ 1:\ Baseline\ Series}$",
        max_downtime_y=72.0,
        annotation_text=ann1,
    )

    ann2 = (
        f"Bottleneck Shift\n"
        f"Internal downtime: -{shifts['internal_tier_reduction_pct']:.1f}%\n"
        f"DB & PGW: {s2.pgw_share_pct + s2.contributions[0].percentage_of_total:.1f}% of downtime\n"
        f"Total: {s2.system_downtime_hours:.2f} h/year ({s2.system_availability * 100:.3f}% A)"
    )
    _plot_subsystem_contribution_axis(
        ax=ax2,
        result=s2,
        title=r"$\mathbf{Scenario\ 2:\ Multi-AZ\ Series-Parallel}$",
        max_downtime_y=8.4,
        annotation_text=ann2,
    )

    plt.suptitle(
        "Subsystem Unavailability Contribution: Architectural Bottleneck Shift",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    _save_figure(fig, "subsystem_downtime_contribution", output_dir)
    return fig


def plot_subsystem_contribution_single_scenario(
    scenario_id: int,
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (8.0, 5.5),
) -> plt.Figure:
    """Generate an individual subsystem downtime contribution chart for a scenario."""
    result = compute_subsystem_downtime_contributions(scenario_id, blocks)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    title = f"Subsystem Downtime Contribution - {result.scenario_name}"
    _plot_subsystem_contribution_axis(ax=ax, result=result, title=title)

    plt.tight_layout()
    filename = f"subsystem_contribution_scenario_{scenario_id}"
    _save_figure(fig, filename, output_dir)
    return fig


def plot_subsystem_contribution_all_scenarios(
    output_dir: Optional[Path] = None,
    blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS,
    figsize: Tuple[float, float] = (20.0, 5.8),
) -> plt.Figure:
    """Generate a 3-panel subsystem downtime contribution figure for Scenarios 1, 2, and 3."""
    results = evaluate_subsystem_contributions(blocks)
    s1 = results["scenario_1"]
    s2 = results["scenario_2"]
    s3 = results["scenario_3"]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=figsize)

    _plot_subsystem_contribution_axis(
        ax=ax1,
        result=s1,
        title=r"$\mathbf{Scenario\ 1:\ Baseline\ Series}$",
        max_downtime_y=72.0,
    )
    _plot_subsystem_contribution_axis(
        ax=ax2,
        result=s2,
        title=r"$\mathbf{Scenario\ 2:\ Multi-AZ\ Series-Parallel}$",
        max_downtime_y=8.4,
    )
    _plot_subsystem_contribution_axis(
        ax=ax3,
        result=s3,
        title=r"$\mathbf{Scenario\ 3:\ Multi-Gateway\ Expansion}$",
        max_downtime_y=5.8,
    )

    plt.suptitle(
        "Subsystem Unavailability Contribution Across Cloud Architecture Scenarios",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.93])

    _save_figure(fig, "subsystem_contribution_comparison_all", output_dir)
    return fig


def generate_all_subsystem_contribution_diagrams(output_dir: Optional[Path] = None) -> None:
    """Generate all subsystem contribution figures (individual and combined) in PDF and PNG."""
    fig_pair = plot_subsystem_downtime_contribution(output_dir=output_dir)
    plt.close(fig_pair)

    for s_id in (1, 2, 3):
        fig_s = plot_subsystem_contribution_single_scenario(scenario_id=s_id, output_dir=output_dir)
        plt.close(fig_s)

    fig_all = plot_subsystem_contribution_all_scenarios(output_dir=output_dir)
    plt.close(fig_all)


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
    generate_all_subsystem_contribution_diagrams()
