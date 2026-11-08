"""
Models package for analytical and stochastic reliability engineering.
"""

from src.models.analytical import (
    BlockParameters,
    DEFAULT_BLOCKS,
    HOURS_PER_YEAR,
    MINUTES_PER_YEAR,
    calculate_series_availability,
    calculate_parallel_availability,
    calculate_downtime_hours,
    calculate_downtime_minutes,
    ScenarioMetrics,
    evaluate_scenario_1,
    evaluate_scenario_2,
    evaluate_scenario_3,
    get_all_scenarios_summary,
)

__all__ = [
    "BlockParameters",
    "DEFAULT_BLOCKS",
    "HOURS_PER_YEAR",
    "MINUTES_PER_YEAR",
    "calculate_series_availability",
    "calculate_parallel_availability",
    "calculate_downtime_hours",
    "calculate_downtime_minutes",
    "ScenarioMetrics",
    "evaluate_scenario_1",
    "evaluate_scenario_2",
    "evaluate_scenario_3",
    "get_all_scenarios_summary",
]
