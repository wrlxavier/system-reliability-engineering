# Systems Reliability Engineering

This repository contains analytical models, computational simulations, and evaluation routines for systems reliability and availability engineering.

## Repository Structure

```text
system-reliability-engineering/
├── data/
│   ├── processed/                     # Processed results and numerical simulation outputs
│   └── raw/                           # Baseline parameters and raw input data
├── docs/                              # Technical documentation, literature, and notes
├── notebooks/                         # Jupyter notebooks for analytical modeling and simulations
├── reports/
│   ├── figures/                       # Generated plots, charts, and reliability diagrams
│   └── presentation/                  # Presentation slides and visual deliverables
├── src/                               # Reusable Python routines and helper functions
├── .gitignore                         # Git ignore configuration
├── LICENSE                            # Repository license
├── README.md                          # Project overview and setup instructions
└── requirements.txt                   # Software dependency manifest
```

## Environment Setup

The project uses standard Python packaging tools. A local virtual environment is recommended to run the notebooks and scripts.

### Prerequisites

Python 3.10 or higher and the pip package manager are required.

### Installation

Clone the repository and navigate into the project directory.

Create a virtual environment.

```bash
python3 -m venv .venv
```

Activate the virtual environment on Linux or macOS.

```bash
source .venv/bin/activate
```

Activate the virtual environment on Windows.

```bash
.venv\Scripts\activate
```

Install the required dependencies.

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Notebooks

With the virtual environment active, launch the Jupyter interface.

```bash
jupyter notebook
```

Open the desired notebook in the `notebooks/` directory and execute the cells sequentially.

