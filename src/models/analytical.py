"""
Analytical Availability and Reliability Modeling for Cloud Payment Architectures.

This module provides closed-form analytical models, functional block definitions,
availability calculations, and downtime estimations for the Systems Reliability
Engineering capstone project (Milestone 1, Issue #1).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class BlockParameters:
    """Parameters representing a single functional subsystem block.

    Attributes:
        name: Human-readable subsystem name.
        code: Short block identifier (e.g., LB, App, DB, PGW).
        tier: Architectural tier description.
        availability_base: Nominal single-unit steady-state availability (A_i).
        availability_redundant: Nominal redundant steady-state availability (A_i_red), if applicable.
        mttr_hours: Nominal mean time to repair/recover in hours.
        reference_sla: Literature or cloud provider SLA reference.
    """
    name: str
    code: str
    tier: str
    availability_base: float
    availability_redundant: Optional[float] = None
    mttr_hours: float = 0.5
    reference_sla: str = ""

    @property
    def unavailability_base(self) -> float:
        """Baseline steady-state unavailability U = 1 - A."""
        return 1.0 - self.availability_base

    @property
    def unavailability_redundant(self) -> Optional[float]:
        """Redundant steady-state unavailability U_red = 1 - A_red."""
        if self.availability_redundant is not None:
            return 1.0 - self.availability_redundant
        return None

    @property
    def lambda_base(self) -> float:
        """Constant failure rate lambda (failures/hour) in baseline configuration.

        Derived from A = mu / (lambda + mu) => lambda = mu * (1 - A) / A.
        """
        mu = 1.0 / self.mttr_hours
        return mu * self.unavailability_base / self.availability_base

    @property
    def mtbf_hours_base(self) -> float:
        """Mean Time Between Failures (MTBF) in hours for baseline."""
        return 1.0 / self.lambda_base

    @property
    def annual_downtime_hours_base(self) -> float:
        """Baseline expected annual downtime in hours (8760 h/year)."""
        return self.unavailability_base * 8760.0

    @property
    def annual_downtime_hours_redundant(self) -> Optional[float]:
        """Redundant expected annual downtime in hours (8760 h/year)."""
        if self.availability_redundant is not None:
            return self.unavailability_redundant * 8760.0
        return None


# Standard nominal system parameters based on official Cloud SLAs
DEFAULT_BLOCKS: Dict[str, BlockParameters] = {
    "LB": BlockParameters(
        name="Load Balancer",
        code="LB",
        tier="Ingress & Routing",
        availability_base=0.9999,      # 99.99% AWS ELB / GCP Cloud LB SLA
        availability_redundant=0.9999, # 99.99% managed cloud load balancer
        mttr_hours=0.25,               # 15 minutes automated VIP rerouting
        reference_sla="AWS ELB SLA / GCP Cloud Load Balancing SLA",
    ),
    "App": BlockParameters(
        name="Application Server",
        code="App",
        tier="Business Logic & Auth",
        availability_base=0.9950,      # 99.50% AWS EC2 Single Instance SLA
        availability_redundant=0.9999, # 99.99% AWS EC2 Multi-AZ SLA
        mttr_hours=0.50,               # 30 minutes auto-recovery/restart
        reference_sla="AWS EC2 / Azure VM Single vs Multi-AZ SLA",
    ),
    "DB": BlockParameters(
        name="Transactional Database",
        code="DB",
        tier="Data Persistence",
        availability_base=0.9950,      # 99.50% AWS RDS Single-AZ SLA
        availability_redundant=0.9995, # 99.95% AWS RDS Multi-AZ SLA
        mttr_hours=1.00,               # 60 minutes DB failover & synchronization
        reference_sla="AWS RDS Single-AZ vs Multi-AZ HA SLA",
    ),
    "PGW": BlockParameters(
        name="Payment Gateway",
        code="PGW",
        tier="External Settlement Network",
        availability_base=0.9995,        # 99.95% Payment Gateway API SLA
        availability_redundant=0.99999975, # 1 - (1 - 0.9995)^2 for active dual-gateway
        mttr_hours=0.50,                 # 30 minutes provider incident resolution
        reference_sla="Stripe / Adyen Payment Gateway SLA (Single vs Dual)",
    ),
}

HOURS_PER_YEAR: float = 8760.0
MINUTES_PER_YEAR: float = 8760.0 * 60.0


def calculate_series_availability(availabilities: List[float]) -> float:
    """Calculate the closed-form availability of an unredundant pure series system.

    Formula:
        A_series = prod_{i=1}^n A_i

    Args:
        availabilities: List of component availabilities A_i.

    Returns:
        System availability A_series.
    """
    return float(np.prod(availabilities))


def calculate_parallel_availability(availabilities: List[float]) -> float:
    """Calculate the closed-form availability of an active parallel redundant system.

    Formula:
        A_parallel = 1 - prod_{j=1}^m (1 - A_j)

    Args:
        availabilities: List of parallel component availabilities A_j.

    Returns:
        System availability A_parallel.
    """
    unavailabilities = [1.0 - a for a in availabilities]
    return float(1.0 - np.prod(unavailabilities))


def calculate_downtime_hours(availability: float, hours: float = HOURS_PER_YEAR) -> float:
    """Calculate expected downtime in hours over a given time horizon.

    Args:
        availability: Steady-state system availability A.
        hours: Horizon duration in hours (default: 8760 h = 1 year).

    Returns:
        Downtime in hours.
    """
    return (1.0 - availability) * hours


def calculate_downtime_minutes(availability: float, hours: float = HOURS_PER_YEAR) -> float:
    """Calculate expected downtime in minutes over a given time horizon."""
    return calculate_downtime_hours(availability, hours) * 60.0


@dataclass
class ScenarioMetrics:
    """Summary of analytical metrics for an architectural scenario."""
    scenario_id: int
    name: str
    description: str
    block_availabilities: Dict[str, float]
    system_availability: float
    unavailability: float
    annual_downtime_hours: float
    annual_downtime_minutes: float
    relative_reduction_vs_baseline_pct: float
    absolute_reduction_hours_vs_baseline: float


def evaluate_scenario_1(blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS) -> ScenarioMetrics:
    """Evaluate Scenario 1: Pure Series Baseline Architecture.

    Topology:
        LB -> App -> DB -> PGW
    Formula:
        A_base = A_LB * A_App * A_DB * A_PGW
    """
    a_lb = blocks["LB"].availability_base
    a_app = blocks["App"].availability_base
    a_db = blocks["DB"].availability_base
    a_pgw = blocks["PGW"].availability_base

    a_sys = calculate_series_availability([a_lb, a_app, a_db, a_pgw])
    u_sys = 1.0 - a_sys
    d_hours = calculate_downtime_hours(a_sys)
    d_mins = calculate_downtime_minutes(a_sys)

    return ScenarioMetrics(
        scenario_id=1,
        name="Scenario 1 (Baseline Series)",
        description="Pure series topology with single point of failure at every tier: LB -> App -> DB -> PGW",
        block_availabilities={
            "LB": a_lb,
            "App": a_app,
            "DB": a_db,
            "PGW": a_pgw,
        },
        system_availability=a_sys,
        unavailability=u_sys,
        annual_downtime_hours=d_hours,
        annual_downtime_minutes=d_mins,
        relative_reduction_vs_baseline_pct=0.0,
        absolute_reduction_hours_vs_baseline=0.0,
    )


def evaluate_scenario_2(blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS) -> ScenarioMetrics:
    """Evaluate Scenario 2: Multi-AZ Series-Parallel Architecture.

    Topology:
        LB -> [App Multi-AZ] -> [DB Multi-AZ HA] -> PGW
    Formula:
        A_red = A_LB * A_App,red * A_DB,red * A_PGW
    """
    baseline = evaluate_scenario_1(blocks)
    a_lb = blocks["LB"].availability_base
    a_app_red = blocks["App"].availability_redundant
    a_db_red = blocks["DB"].availability_redundant
    a_pgw = blocks["PGW"].availability_base

    a_sys = calculate_series_availability([a_lb, a_app_red, a_db_red, a_pgw])
    u_sys = 1.0 - a_sys
    d_hours = calculate_downtime_hours(a_sys)
    d_mins = calculate_downtime_minutes(a_sys)

    d_saved = baseline.annual_downtime_hours - d_hours
    pct_reduction = (d_saved / baseline.annual_downtime_hours) * 100.0

    return ScenarioMetrics(
        scenario_id=2,
        name="Scenario 2 (Multi-AZ Series-Parallel)",
        description="Active Multi-AZ redundancy on App and DB tiers: LB -> [App1 || App2] -> [DB1 || DB2] -> PGW",
        block_availabilities={
            "LB": a_lb,
            "App": a_app_red,
            "DB": a_db_red,
            "PGW": a_pgw,
        },
        system_availability=a_sys,
        unavailability=u_sys,
        annual_downtime_hours=d_hours,
        annual_downtime_minutes=d_mins,
        relative_reduction_vs_baseline_pct=pct_reduction,
        absolute_reduction_hours_vs_baseline=d_saved,
    )


def evaluate_scenario_3(blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS) -> ScenarioMetrics:
    """Evaluate Scenario 3: Multi-Gateway Expansion Architecture.

    Topology:
        LB -> [App Multi-AZ] -> [DB Multi-AZ HA] -> [PGW Dual-Active]
    Formula:
        A_scen3 = A_LB * A_App,red * A_DB,red * A_PGW,red
    """
    baseline = evaluate_scenario_1(blocks)
    a_lb = blocks["LB"].availability_base
    a_app_red = blocks["App"].availability_redundant
    a_db_red = blocks["DB"].availability_redundant
    a_pgw_red = blocks["PGW"].availability_redundant

    a_sys = calculate_series_availability([a_lb, a_app_red, a_db_red, a_pgw_red])
    u_sys = 1.0 - a_sys
    d_hours = calculate_downtime_hours(a_sys)
    d_mins = calculate_downtime_minutes(a_sys)

    d_saved = baseline.annual_downtime_hours - d_hours
    pct_reduction = (d_saved / baseline.annual_downtime_hours) * 100.0

    return ScenarioMetrics(
        scenario_id=3,
        name="Scenario 3 (Multi-Gateway Expansion)",
        description="Full end-to-end redundancy with Multi-AZ App, Multi-AZ DB, and Dual Payment Gateways",
        block_availabilities={
            "LB": a_lb,
            "App": a_app_red,
            "DB": a_db_red,
            "PGW": a_pgw_red,
        },
        system_availability=a_sys,
        unavailability=u_sys,
        annual_downtime_hours=d_hours,
        annual_downtime_minutes=d_mins,
        relative_reduction_vs_baseline_pct=pct_reduction,
        absolute_reduction_hours_vs_baseline=d_saved,
    )


def get_all_scenarios_summary(blocks: Dict[str, BlockParameters] = DEFAULT_BLOCKS) -> List[ScenarioMetrics]:
    """Return a list containing evaluated metrics for Scenarios 1, 2, and 3."""
    return [
        evaluate_scenario_1(blocks),
        evaluate_scenario_2(blocks),
        evaluate_scenario_3(blocks),
    ]
