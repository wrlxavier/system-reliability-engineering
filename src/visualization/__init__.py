"""
Visualization package for reliability diagrams, Pareto charts, and simulation plots.
"""

from src.visualization.draw_rbd import (
    draw_rbd_scenario_1,
    draw_rbd_scenario_2,
    draw_rbd_scenario_3,
    draw_rbd_comparison_all,
    generate_all_rbd_diagrams,
)
from src.visualization.plot_pareto import (
    plot_pareto_analysis,
    plot_pareto_single_scenario,
    plot_pareto_all_scenarios_3panel,
    generate_all_pareto_diagrams,
)
from src.visualization.plot_monte_carlo import (
    plot_monte_carlo_convergence,
    plot_downtime_histograms,
    plot_simulation_subsystem_breakdown,
    generate_all_monte_carlo_diagrams,
)
from src.visualization.plot_sensitivity import (
    plot_gateway_sla_sensitivity,
    plot_failover_and_ccf_sensitivity,
    plot_architectural_diminishing_returns,
    generate_all_sensitivity_diagrams,
)

__all__ = [
    "draw_rbd_scenario_1",
    "draw_rbd_scenario_2",
    "draw_rbd_scenario_3",
    "draw_rbd_comparison_all",
    "generate_all_rbd_diagrams",
    "plot_pareto_analysis",
    "plot_pareto_single_scenario",
    "plot_pareto_all_scenarios_3panel",
    "generate_all_pareto_diagrams",
    "plot_monte_carlo_convergence",
    "plot_downtime_histograms",
    "plot_simulation_subsystem_breakdown",
    "generate_all_monte_carlo_diagrams",
    "plot_gateway_sla_sensitivity",
    "plot_failover_and_ccf_sensitivity",
    "plot_architectural_diminishing_returns",
    "generate_all_sensitivity_diagrams",
]
