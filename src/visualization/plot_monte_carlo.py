"""
Publication-Grade Visualizations for Monte Carlo Stochastic Simulation.

This module generates publication-grade vector graphics (PDF) and high-resolution raster
images (PNG, 300 DPI) illustrating:
1. Cumulative asymptotic convergence curves of availability estimators against iterations (n in [1, 10^4]).
2. Empirical annual downtime distributions with superimposed mean, median, and 95th percentile markers.
3. Subsystem downtime breakdown and Pareto cross-validation contrasting analytical benchmarks against
   simulated empirical averages.
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.models.analytical import (
    DEFAULT_BLOCKS,
    HOURS_PER_YEAR,
)
from src.simulation.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_NUM_REPLICAS,
    DEFAULT_HORIZON_HOURS,
    SimulationConfig,
    SimulationMetrics,
    ScenarioSimulationResult,
    EmpiricalDistributionSummary,
    run_all_scenarios_simulation,
    compute_running_statistics,
    compute_empirical_distribution_summary,
)

# Publication color palette
SCENARIO_COLORS: Dict[int, str] = {
    1: "#D9383A",  # Baseline Series Crimson
    2: "#1D76DB",  # Multi-AZ Series-Parallel Blue
    3: "#27AE60",  # Multi-Gateway Expansion Emerald
}

SCENARIO_LIGHT_COLORS: Dict[int, str] = {
    1: "#FADBD8",  # Soft Red Tint
    2: "#D4E6F1",  # Soft Blue Tint
    3: "#D5F5E3",  # Soft Green Tint
}

BLOCK_COLORS: Dict[str, str] = {
    "LB": "#1D76DB",   # Managed Ingress Blue
    "App": "#D9383A",  # Compute Logic Crimson
    "DB": "#E67E22",   # Database Amber / Orange
    "PGW": "#8E44AD",  # Payment Gateway Purple
}

THEORETICAL_LINE_COLOR: str = "#1A252C"
PERCENTILE_95_COLOR: str = "#8E44AD"
PERCENTILE_99_COLOR: str = "#C0392B"
MEDIAN_LINE_COLOR: str = "#7F8C8D"


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
    return pdf_path, png_path


def plot_monte_carlo_convergence(
    results: Optional[Union[ScenarioSimulationResult, Dict[int, ScenarioSimulationResult], List[ScenarioSimulationResult]]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    save_individual: bool = True,
    figsize: Tuple[float, float] = (15.0, 11.0),
) -> plt.Figure:
    """Plot cumulative asymptotic convergence curves of availability estimators.

    Illustrates running cumulative mean availability A_hat(n) as a function of simulation
    replications n in [1, 10^4], alongside the closed-form analytical benchmark line
    and the 95% bilateral confidence envelope.

    Args:
        results: Simulation results (single result, dict of results by scenario_id, or None).
        output_dir: Target output directory for figure exports.
        save_individual: If True, also exports individual scenario convergence plots.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if results is None:
        cfg = SimulationConfig(num_replicas=DEFAULT_NUM_REPLICAS, seed=DEFAULT_SEED)
        results_dict = run_all_scenarios_simulation(config=cfg)
    elif isinstance(results, ScenarioSimulationResult):
        results_dict = {results.scenario_id: results}
    elif isinstance(results, dict):
        results_dict = results
    else:
        results_dict = {r.scenario_id: r for r in results}

    scenario_ids = sorted(results_dict.keys())

    # Create 3-panel figure (one subplot per scenario)
    fig, axes = plt.subplots(
        nrows=len(scenario_ids),
        ncols=1,
        figsize=figsize,
        sharex=True,
    )
    if len(scenario_ids) == 1:
        axes = [axes]

    for ax, s_id in zip(axes, scenario_ids):
        res = results_dict[s_id]
        m = res.metrics
        color = SCENARIO_COLORS.get(s_id, "#2C3E50")
        tint = SCENARIO_LIGHT_COLORS.get(s_id, "#EAEDED")

        cum_mean, cum_std, margin = compute_running_statistics(
            res.availability,
            confidence_level=res.config.confidence_level,
        )

        n_replicas = len(res.availability)
        x_vals = np.arange(1, n_replicas + 1)

        # Plot 95% confidence envelope (omitting first 10 steps to avoid infinite boundary spikes)
        start_step = min(10, n_replicas - 1)
        ax.fill_between(
            x_vals[start_step:],
            (cum_mean - margin)[start_step:] * 100.0,
            (cum_mean + margin)[start_step:] * 100.0,
            color=color,
            alpha=0.18,
            label=r"Empirical $95\%$ Confidence Envelope $\hat{A}(n) \pm 1.96 \cdot \text{SE}(n)$",
            zorder=2,
        )

        # Plot running cumulative availability sequence
        ax.plot(
            x_vals,
            cum_mean * 100.0,
            color=color,
            linewidth=1.8,
            label=rf"Cumulative Running Mean $\hat{{A}}(n)$ ({res.name})",
            zorder=4,
        )

        # Theoretical reference line
        ax.axhline(
            m.theoretical_availability * 100.0,
            color=THEORETICAL_LINE_COLOR,
            linestyle="--",
            linewidth=1.6,
            label=rf"Theoretical Benchmark $A = {m.theoretical_availability * 100.0:.4f}\%$",
            zorder=3,
        )

        # Format axes
        ax.set_title(
            f"Scenario {s_id}: {res.name} — Asymptotic Convergence ($N = {n_replicas:,}$ Replications)",
            fontsize=12,
            fontweight="bold",
            pad=8,
            color="#1A252C",
        )
        ax.set_ylabel("Availability (%)", fontsize=10.5, fontweight="bold", labelpad=8)
        ax.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7", zorder=0)

        # Formatting limits: zoom in around theoretical availability
        center_y = m.theoretical_availability * 100.0
        delta_y = max(abs(cum_mean[-1] - m.theoretical_availability) * 100.0 * 8.0, 0.015)
        ax.set_ylim(center_y - delta_y, center_y + delta_y)

        # Annotation summary card
        status_text = "PASSED" if m.relative_error_availability_pct < 0.05 else "FAILED"
        stat_box_text = (
            f"Analytical Benchmark $A$: {m.theoretical_availability * 100.0:.4f}%\n"
            f"Simulated Mean $\\hat{{A}}$: {m.mean_availability * 100.0:.4f}%\n"
            f"Bilateral 95% CI: [{m.ci_availability_lower * 100.0:.4f}%, {m.ci_availability_upper * 100.0:.4f}%]\n"
            f"Availability Relative Error: {m.relative_error_availability_pct:.5f}%\n"
            f"Validation Status (<0.05%): {status_text}"
        )
        ax.text(
            0.985,
            0.08,
            stat_box_text,
            transform=ax.transAxes,
            fontsize=9.0,
            verticalalignment="bottom",
            horizontalalignment="right",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="#FFFFFF",
                edgecolor="#BDC3C7",
                alpha=0.92,
            ),
            zorder=5,
        )
        ax.legend(loc="upper right", fontsize=8.8, framealpha=0.92)

    axes[-1].set_xlabel("Monte Carlo Replications ($n$)", fontsize=11, fontweight="bold", labelpad=8)
    axes[-1].set_xlim(1, n_replicas)

    fig.suptitle(
        "Monte Carlo Asymptotic Convergence and Theoretical SLA Cross-Validation",
        fontsize=14,
        fontweight="bold",
        y=0.995,
        color="#1A252C",
    )
    fig.tight_layout()

    # Save consolidated 3-panel figure
    _save_figure_dual_formats(fig, "monte_carlo_convergence", out_dir)

    # Save individual scenario figures if requested
    if save_individual:
        for s_id, res in results_dict.items():
            fig_single, ax_single = plt.subplots(figsize=(10.0, 4.8))
            color = SCENARIO_COLORS.get(s_id, "#2C3E50")
            cum_mean, _, margin = compute_running_statistics(
                res.availability,
                confidence_level=res.config.confidence_level,
            )
            n_replicas = len(res.availability)
            x_vals = np.arange(1, n_replicas + 1)
            start_step = min(10, n_replicas - 1)

            ax_single.fill_between(
                x_vals[start_step:],
                (cum_mean - margin)[start_step:] * 100.0,
                (cum_mean + margin)[start_step:] * 100.0,
                color=color,
                alpha=0.18,
                label=r"Empirical $95\%$ Confidence Envelope",
            )
            ax_single.plot(
                x_vals,
                cum_mean * 100.0,
                color=color,
                linewidth=1.8,
                label=rf"Cumulative Running Mean $\hat{{A}}(n)$",
            )
            ax_single.axhline(
                res.metrics.theoretical_availability * 100.0,
                color=THEORETICAL_LINE_COLOR,
                linestyle="--",
                linewidth=1.6,
                label=rf"Theoretical $A = {res.metrics.theoretical_availability * 100.0:.4f}\%$",
            )
            center_y = res.metrics.theoretical_availability * 100.0
            delta_y = max(abs(cum_mean[-1] - res.metrics.theoretical_availability) * 100.0 * 8.0, 0.015)
            ax_single.set_ylim(center_y - delta_y, center_y + delta_y)
            ax_single.set_xlim(1, n_replicas)
            ax_single.set_title(
                f"Scenario {s_id}: {res.name} — Asymptotic Convergence ($N = {n_replicas:,}$)",
                fontsize=11.5,
                fontweight="bold",
                pad=8,
            )
            ax_single.set_xlabel("Monte Carlo Replications ($n$)", fontsize=10.5, fontweight="bold")
            ax_single.set_ylabel("Availability (%)", fontsize=10.5, fontweight="bold")
            ax_single.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7")
            ax_single.legend(loc="upper right", fontsize=9.0)
            fig_single.tight_layout()
            _save_figure_dual_formats(fig_single, f"monte_carlo_convergence_scenario_{s_id}", out_dir)
            plt.close(fig_single)

    return fig


def plot_downtime_histograms(
    results: Optional[Union[ScenarioSimulationResult, Dict[int, ScenarioSimulationResult], List[ScenarioSimulationResult]]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    save_individual: bool = True,
    figsize: Tuple[float, float] = (16.0, 5.5),
) -> plt.Figure:
    """Plot empirical annual downtime distributions with superimposed mean and 95th percentile markers.

    Illustrates the empirical probability density and frequency distribution of annual downtime
    accumulated over N = 10^4 simulated years for Scenario 1, Scenario 2, and Scenario 3.
    Superimposes mean (D_hat), median (p50), 95th percentile (D_0.95 SLA Risk Boundary),
    and smooth KDE profile.

    Args:
        results: Simulation results (single result, dict of results by scenario_id, or None).
        output_dir: Target output directory for figure exports.
        save_individual: If True, also exports individual scenario histogram plots.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if results is None:
        cfg = SimulationConfig(num_replicas=DEFAULT_NUM_REPLICAS, seed=DEFAULT_SEED)
        results_dict = run_all_scenarios_simulation(config=cfg)
    elif isinstance(results, ScenarioSimulationResult):
        results_dict = {results.scenario_id: results}
    elif isinstance(results, dict):
        results_dict = results
    else:
        results_dict = {r.scenario_id: r for r in results}

    scenario_ids = sorted(results_dict.keys())

    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(scenario_ids),
        figsize=figsize,
    )
    if len(scenario_ids) == 1:
        axes = [axes]

    for ax, s_id in zip(axes, scenario_ids):
        res = results_dict[s_id]
        m = res.metrics
        downtimes = res.downtime_hours
        color = SCENARIO_COLORS.get(s_id, "#2C3E50")

        summary = compute_empirical_distribution_summary(
            downtimes,
            scenario_id=s_id,
            scenario_name=res.name,
        )

        # Plot normalized histogram
        counts, bin_edges, patches = ax.hist(
            downtimes,
            bins=45,
            density=True,
            color=color,
            alpha=0.68,
            edgecolor="#1A252C",
            linewidth=0.8,
            label="Empirical Density",
            zorder=3,
        )

        # Overlay smooth KDE curve
        try:
            kde = stats.gaussian_kde(downtimes)
            x_kde = np.linspace(float(np.min(downtimes)), float(np.max(downtimes)), 250)
            ax.plot(
                x_kde,
                kde(x_kde),
                color="#1A252C",
                linewidth=1.9,
                label="KDE Profile",
                zorder=4,
            )
        except Exception:
            pass

        # Superimpose Mean marker
        ax.axvline(
            summary.mean,
            color="#1A252C",
            linestyle="--",
            linewidth=1.8,
            label=rf"Mean $\hat{{D}} = {summary.mean:.2f}\text{{ h}}$",
            zorder=5,
        )

        # Superimpose Median marker
        ax.axvline(
            summary.median,
            color=MEDIAN_LINE_COLOR,
            linestyle=":",
            linewidth=1.6,
            label=rf"Median $p_{{50}} = {summary.median:.2f}\text{{ h}}$",
            zorder=5,
        )

        # Superimpose 95th Percentile marker (Value-at-Risk boundary)
        ax.axvline(
            summary.p95,
            color=PERCENTILE_95_COLOR,
            linestyle="-.",
            linewidth=2.0,
            label=rf"95th %ile $D_{{0.95}} = {summary.p95:.2f}\text{{ h}}$",
            zorder=5,
        )

        # Styling
        ax.set_title(
            f"Scenario {s_id}: {res.name}\nAnnual Downtime Distribution",
            fontsize=11.5,
            fontweight="bold",
            pad=8,
            color="#1A252C",
        )
        ax.set_xlabel("Annual Downtime (hours/year)", fontsize=10.5, fontweight="bold", labelpad=6)
        ax.set_ylabel("Probability Density", fontsize=10.5, fontweight="bold", labelpad=6)
        ax.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7", zorder=0)

        # Summary box
        stat_box_text = (
            f"Replications $N$: {summary.sample_size:,}\n"
            f"Analytical $D$: {m.theoretical_downtime_hours:.2f} h/yr\n"
            f"Simulated Mean $\\hat{{D}}$: {summary.mean:.2f} h/yr\n"
            f"Std Dev $s_D$: {summary.std:.2f} h\n"
            f"Median: {summary.median:.2f} h\n"
            f"95th %ile: {summary.p95:.2f} h\n"
            f"99th %ile: {summary.p99:.2f} h\n"
            f"Max Downtime: {summary.max_val:.2f} h"
        )
        ax.text(
            0.96,
            0.68,
            stat_box_text,
            transform=ax.transAxes,
            fontsize=8.5,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="#FFFFFF",
                edgecolor="#BDC3C7",
                alpha=0.92,
            ),
            zorder=6,
        )
        ax.legend(loc="upper right", fontsize=8.2, framealpha=0.90)

    fig.suptitle(
        "Empirical Annual Downtime Distributions and SLA Risk Thresholds (N = 10,000 Years)",
        fontsize=13.5,
        fontweight="bold",
        y=1.02,
        color="#1A252C",
    )
    fig.tight_layout()

    # Save consolidated 3-panel figure
    _save_figure_dual_formats(fig, "downtime_histogram", out_dir)

    # Save individual scenario figures if requested
    if save_individual:
        for s_id, res in results_dict.items():
            fig_single, ax_single = plt.subplots(figsize=(8.0, 5.0))
            color = SCENARIO_COLORS.get(s_id, "#2C3E50")
            downtimes = res.downtime_hours
            summary = compute_empirical_distribution_summary(downtimes, scenario_id=s_id, scenario_name=res.name)

            ax_single.hist(
                downtimes,
                bins=45,
                density=True,
                color=color,
                alpha=0.70,
                edgecolor="#1A252C",
                linewidth=0.8,
                label="Empirical Density",
            )
            try:
                kde = stats.gaussian_kde(downtimes)
                x_kde = np.linspace(float(np.min(downtimes)), float(np.max(downtimes)), 250)
                ax_single.plot(x_kde, kde(x_kde), color="#1A252C", linewidth=1.9, label="KDE Profile")
            except Exception:
                pass

            ax_single.axvline(summary.mean, color="#1A252C", linestyle="--", linewidth=1.8, label=rf"Mean $\hat{{D}} = {summary.mean:.2f}\text{{ h}}$")
            ax_single.axvline(summary.median, color=MEDIAN_LINE_COLOR, linestyle=":", linewidth=1.6, label=rf"Median $p_{{50}} = {summary.median:.2f}\text{{ h}}$")
            ax_single.axvline(summary.p95, color=PERCENTILE_95_COLOR, linestyle="-.", linewidth=2.0, label=rf"95th %ile $D_{{0.95}} = {summary.p95:.2f}\text{{ h}}$")

            ax_single.set_title(
                f"Scenario {s_id}: {res.name} — Annual Downtime Distribution ($N = {summary.sample_size:,}$)",
                fontsize=11.5,
                fontweight="bold",
                pad=8,
            )
            ax_single.set_xlabel("Annual Downtime (hours/year)", fontsize=10.5, fontweight="bold")
            ax_single.set_ylabel("Probability Density", fontsize=10.5, fontweight="bold")
            ax_single.grid(True, linestyle="--", alpha=0.5, color="#BDC3C7")
            ax_single.legend(loc="upper right", fontsize=8.8)
            fig_single.tight_layout()
            _save_figure_dual_formats(fig_single, f"downtime_histogram_scenario_{s_id}", out_dir)
            plt.close(fig_single)

    return fig


def plot_simulation_subsystem_breakdown(
    results: Optional[Union[Dict[int, ScenarioSimulationResult], List[ScenarioSimulationResult]]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    figsize: Tuple[float, float] = (13.0, 5.5),
) -> plt.Figure:
    """Plot subsystem downtime breakdown contrasting analytical benchmarks with Monte Carlo estimates.

    Demonstrates that the stochastic simulation confirms the Pareto principle:
    - In Scenario 1: App and DB represent >94% of downtime.
    - In Scenario 2: App downtime collapses by 98%, shifting the dominant bottleneck to DB and external PGW.
    - In Scenario 3: External PGW outage is eliminated, leaving DB as the primary residual bottleneck.

    Args:
        results: Simulation results dictionary or list (defaults to fresh run).
        output_dir: Target output directory for figure exports.
        figsize: Matplotlib figure dimensions.

    Returns:
        The generated matplotlib Figure object.
    """
    out_dir = _resolve_output_dir(output_dir)

    if results is None:
        cfg = SimulationConfig(num_replicas=DEFAULT_NUM_REPLICAS, seed=DEFAULT_SEED)
        results_dict = run_all_scenarios_simulation(config=cfg)
    elif isinstance(results, dict):
        results_dict = results
    else:
        results_dict = {r.scenario_id: r for r in results}

    # Compare Scenario 1 and Scenario 2
    fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=figsize, sharey=False)

    blocks = ["LB", "App", "DB", "PGW"]
    colors = [BLOCK_COLORS[b] for b in blocks]

    # Scenario 1 Analytical vs Simulated
    s1_res = results_dict.get(1)
    if s1_res is not None:
        x_indices = np.arange(len(blocks))
        bar_width = 0.35

        # Analytical values
        analytical_s1 = [0.876, 43.800, 43.800, 4.380]
        simulated_s1 = [float(np.mean(s1_res.subsystem_downtimes[b])) for b in blocks]

        rects1 = ax1.bar(
            x_indices - bar_width / 2.0,
            analytical_s1,
            bar_width,
            label="Analytical Benchmark",
            color="#7F8C8D",
            alpha=0.85,
            edgecolor="#1A252C",
        )
        rects2 = ax1.bar(
            x_indices + bar_width / 2.0,
            simulated_s1,
            bar_width,
            label=r"Monte Carlo Mean $\hat{D}_i$",
            color=colors,
            alpha=0.90,
            edgecolor="#1A252C",
        )

        ax1.set_title("Scenario 1: Baseline Architecture\nSubsystem Downtime Contribution", fontsize=11, fontweight="bold", pad=8)
        ax1.set_ylabel("Annual Downtime (hours/year)", fontsize=10.5, fontweight="bold")
        ax1.set_xticks(x_indices)
        ax1.set_xticklabels(blocks, fontsize=10, fontweight="bold")
        ax1.grid(axis="y", linestyle="--", alpha=0.5, color="#BDC3C7")
        ax1.legend(loc="upper right", fontsize=8.8)

        # Annotate values on top of bars
        for rect in rects2:
            height = rect.get_height()
            ax1.annotate(
                f"{height:.2f} h",
                xy=(rect.get_x() + rect.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.2,
                fontweight="bold",
            )

    # Scenario 2 Analytical vs Simulated
    s2_res = results_dict.get(2)
    if s2_res is not None:
        x_indices = np.arange(len(blocks))
        bar_width = 0.35

        analytical_s2 = [0.876, 0.876, 4.380, 4.380]
        simulated_s2 = [float(np.mean(s2_res.subsystem_downtimes[b])) for b in blocks]

        rects1_s2 = ax2.bar(
            x_indices - bar_width / 2.0,
            analytical_s2,
            bar_width,
            label="Analytical Benchmark",
            color="#7F8C8D",
            alpha=0.85,
            edgecolor="#1A252C",
        )
        rects2_s2 = ax2.bar(
            x_indices + bar_width / 2.0,
            simulated_s2,
            bar_width,
            label=r"Monte Carlo Mean $\hat{D}_i$",
            color=colors,
            alpha=0.90,
            edgecolor="#1A252C",
        )

        ax2.set_title("Scenario 2: Multi-AZ Series-Parallel\nBottleneck Shift to DB & PGW", fontsize=11, fontweight="bold", pad=8)
        ax2.set_ylabel("Annual Downtime (hours/year)", fontsize=10.5, fontweight="bold")
        ax2.set_xticks(x_indices)
        ax2.set_xticklabels(blocks, fontsize=10, fontweight="bold")
        ax2.grid(axis="y", linestyle="--", alpha=0.5, color="#BDC3C7")
        ax2.legend(loc="upper left", fontsize=8.8)

        for rect in rects2_s2:
            height = rect.get_height()
            ax2.annotate(
                f"{height:.2f} h",
                xy=(rect.get_x() + rect.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.2,
                fontweight="bold",
            )

    fig.suptitle(
        "Monte Carlo Validation of Subsystem Downtimes and Architectural Bottleneck Shift",
        fontsize=13,
        fontweight="bold",
        y=1.02,
        color="#1A252C",
    )
    fig.tight_layout()

    _save_figure_dual_formats(fig, "monte_carlo_pareto_validation", out_dir)
    return fig


def generate_all_monte_carlo_diagrams(
    results: Optional[Union[Dict[int, ScenarioSimulationResult], List[ScenarioSimulationResult]]] = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Path]:
    """Generate and export all Monte Carlo convergence, histogram, and validation figures.

    Produces:
    - monte_carlo_convergence.pdf / .png
    - downtime_histogram.pdf / .png
    - monte_carlo_pareto_validation.pdf / .png
    - Individual scenario convergence and histogram figures

    Args:
        results: Simulation results (or None to execute simulation).
        output_dir: Target output directory for figure exports.

    Returns:
        Dictionary mapping figure keys to resolved output file paths.
    """
    out_dir = _resolve_output_dir(output_dir)

    if results is None:
        cfg = SimulationConfig(num_replicas=DEFAULT_NUM_REPLICAS, seed=DEFAULT_SEED)
        results_dict = run_all_scenarios_simulation(config=cfg)
    elif isinstance(results, dict):
        results_dict = results
    else:
        results_dict = {r.scenario_id: r for r in results}

    fig_conv = plot_monte_carlo_convergence(results_dict, output_dir=out_dir, save_individual=True)
    plt.close(fig_conv)

    fig_hist = plot_downtime_histograms(results_dict, output_dir=out_dir, save_individual=True)
    plt.close(fig_hist)

    fig_pareto = plot_simulation_subsystem_breakdown(results_dict, output_dir=out_dir)
    plt.close(fig_pareto)

    created_files: Dict[str, Path] = {}
    expected_names = [
        "monte_carlo_convergence.pdf",
        "monte_carlo_convergence.png",
        "downtime_histogram.pdf",
        "downtime_histogram.png",
        "monte_carlo_pareto_validation.pdf",
        "monte_carlo_pareto_validation.png",
        "monte_carlo_convergence_scenario_1.pdf",
        "monte_carlo_convergence_scenario_1.png",
        "monte_carlo_convergence_scenario_2.pdf",
        "monte_carlo_convergence_scenario_2.png",
        "monte_carlo_convergence_scenario_3.pdf",
        "monte_carlo_convergence_scenario_3.png",
        "downtime_histogram_scenario_1.pdf",
        "downtime_histogram_scenario_1.png",
        "downtime_histogram_scenario_2.pdf",
        "downtime_histogram_scenario_2.png",
        "downtime_histogram_scenario_3.pdf",
        "downtime_histogram_scenario_3.png",
    ]
    for fname in expected_names:
        p = out_dir / fname
        if p.exists():
            created_files[fname] = p

    return created_files
