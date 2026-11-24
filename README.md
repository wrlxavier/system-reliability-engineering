# Systems Reliability Engineering (EEE017 — UFMG)

This repository contains the analytical models, Monte Carlo simulation engine, visualizations, notebooks, and test suite for the final project of **EEE017 – Systems Reliability Engineering** (*Confiabilidade de Sistemas*, UFMG): modeling reliability and steady-state availability in cloud payment architectures across three scenarios (**Baseline Series**, **Multi-AZ Series-Parallel**, and **Multi-Gateway Expansion**).

## Repository Structure

```text
system-reliability-engineering/
├── data/
│   ├── processed/
│   │   └── simulation_metrics.csv                  # Exported Monte Carlo metrics (N = 10^4, seed = 2026)
│   └── raw/                                        # Raw input directory placeholder
├── docs/
│   ├── CALCULATION_MEMORY.md                       # Complete analytical and simulation calculation memory
│   ├── PROBLEM_STATEMENT.md                        # System architecture context and SLA parameterization
│   └── proposta_trabalho.tex.txt                   # Historical project proposal (LaTeX source)
├── notebooks/
│   ├── 01_analytical_modeling.ipynb                # RBDs, availability, R(t), MTTF, and subsystem contributions
│   └── 02_monte_carlo_simulation.ipynb             # Monte Carlo simulation (T = 8760 h, N = 10^4) and validation
├── reports/
│   ├── figures/                                    # Generated PDF and 300 DPI PNG figures
│   └── presentation/                               # Presentation assets directory
├── src/
│   ├── models/
│   │   ├── analytical.py                           # Block parameters, series/parallel availability, Scenarios 1-3
│   │   ├── analytical_reliability.py               # Exponential R(t) and closed-form MTTF derivations
│   │   └── subsystem_contribution.py               # Percentage downtime contribution & bottleneck identification
│   ├── simulation/
│   │   └── monte_carlo.py                          # Monte Carlo engine (inverse transform, interval union, Student's t CI)
│   └── visualization/
│       ├── draw_rbd.py                             # Reliability Block Diagrams (RBDs)
│       ├── plot_monte_carlo.py                     # Convergence, downtime histograms, and subsystem validation plots
│       └── plot_subsystem_contribution.py          # Subsystem downtime contribution and cumulative share charts
├── tests/
│   ├── test_analytical_modeling.py                 # Analytical availability and RBD tests
│   ├── test_analytical_reliability.py              # R(t) and closed-form MTTF tests
│   ├── test_monte_carlo_simulation.py              # Monte Carlo simulation engine and CSV export tests
│   ├── test_monte_carlo_visualization.py           # Convergence, histogram, and Student's t CI visualization tests
│   └── test_subsystem_contribution.py              # Subsystem contribution and bottleneck shift tests
├── conftest.py                                     # Pytest root path setup
├── README.md                                       # Project overview and setup instructions
└── requirements.txt                                # Software dependency manifest
```

## Environment Setup

Python 3.10 or higher and `pip` are recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Running Notebooks and Scripts

Launch Jupyter from the activated virtual environment and run the notebooks in `notebooks/` sequentially:

```bash
jupyter notebook
```

To regenerate all figures directly from the Python modules:

```bash
python -m src.visualization.draw_rbd
python -m src.visualization.plot_subsystem_contribution
python -c "from src.visualization.plot_monte_carlo import generate_all_monte_carlo_diagrams; generate_all_monte_carlo_diagrams()"
```

## Automated Testing

Run the complete `pytest` test suite from the project root:

```bash
pytest -v
```
