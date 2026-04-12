# Multi-Stakeholder Ethical Decision-Making Frameworks (MEDF) for AI Systems

> **Project CCDS25-0582** | College of Computing and Data Science, Nanyang Technological University, Singapore (NTU Singapore)
>
> **Author:** Benjamin Oliver Yick (U2120984H)
> **Supervisor:** Dr. Zhang Jiehuang | **Examiner:** A/P A S Madhukumar
> **Degree:** Bachelor of Computing (Hons) in Data Science and Artificial Intelligence
> **Academic Year:** 2025/2026 | **Version:** 1.1.1 (Feature-Frozen)

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.133+-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.54+-FF4B4B)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Status](https://img.shields.io/badge/Status-Feature--Frozen-green)
![Version](https://img.shields.io/badge/Version-1.1.1-orange)
![Tests](https://img.shields.io/badge/Tests-105%20passed-brightgreen)

> **This repository is archived and frozen for FYP examination. No further development is planned.**

## Overview

MEDF is a decision-support platform that evaluates AI systems against three prominent governance frameworks using multi-criteria decision analysis. The platform operationalizes high-level ethical principles into quantifiable metrics across six unified dimensions, detects and quantifies conflicts between stakeholder perspectives through Spearman's rank correlation, and produces Pareto-optimal consensus solutions via NSGA-II multi-objective optimization. Three stakeholder perspectives drive the analysis: Developer, Regulator, and Affected Community.

**Live Dashboard:** [https://ccds25-0582-medf-api.streamlit.app/](https://ccds25-0582-medf-api.streamlit.app/)

## Features

- Multi-framework governance evaluation across the EU ALTAI, NIST AI RMF, and Singapore MGAF.
- MCDA scoring via TOPSIS and Weighted Sum Model (WSM).
- Stakeholder conflict detection using Spearman's rank correlation on both priority and contribution matrices.
- Pareto consensus optimization through NSGA-II multi-objective evolutionary search.
- Harm-adjusted risk classification with composite severity scoring.
- Interactive Streamlit dashboard with evaluation visualization, conflict heatmaps, and Pareto frontier exploration.
- RESTful API with 7 endpoints and full OpenAPI documentation.

## Architecture

MEDF follows a three-tier architecture. The presentation layer is an interactive Streamlit dashboard (`streamlit_app.py`) that provides evaluation configuration, results visualization, and Pareto frontier exploration. The API and orchestration layer is a FastAPI server with 7 endpoints across modular routers and strict Pydantic schema validation. The engine layer contains stateless algorithmic modules for TOPSIS/WSM scoring and harm assessment, backed by SQLite persistence (via SQLAlchemy) and YAML framework configuration files.

## Governance Frameworks

| Framework | Criteria | Sub-items | Sub-item Type |
|-----------|----------|-----------|---------------|
| EU ALTAI | 6 | 22 | Requirements |
| NIST RMF | 6 | 19 | Subcategories |
| Singapore MGAF | 6 | 20 | Principles |

Framework definitions are stored as version-controlled YAML files in `app/frameworks/`.

## Case Studies

Three real-world case studies validate the platform's analytical capabilities:

1. Metropolitan Police Live Facial Recognition.
2. iTutorGroup Automated Hiring Screening.
3. Royal Free NHS-DeepMind Streams Deployment.

Case study data files are located in the `case_studies/` directory.

## Testing

105 automated tests across 33 test files cover unit, integration, property-based, and end-to-end scenarios.

```bash
pytest --tb=short -q
```

## Local Setup

1. Clone the repository:

```bash
git clone https://github.com/benjaminyjr17/ccds25-0582-medf.git
cd ccds25-0582-medf
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. Start the dashboard:

```bash
streamlit run streamlit_app.py
```

## License

This project is released under the MIT License. See `LICENSE` for details.

## Version History

v1.1.1: Final frozen release for FYP defense and examination (April 17, 2026).
