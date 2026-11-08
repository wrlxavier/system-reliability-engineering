"""
Reliability Block Diagram (RBD) Generator for Cloud Payment Architectures.

This module renders high-resolution publication-quality vector diagrams (PDF and
PNG >= 300 DPI) for the Systems Reliability Engineering project (Milestone 1, Issue #1).
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MPath


def set_plot_style():
    """Configure matplotlib style for clean IEEE-grade publication diagrams."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
        "mathtext.fontset": "dejavusans",
        "figure.autolayout": False,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
    })


def draw_block(
    ax,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    availability_text: str,
    facecolor: str = "#EBF5FB",
    edgecolor: str = "#2980B9",
    corner_radius: float = 0.08,
):
    """Draw a single functional subsystem block with title, subtitle, and SLA metrics."""
    x0 = center_x - width / 2.0
    y0 = center_y - height / 2.0
    box = patches.FancyBboxPatch(
        (x0, y0),
        width,
        height,
        boxstyle=f"round,pad=0.0,rounding_size={corner_radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.6,
        zorder=3,
    )
    ax.add_patch(box)

    # Title
    ax.text(
        center_x,
        center_y + height * 0.22,
        title,
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        color="#1A252C",
        zorder=4,
    )
    # Subtitle
    ax.text(
        center_x,
        center_y - height * 0.02,
        subtitle,
        ha="center",
        va="center",
        fontsize=8.0,
        fontstyle="italic",
        color="#566573",
        zorder=4,
    )
    # Availability text
    ax.text(
        center_x,
        center_y - height * 0.26,
        availability_text,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color=edgecolor,
        zorder=4,
    )


def draw_terminal_node(
    ax,
    center_x: float,
    center_y: float,
    label: str,
    facecolor: str = "#EAFAF1",
    edgecolor: str = "#27AE60",
    width: float = 1.3,
    height: float = 0.55,
):
    """Draw transaction start/end boundary pill nodes."""
    x0 = center_x - width / 2.0
    y0 = center_y - height / 2.0
    box = patches.FancyBboxPatch(
        (x0, y0),
        width,
        height,
        boxstyle="round,pad=0.0,rounding_size=0.25",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.5,
        zorder=3,
    )
    ax.add_patch(box)
    ax.text(
        center_x,
        center_y,
        label,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#145A32",
        zorder=4,
    )


def draw_arrow(
    ax,
    x_start: float,
    y_start: float,
    x_end: float,
    y_end: float,
    color: str = "#2C3E50",
    lw: float = 1.5,
    arrow_size: float = 12,
):
    """Draw a directed flow connection between two points."""
    ax.annotate(
        "",
        xy=(x_end, y_end),
        xytext=(x_start, y_start),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=lw,
            mutation_scale=arrow_size,
        ),
        zorder=2,
    )


def draw_branch_split(
    ax,
    x_in: float,
    y_in: float,
    x_branch: float,
    y_top: float,
    y_bottom: float,
    x_out_top: float,
    x_out_bottom: float,
    color: str = "#2C3E50",
    lw: float = 1.4,
):
    """Draw a 1-to-2 parallel branch splitting connection."""
    # Line from (x_in, y_in) to (x_branch, y_in)
    ax.plot([x_in, x_branch], [y_in, y_in], color=color, lw=lw, zorder=2)
    # Vertical distributor line from y_bottom to y_top
    ax.plot([x_branch, x_branch], [y_bottom, y_top], color=color, lw=lw, zorder=2)
    # Arrows to top and bottom target blocks
    draw_arrow(ax, x_branch, y_top, x_out_top, y_top, color=color, lw=lw)
    draw_arrow(ax, x_branch, y_bottom, x_out_bottom, y_bottom, color=color, lw=lw)


def draw_branch_join(
    ax,
    x_in_top: float,
    y_top: float,
    x_in_bottom: float,
    y_bottom: float,
    x_branch: float,
    y_out: float,
    x_out: float,
    y_out_end: Optional[float] = None,
    color: str = "#2C3E50",
    lw: float = 1.4,
):
    """Draw a 2-to-1 parallel branch recombining connection."""
    if y_out_end is None:
        y_out_end = y_out
    ax.plot([x_in_top, x_branch], [y_top, y_top], color=color, lw=lw, zorder=2)
    ax.plot([x_in_bottom, x_branch], [y_bottom, y_bottom], color=color, lw=lw, zorder=2)
    ax.plot([x_branch, x_branch], [y_bottom, y_top], color=color, lw=lw, zorder=2)
    draw_arrow(ax, x_branch, y_out, x_out, y_out_end, color=color, lw=lw)


def draw_rbd_scenario_1(output_dir: Optional[Path] = None) -> plt.Figure:
    """Generate high-resolution vector RBD for Scenario 1: Pure Series Baseline."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11, 3.2), dpi=300)
    ax.set_xlim(-0.2, 11.8)
    ax.set_ylim(-0.8, 2.2)
    ax.axis("off")

    y_mid = 0.8
    block_w = 1.75
    block_h = 1.05

    # Title & Metric Banner
    ax.text(
        5.5,
        1.95,
        "Scenario 1: Baseline Architecture (Pure Series RBD)",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#1B2631",
    )
    ax.text(
        5.5,
        1.62,
        r"$A_{\mathrm{base}} = \prod_{i=1}^4 A_i = A_{\mathrm{LB}} \cdot A_{\mathrm{App}} \cdot A_{\mathrm{DB}} \cdot A_{\mathrm{PGW}} = 98.943\% \quad \Longrightarrow \quad 92.58\ \mathrm{h/year\ downtime}$",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#7B241C",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FDEDEC", edgecolor="#E6B0AA", lw=1.0),
    )

    # Nodes
    # 1. Ingress
    draw_terminal_node(ax, 0.7, y_mid, "Transaction\nIngress")

    # 2. LB
    x_lb = 2.45
    draw_block(
        ax,
        x_lb,
        y_mid,
        block_w,
        block_h,
        "Load Balancer",
        "AWS ELB (Ingress)",
        r"$A_1 = 99.99\%$",
        facecolor="#EBF5FB",
        edgecolor="#2980B9",
    )

    # 3. App
    x_app = 4.7
    draw_block(
        ax,
        x_app,
        y_mid,
        block_w,
        block_h,
        "Application",
        "Single VM Instance",
        r"$A_2 = 99.50\%$",
        facecolor="#FEF9E7",
        edgecolor="#B7950B",
    )

    # 4. DB
    x_db = 6.95
    draw_block(
        ax,
        x_db,
        y_mid,
        block_w,
        block_h,
        "Database",
        "Single-AZ RDS",
        r"$A_3 = 99.50\%$",
        facecolor="#FDF2E9",
        edgecolor="#CA6F1E",
    )

    # 5. PGW
    x_pgw = 9.2
    draw_block(
        ax,
        x_pgw,
        y_mid,
        block_w,
        block_h,
        "Payment Gateway",
        "External FinTech API",
        r"$A_4 = 99.95\%$",
        facecolor="#F4ECF7",
        edgecolor="#884EA0",
    )

    # 6. Egress
    draw_terminal_node(ax, 10.9, y_mid, "Payment\nSettled", facecolor="#EAFAF1", edgecolor="#27AE60")

    # Arrows
    draw_arrow(ax, 1.35, y_mid, x_lb - block_w / 2.0, y_mid)
    draw_arrow(ax, x_lb + block_w / 2.0, y_mid, x_app - block_w / 2.0, y_mid)
    draw_arrow(ax, x_app + block_w / 2.0, y_mid, x_db - block_w / 2.0, y_mid)
    draw_arrow(ax, x_db + block_w / 2.0, y_mid, x_pgw - block_w / 2.0, y_mid)
    draw_arrow(ax, x_pgw + block_w / 2.0, y_mid, 10.05, y_mid)

    # Single Point of Failure (SPOF) markers
    ax.text(
        5.5,
        -0.4,
        "Critical Flaw: Every component is a Single Point of Failure (SPOF). App and DB alone account for >94% of total downtime.",
        ha="center",
        va="center",
        fontsize=8.5,
        fontstyle="italic",
        color="#922B21",
    )

    plt.tight_layout()
    _save_figure(fig, "rbd_scenario_1", output_dir)
    return fig


def draw_rbd_scenario_2(output_dir: Optional[Path] = None) -> plt.Figure:
    """Generate high-resolution vector RBD for Scenario 2: Multi-AZ Series-Parallel."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11.5, 4.6), dpi=300)
    ax.set_xlim(-0.2, 11.8)
    ax.set_ylim(-1.4, 2.9)
    ax.axis("off")

    y_mid = 0.7
    y_top = 1.35
    y_bottom = 0.05
    block_w = 1.6
    block_h = 0.85

    # Title & Banner
    ax.text(
        5.7,
        2.65,
        "Scenario 2: Multi-AZ Redundant Architecture (Series-Parallel RBD)",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#1B2631",
    )
    ax.text(
        5.7,
        2.30,
        r"$A_{\mathrm{red}} = A_1 \cdot A_{2,\mathrm{red}} \cdot A_{3,\mathrm{red}} \cdot A_4 = 99.880\% \quad \Longrightarrow \quad 10.51\ \mathrm{h/year\ downtime}\ (-88.6\%\ \mathrm{vs.\ baseline})$",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#1E8449",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#EAFAF1", edgecolor="#A9DFBF", lw=1.0),
    )

    # 1. Ingress
    draw_terminal_node(ax, 0.7, y_mid, "Transaction\nIngress")

    # 2. LB
    x_lb = 2.1
    draw_block(
        ax,
        x_lb,
        y_mid,
        1.45,
        0.95,
        "Load Balancer",
        "AWS ELB Multi-AZ",
        r"$A_1 = 99.99\%$",
        facecolor="#EBF5FB",
        edgecolor="#2980B9",
    )
    draw_arrow(ax, 1.35, y_mid, x_lb - 1.45 / 2.0, y_mid)

    # Multi-AZ Bounding Box for App Tier
    app_box = patches.FancyBboxPatch(
        (3.35, -0.65),
        2.3,
        2.7,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#F4F6F6",
        edgecolor="#27AE60",
        linestyle="--",
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(app_box)
    ax.text(
        4.5,
        1.95,
        "Application Tier (Multi-AZ)\n" + r"$A_{2,\mathrm{red}} = 99.99\%$",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#1E8449",
    )

    # App Parallel Nodes
    x_app = 4.5
    draw_block(
        ax,
        x_app,
        y_top,
        block_w,
        block_h,
        "App Node 1",
        "Zone A (Active)",
        r"$A_2 = 99.50\%$",
        facecolor="#E8F8F5",
        edgecolor="#27AE60",
    )
    draw_block(
        ax,
        x_app,
        y_bottom,
        block_w,
        block_h,
        "App Node 2",
        "Zone B (Active)",
        r"$A_2 = 99.50\%$",
        facecolor="#E8F8F5",
        edgecolor="#27AE60",
    )

    # Multi-AZ Bounding Box for DB Tier
    db_box = patches.FancyBboxPatch(
        (6.3, -0.65),
        2.3,
        2.7,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#F4F6F6",
        edgecolor="#D35400",
        linestyle="--",
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(db_box)
    ax.text(
        7.45,
        1.95,
        "Database Tier (Multi-AZ HA)\n" + r"$A_{3,\mathrm{red}} = 99.95\%$",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#BA4A00",
    )

    # DB Parallel Nodes
    x_db = 7.45
    draw_block(
        ax,
        x_db,
        y_top,
        block_w,
        block_h,
        "Primary DB",
        "Zone A (Read/Write)",
        r"$A_3 = 99.50\%$",
        facecolor="#FEF5E7",
        edgecolor="#D35400",
    )
    draw_block(
        ax,
        x_db,
        y_bottom,
        block_w,
        block_h,
        "Sync Standby DB",
        "Zone B (Hot Failover)",
        r"$A_3 = 99.50\%$",
        facecolor="#FEF5E7",
        edgecolor="#D35400",
    )

    # 4. PGW
    x_pgw = 9.85
    draw_block(
        ax,
        x_pgw,
        y_mid,
        1.55,
        0.95,
        "Payment Gateway",
        "Single Provider API",
        r"$A_4 = 99.95\%$",
        facecolor="#F4ECF7",
        edgecolor="#884EA0",
    )

    # 5. Egress
    draw_terminal_node(ax, 11.2, y_mid, "Payment\nSettled", facecolor="#EAFAF1", edgecolor="#27AE60", width=1.1)

    # Connections
    # LB -> App (split)
    draw_branch_split(ax, x_lb + 1.45 / 2.0, y_mid, 3.45, y_top, y_bottom, x_app - block_w / 2.0, x_app - block_w / 2.0)

    # App -> DB (recombine & cross-feed)
    draw_branch_join(ax, x_app + block_w / 2.0, y_top, x_app + block_w / 2.0, y_bottom, 5.5, y_mid, 5.8, y_mid)
    draw_branch_split(ax, 5.8, y_mid, 6.4, y_top, y_bottom, x_db - block_w / 2.0, x_db - block_w / 2.0)

    # DB -> PGW (join)
    draw_branch_join(ax, x_db + block_w / 2.0, y_top, x_db + block_w / 2.0, y_bottom, 8.85, y_mid, x_pgw - 1.55 / 2.0, y_mid)

    # PGW -> Egress
    draw_arrow(ax, x_pgw + 1.55 / 2.0, y_mid, 10.65, y_mid)

    # Note on bottleneck transition
    ax.text(
        5.7,
        -1.05,
        "Bottleneck Shift: With internal tiers redundant, the external Payment Gateway (PGW) becomes the dominant single point of failure (4.38 h/yr).",
        ha="center",
        va="center",
        fontsize=8.5,
        fontstyle="italic",
        color="#7D6608",
    )

    plt.tight_layout()
    _save_figure(fig, "rbd_scenario_2", output_dir)
    return fig


def draw_rbd_scenario_3(output_dir: Optional[Path] = None) -> plt.Figure:
    """Generate high-resolution vector RBD for Scenario 3: Multi-Gateway Expansion."""
    set_plot_style()
    fig, ax = plt.subplots(figsize=(12.0, 4.8), dpi=300)
    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(-1.5, 2.9)
    ax.axis("off")

    y_mid = 0.7
    y_top = 1.35
    y_bottom = 0.05
    block_w = 1.55
    block_h = 0.85

    # Title & Banner
    ax.text(
        6.0,
        2.65,
        "Scenario 3: Multi-Gateway Expansion Architecture (End-to-End Fault Tolerance)",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#1B2631",
    )
    ax.text(
        6.0,
        2.30,
        r"$A_{\mathrm{scen3}} = A_1 \cdot A_{2,\mathrm{red}} \cdot A_{3,\mathrm{red}} \cdot A_{4,\mathrm{red}} = 99.930\% \quad \Longrightarrow \quad 6.13\ \mathrm{h/year\ downtime}\ (-93.4\%\ \mathrm{vs.\ baseline})$",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#154360",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#EBF5FB", edgecolor="#AED6F1", lw=1.0),
    )

    # 1. Ingress
    draw_terminal_node(ax, 0.65, y_mid, "Transaction\nIngress")

    # 2. LB
    x_lb = 1.95
    draw_block(
        ax,
        x_lb,
        y_mid,
        1.35,
        0.95,
        "Load Balancer",
        "AWS ELB Ingress",
        r"$A_1 = 99.99\%$",
        facecolor="#EBF5FB",
        edgecolor="#2980B9",
    )
    draw_arrow(ax, 1.30, y_mid, x_lb - 1.35 / 2.0, y_mid)

    # App Tier Bounding Box
    app_box = patches.FancyBboxPatch(
        (3.05, -0.65),
        2.1,
        2.7,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#F4F6F6",
        edgecolor="#27AE60",
        linestyle="--",
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(app_box)
    ax.text(
        4.1,
        1.95,
        "App Tier (Multi-AZ)\n" + r"$A_{2,\mathrm{red}} = 99.99\%$",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#1E8449",
    )

    # App Nodes
    x_app = 4.1
    draw_block(ax, x_app, y_top, block_w, block_h, "App Node 1", "Zone A (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")
    draw_block(ax, x_app, y_bottom, block_w, block_h, "App Node 2", "Zone B (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")

    # DB Tier Bounding Box
    db_box = patches.FancyBboxPatch(
        (5.7, -0.65),
        2.1,
        2.7,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#F4F6F6",
        edgecolor="#D35400",
        linestyle="--",
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(db_box)
    ax.text(
        6.75,
        1.95,
        "DB Tier (Multi-AZ HA)\n" + r"$A_{3,\mathrm{red}} = 99.95\%$",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#BA4A00",
    )

    # DB Nodes
    x_db = 6.75
    draw_block(ax, x_db, y_top, block_w, block_h, "Primary DB", "Zone A (Sync)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")
    draw_block(ax, x_db, y_bottom, block_w, block_h, "Replica DB", "Zone B (Standby)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")

    # Payment Gateway Tier Bounding Box
    pgw_box = patches.FancyBboxPatch(
        (8.35, -0.65),
        2.2,
        2.7,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        facecolor="#F4F6F6",
        edgecolor="#884EA0",
        linestyle="--",
        linewidth=1.2,
        zorder=1,
    )
    ax.add_patch(pgw_box)
    ax.text(
        9.45,
        1.95,
        "PGW Tier (Multi-Gateway)\n" + r"$A_{4,\mathrm{red}} = 99.999975\%$",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#6C3483",
    )

    # PGW Parallel Nodes
    x_pgw = 9.45
    draw_block(
        ax,
        x_pgw,
        y_top,
        block_w,
        block_h,
        "Gateway A",
        "Primary (e.g. Stripe)",
        r"$A_4 = 99.95\%$",
        facecolor="#F4ECF7",
        edgecolor="#884EA0",
    )
    draw_block(
        ax,
        x_pgw,
        y_bottom,
        block_w,
        block_h,
        "Gateway B",
        "Secondary (Adyen)",
        r"$A_4 = 99.95\%$",
        facecolor="#F4ECF7",
        edgecolor="#884EA0",
    )

    # Egress
    draw_terminal_node(ax, 11.65, y_mid, "Payment\nSettled", facecolor="#EAFAF1", edgecolor="#27AE60", width=1.0)

    # Connections
    # LB -> App
    draw_branch_split(ax, x_lb + 1.35 / 2.0, y_mid, 3.15, y_top, y_bottom, x_app - block_w / 2.0, x_app - block_w / 2.0)
    # App -> DB
    draw_branch_join(ax, x_app + block_w / 2.0, y_top, x_app + block_w / 2.0, y_bottom, 5.0, y_mid, 5.25, y_mid)
    draw_branch_split(ax, 5.25, y_mid, 5.8, y_top, y_bottom, x_db - block_w / 2.0, x_db - block_w / 2.0)
    # DB -> PGW
    draw_branch_join(ax, x_db + block_w / 2.0, y_top, x_db + block_w / 2.0, y_bottom, 7.65, y_mid, 7.9, y_mid)
    draw_branch_split(ax, 7.9, y_mid, 8.45, y_top, y_bottom, x_pgw - block_w / 2.0, x_pgw - block_w / 2.0)
    # PGW -> Egress
    draw_branch_join(ax, x_pgw + block_w / 2.0, y_top, x_pgw + block_w / 2.0, y_bottom, 10.85, y_mid, 11.15, y_mid)

    # Footnote
    ax.text(
        6.0,
        -1.15,
        "Architectural Peak: Dual external gateway routing reduces annual third-party downtime to 0.002 h/year (approx. 8 seconds/year).",
        ha="center",
        va="center",
        fontsize=8.5,
        fontstyle="italic",
        color="#154360",
    )

    plt.tight_layout()
    _save_figure(fig, "rbd_scenario_3", output_dir)
    return fig


def draw_rbd_comparison_all(output_dir: Optional[Path] = None) -> plt.Figure:
    """Generate a combined 3-panel comparative RBD diagram for paper/presentation."""
    set_plot_style()
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 11.0), dpi=300)

    # We reuse the logic for subplots
    ax1, ax2, ax3 = axes

    # --- Panel 1: Scenario 1 ---
    ax1.set_xlim(-0.2, 11.4)
    ax1.set_ylim(-0.7, 1.8)
    ax1.axis("off")
    y_mid = 0.5
    block_w = 1.7
    block_h = 0.95

    ax1.text(0.0, 1.55, "(a) Scenario 1: Baseline Architecture (Pure Series)", fontsize=11, fontweight="bold", color="#1B2631")
    ax1.text(11.2, 1.55, r"$A_{\mathrm{base}} = 98.943\% \ (92.58\ \mathrm{h/yr})$", ha="right", fontsize=10, fontweight="bold", color="#7B241C")

    draw_terminal_node(ax1, 0.7, y_mid, "Ingress")
    draw_block(ax1, 2.35, y_mid, block_w, block_h, "Load Balancer", "AWS ELB Ingress", r"$A_1 = 99.99\%$", facecolor="#EBF5FB", edgecolor="#2980B9")
    draw_block(ax1, 4.6, y_mid, block_w, block_h, "Application", "Single VM Instance", r"$A_2 = 99.50\%$", facecolor="#FEF9E7", edgecolor="#B7950B")
    draw_block(ax1, 6.85, y_mid, block_w, block_h, "Database", "Single-AZ RDS", r"$A_3 = 99.50\%$", facecolor="#FDF2E9", edgecolor="#CA6F1E")
    draw_block(ax1, 9.1, y_mid, block_w, block_h, "Payment Gateway", "Single FinTech API", r"$A_4 = 99.95\%$", facecolor="#F4ECF7", edgecolor="#884EA0")
    draw_terminal_node(ax1, 10.65, y_mid, "Settled", facecolor="#EAFAF1", edgecolor="#27AE60", width=1.1)

    draw_arrow(ax1, 1.35, y_mid, 2.35 - block_w / 2.0, y_mid)
    draw_arrow(ax1, 2.35 + block_w / 2.0, y_mid, 4.6 - block_w / 2.0, y_mid)
    draw_arrow(ax1, 4.6 + block_w / 2.0, y_mid, 6.85 - block_w / 2.0, y_mid)
    draw_arrow(ax1, 6.85 + block_w / 2.0, y_mid, 9.1 - block_w / 2.0, y_mid)
    draw_arrow(ax1, 9.1 + block_w / 2.0, y_mid, 10.1, y_mid)

    # --- Panel 2: Scenario 2 ---
    ax2.set_xlim(-0.2, 11.4)
    ax2.set_ylim(-1.1, 2.2)
    ax2.axis("off")
    y_m = 0.55
    y_t = 1.15
    y_b = -0.05
    bw = 1.5
    bh = 0.75

    ax2.text(0.0, 1.95, "(b) Scenario 2: Multi-AZ Series-Parallel Architecture", fontsize=11, fontweight="bold", color="#1B2631")
    ax2.text(11.2, 1.95, r"$A_{\mathrm{red}} = 99.880\% \ (10.51\ \mathrm{h/yr},\ -88.6\%)$", ha="right", fontsize=10, fontweight="bold", color="#1E8449")

    draw_terminal_node(ax2, 0.7, y_m, "Ingress")
    draw_block(ax2, 2.1, y_m, 1.4, 0.85, "Load Balancer", "AWS ELB Multi-AZ", r"$A_1 = 99.99\%$", facecolor="#EBF5FB", edgecolor="#2980B9")
    draw_arrow(ax2, 1.35, y_m, 2.1 - 1.4 / 2.0, y_m)

    # App tier box
    app_box = patches.FancyBboxPatch((3.25, -0.65), 2.1, 2.4, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor="#F4F6F6", edgecolor="#27AE60", linestyle="--", linewidth=1.1, zorder=1)
    ax2.add_patch(app_box)
    ax2.text(4.3, 1.6, "App Tier (" + r"$A_{2,\mathrm{red}} = 99.99\%$)", ha="center", fontsize=8.0, fontweight="bold", color="#1E8449")
    draw_block(ax2, 4.3, y_t, bw, bh, "App Node 1", "Zone A (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")
    draw_block(ax2, 4.3, y_b, bw, bh, "App Node 2", "Zone B (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")

    # DB tier box
    db_box = patches.FancyBboxPatch((5.95, -0.65), 2.1, 2.4, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor="#F4F6F6", edgecolor="#D35400", linestyle="--", linewidth=1.1, zorder=1)
    ax2.add_patch(db_box)
    ax2.text(7.0, 1.6, "DB Tier (" + r"$A_{3,\mathrm{red}} = 99.95\%$)", ha="center", fontsize=8.0, fontweight="bold", color="#BA4A00")
    draw_block(ax2, 7.0, y_t, bw, bh, "Primary DB", "Zone A (Sync)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")
    draw_block(ax2, 7.0, y_b, bw, bh, "Replica DB", "Zone B (Standby)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")

    draw_block(ax2, 9.35, y_m, 1.5, 0.85, "Payment Gateway", "Single Provider API", r"$A_4 = 99.95\%$", facecolor="#F4ECF7", edgecolor="#884EA0")
    draw_terminal_node(ax2, 10.7, y_m, "Settled", facecolor="#EAFAF1", edgecolor="#27AE60", width=1.1)

    draw_branch_split(ax2, 2.1 + 1.4 / 2.0, y_m, 3.35, y_t, y_b, 4.3 - bw / 2.0, 4.3 - bw / 2.0)
    draw_branch_join(ax2, 4.3 + bw / 2.0, y_t, 4.3 + bw / 2.0, y_b, 5.25, y_m, 5.5, y_m)
    draw_branch_split(ax2, 5.5, y_m, 6.05, y_t, y_b, 7.0 - bw / 2.0, 7.0 - bw / 2.0)
    draw_branch_join(ax2, 7.0 + bw / 2.0, y_t, 7.0 + bw / 2.0, y_b, 8.25, y_m, 9.35 - 1.5 / 2.0, y_m)
    draw_arrow(ax2, 9.35 + 1.5 / 2.0, y_m, 10.15, y_m)

    # --- Panel 3: Scenario 3 ---
    ax3.set_xlim(-0.2, 11.4)
    ax3.set_ylim(-1.1, 2.2)
    ax3.axis("off")

    ax3.text(0.0, 1.95, "(c) Scenario 3: Multi-Gateway Expansion (Full Redundancy)", fontsize=11, fontweight="bold", color="#1B2631")
    ax3.text(11.2, 1.95, r"$A_{\mathrm{scen3}} = 99.930\% \ (6.13\ \mathrm{h/yr},\ -93.4\%)$", ha="right", fontsize=10, fontweight="bold", color="#154360")

    bw3 = 1.4
    draw_terminal_node(ax3, 0.6, y_m, "Ingress", width=1.0)
    draw_block(ax3, 1.8, y_m, 1.25, 0.85, "Load Balancer", "AWS ELB Ingress", r"$A_1 = 99.99\%$", facecolor="#EBF5FB", edgecolor="#2980B9")
    draw_arrow(ax3, 1.1, y_m, 1.8 - 1.25 / 2.0, y_m)

    # App
    app_b3 = patches.FancyBboxPatch((2.85, -0.65), 1.95, 2.4, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor="#F4F6F6", edgecolor="#27AE60", linestyle="--", linewidth=1.1, zorder=1)
    ax3.add_patch(app_b3)
    ax3.text(3.82, 1.6, "App Tier (" + r"$A_{2,\mathrm{red}} = 99.99\%$)", ha="center", fontsize=7.5, fontweight="bold", color="#1E8449")
    draw_block(ax3, 3.82, y_t, bw3, bh, "App Node 1", "Zone A (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")
    draw_block(ax3, 3.82, y_b, bw3, bh, "App Node 2", "Zone B (Active)", r"$A_2 = 99.50\%$", facecolor="#E8F8F5", edgecolor="#27AE60")

    # DB
    db_b3 = patches.FancyBboxPatch((5.25, -0.65), 1.95, 2.4, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor="#F4F6F6", edgecolor="#D35400", linestyle="--", linewidth=1.1, zorder=1)
    ax3.add_patch(db_b3)
    ax3.text(6.22, 1.6, "DB Tier (" + r"$A_{3,\mathrm{red}} = 99.95\%$)", ha="center", fontsize=7.5, fontweight="bold", color="#BA4A00")
    draw_block(ax3, 6.22, y_t, bw3, bh, "Primary DB", "Zone A (Sync)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")
    draw_block(ax3, 6.22, y_b, bw3, bh, "Replica DB", "Zone B (Standby)", r"$A_3 = 99.50\%$", facecolor="#FEF5E7", edgecolor="#D35400")

    # PGW
    pgw_b3 = patches.FancyBboxPatch((7.65, -0.65), 2.05, 2.4, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor="#F4F6F6", edgecolor="#884EA0", linestyle="--", linewidth=1.1, zorder=1)
    ax3.add_patch(pgw_b3)
    ax3.text(8.67, 1.6, "PGW Tier (" + r"$A_{4,\mathrm{red}} = 99.999975\%$)", ha="center", fontsize=7.5, fontweight="bold", color="#6C3483")
    draw_block(ax3, 8.67, y_t, bw3, bh, "Gateway A", "Primary (Stripe)", r"$A_4 = 99.95\%$", facecolor="#F4ECF7", edgecolor="#884EA0")
    draw_block(ax3, 8.67, y_b, bw3, bh, "Gateway B", "Secondary (Adyen)", r"$A_4 = 99.95\%$", facecolor="#F4ECF7", edgecolor="#884EA0")

    draw_terminal_node(ax3, 10.7, y_m, "Settled", facecolor="#EAFAF1", edgecolor="#27AE60", width=1.0)

    draw_branch_split(ax3, 1.8 + 1.25 / 2.0, y_m, 2.95, y_t, y_b, 3.82 - bw3 / 2.0, 3.82 - bw3 / 2.0)
    draw_branch_join(ax3, 3.82 + bw3 / 2.0, y_t, 3.82 + bw3 / 2.0, y_b, 4.65, y_m, 4.85, y_m)
    draw_branch_split(ax3, 4.85, y_m, 5.35, y_t, y_b, 6.22 - bw3 / 2.0, 6.22 - bw3 / 2.0)
    draw_branch_join(ax3, 6.22 + bw3 / 2.0, y_t, 6.22 + bw3 / 2.0, y_b, 7.05, y_m, 7.25, y_m)
    draw_branch_split(ax3, 7.25, y_m, 7.75, y_t, y_b, 8.67 - bw3 / 2.0, 8.67 - bw3 / 2.0)
    draw_branch_join(ax3, 8.67 + bw3 / 2.0, y_t, 8.67 + bw3 / 2.0, y_b, 9.95, y_m, 10.2, y_m)

    plt.tight_layout()
    _save_figure(fig, "rbd_comparison_all", output_dir)
    return fig


def _save_figure(fig: plt.Figure, basename: str, output_dir: Optional[Path] = None):
    """Save figure to PDF and PNG (300 DPI) in specified and default directories."""
    target_dirs = []
    if output_dir is not None:
        target_dirs.append(Path(output_dir))
    else:
        # Default location in reports/figures/
        repo_root = Path(__file__).resolve().parent.parent.parent
        target_dirs.append(repo_root / "reports" / "figures")

    for directory in target_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        pdf_path = directory / f"{basename}.pdf"
        png_path = directory / f"{basename}.png"
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
        print(f"Saved: {pdf_path} and {png_path}")


def generate_all_rbd_diagrams():
    """Generate all RBD figures for Scenarios 1, 2, 3, and comparison."""
    print("Generating RBD diagrams for all scenarios...")
    fig1 = draw_rbd_scenario_1()
    plt.close(fig1)

    fig2 = draw_rbd_scenario_2()
    plt.close(fig2)

    fig3 = draw_rbd_scenario_3()
    plt.close(fig3)

    fig_all = draw_rbd_comparison_all()
    plt.close(fig_all)
    print("All RBD diagrams successfully generated!")


if __name__ == "__main__":
    generate_all_rbd_diagrams()
