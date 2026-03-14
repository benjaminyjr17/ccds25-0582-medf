# MEDF: Multi-Stakeholder Ethical Decision-Making Frameworks for AI Systems

> **Project CCDS25-0582** | College of Computing and Data Science, Nanyang Technological University
>
> **Author:** Benjamin Oliver Yick (U2120984H)
> **Supervisor:** Dr. Zhang Jiehuang | **Examiner:** A/P A S Madhukumar
> **Degree:** Bachelor of Computing in Data Science and Artificial Intelligence
> **Academic Year:** 2025/2026 | **Version:** 1.1.0 (feature-frozen)

[![CI](https://github.com/benjaminyjr17/ccds25-0582-medf/actions/workflows/test.yml/badge.svg)](https://github.com/benjaminyjr17/ccds25-0582-medf/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.133+-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.54+-FF4B4B)
![License](https://img.shields.io/badge/License-NTU%20FYP-lightgrey)
![Status](https://img.shields.io/badge/Status-Feature--Frozen-green)
![Version](https://img.shields.io/badge/Version-1.1.0-orange)
![Tests](https://img.shields.io/badge/Tests-105%20passed-brightgreen)


## Abstract

As Artificial Intelligence systems become increasingly integrated into critical societal domains, the need for robust, transparent, and multi-stakeholder ethical evaluation becomes paramount. MEDF is a decision-support platform that provides a structured, reproducible, and auditable workflow for evaluating AI applications against prominent governance frameworks: the EU Assessment List for Trustworthy AI (ALTAI), the NIST AI Risk Management Framework (RMF), and Singapore's Model AI Governance Framework (MGAF). The system operationalizes high-level ethical principles into quantifiable metrics across six unified dimensions, surfaces and quantifies stakeholder disagreements, and employs multi-objective optimization (NSGA-II) to identify Pareto-optimal consensus solutions.


## Live Deployment

| Component | URL |
|---|---|
| **API Server** (FastAPI on Render) | <https://ccds25-0582-medf-api.onrender.com> |
| **Dashboard** (Streamlit Community Cloud) | <https://ccds25-0582-medf-api.streamlit.app> |
| **API Documentation** (OpenAPI) | <https://ccds25-0582-medf-api.onrender.com/docs> |

> **Note:** The Render free-tier instance may spin down after periods of inactivity. The first request can take 30–60 seconds while the service restarts.


## Six Unified Dimensions

MEDF harmonizes the three governance frameworks into a single evaluation model based on six dimensions derived from a systematic cross-framework analysis:

1. **Transparency and Explainability.** Assesses the degree to which the AI system's operations, decisions, and logic can be understood by relevant stakeholders.
2. **Fairness and Non-discrimination.** Evaluates whether the system produces equitable outcomes and avoids unjust bias based on protected characteristics.
3. **Safety and Robustness.** Measures technical reliability, resilience to errors and adversarial inputs, and the ability to fail gracefully.
4. **Privacy and Data Governance.** Assesses compliance with data protection principles including data minimization, consent, and security.
5. **Human Agency and Oversight.** Evaluates mechanisms for human intervention and ultimate authority over the system's decisions.
6. **Accountability.** Assesses mechanisms for redress, responsibility, and auditability.


## Governance Frameworks

| Framework | Origin | Criteria | Requirements/Subcategories |
|---|---|---|---|
| EU ALTAI | European Commission AI HLEG (2020) | 6 | 22 |
| NIST AI RMF | U.S. National Institute of Standards and Technology (2023) | 6 | 19 |
| Singapore MGAF | Personal Data Protection Commission (2020) | 6 | 20 |

Framework definitions are stored as version-controlled YAML files in `app/frameworks/`.


## System Architecture

MEDF follows a three-tier architecture with clear separation of concerns:

- **Presentation Layer.** Interactive Streamlit dashboard (`streamlit_app.py`) providing evaluation configuration, results visualization, conflict heatmaps, and Pareto frontier exploration.
- **API/Orchestration Layer.** FastAPI server with modular routers (`/api/evaluate`, `/api/conflicts`, `/api/pareto`, `/api/frameworks`, `/api/stakeholders`) and strict Pydantic schema validation.
- **Engine Layer.** Stateless algorithmic modules for TOPSIS/WSM scoring (`scoring_engine.py`), harm assessment (`harm_assessment.py`), and NSGA-II Pareto optimization (`routers/pareto.py`).
- **Data and Configuration Layer.** YAML framework registry, SQLite database (via SQLAlchemy), case study JSON files, and JSONL audit logging.


## Algorithms

- **TOPSIS** (Technique for Order of Preference by Similarity to Ideal Solution). Primary scoring method producing a closeness coefficient in [0, 1].
- **WSM** (Weighted Sum Model). Alternative scoring method provided for comparison.
- **Product Pooling.** Effective weights computed as the element-wise product of stakeholder and framework weight vectors, then re-normalized.
- **Spearman Rank Correlation.** Conflict detection computing both priority (weights-only) and system-salience (contribution-based) correlation matrices.
- **NSGA-II.** Multi-objective evolutionary optimization (via `pymoo`) for Pareto-optimal consensus weight vectors.
- **Harm Assessment.** Composite harm score: `h = 0.7 × (1 − s_norm) + 0.3 × d_bar`, where `s_norm` is the normalized dimension score and `d_bar` is the mean pairwise stakeholder weight disagreement.


## Case Studies

Three real-world case studies validate the platform's analytical capabilities:

| # | Case Study | Overall Score | Risk Level | Primary Weakness |
|---|---|---|---|---|
| I | Metropolitan Police Live Facial Recognition | 0.3866 | Critical | Fairness, Privacy |
| II | iTutorGroup Automated Hiring Screening | 0.3477 | Critical | Fairness |
| III | Royal Free NHS, DeepMind Streams App | 0.6003 | Medium | Privacy |

Case study data files are located in the `case_studies/` directory.


## Repository Structure

```text
ccds25-0582-medf/
├── app/
│   ├── main.py                  # FastAPI application entry point.
│   ├── models.py                # Pydantic schemas and SQLAlchemy ORM models.
│   ├── scoring_engine.py        # TOPSIS and WSM implementations.
│   ├── harm_assessment.py       # Harm severity classification module.
│   ├── framework_registry.py    # YAML framework loader and validator.
│   ├── routers/
│   │   ├── evaluate.py          # /api/evaluate endpoint.
│   │   ├── conflicts.py         # /api/conflicts endpoint and conflict analysis engine.
│   │   └── pareto.py            # /api/pareto endpoint and NSGA-II optimization.
│   └── frameworks/
│       ├── eu_altai.yaml        # EU ALTAI framework definition (22 requirements).
│       ├── nist_ai_rmf.yaml     # NIST AI RMF framework definition (19 subcategories).
│       └── sg_mgaf.yaml         # Singapore MGAF framework definition (20 principles).
├── streamlit_app.py             # Streamlit dashboard (single-file frontend).
├── tests/                       # 105 test functions across 33 test files.
├── case_studies/                # Pre-configured case study JSON files.
├── docs/
│   └── design_decisions.md      # Engineering decision log.
├── requirements.txt             # Pinned Python dependencies.
└── README.md
```


## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns the health status of the API server. |
| `GET` | `/api/frameworks` | Lists all available governance frameworks and their definitions. |
| `GET` | `/api/stakeholders` | Lists all registered stakeholder profiles. |
| `POST` | `/api/stakeholders` | Creates a new stakeholder profile with custom weights. |
| `POST` | `/api/evaluate` | Runs an ethical evaluation and returns per-framework and aggregated scores. |
| `POST` | `/api/conflicts` | Computes the stakeholder conflict matrix (contribution-based Spearman rho). |
| `POST` | `/api/pareto` | Runs NSGA-II optimization to find Pareto-optimal consensus weight vectors. |

Full interactive API documentation is available at the `/docs` endpoint of the deployed API server.


## Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | FastAPI |
| Frontend Framework | Streamlit |
| Data Persistence | SQLAlchemy + SQLite |
| Numerical Computing | NumPy |
| Multi-objective Optimization | pymoo (NSGA-II) |
| Schema Validation | Pydantic |
| Configuration | YAML |
| Testing | Pytest (105 functions, 33 files) |
| CI/CD | GitHub Actions |
| Deployment (API) | Render |
| Deployment (Dashboard) | Streamlit Community Cloud |


## Testing

The test suite covers unit, integration, property-based, and end-to-end scenarios:

```bash
pytest --tb=short -q
```

Key test modules include:

- `test_api_contract_lock.py` locks down the API schema to prevent regressions.
- `test_topsis_hand_verification.py` verifies TOPSIS scores against hand-calculated examples.
- End-to-end tests run complete evaluations with case study data.


## Reproducibility

- All Python dependencies are pinned to specific versions in `requirements.txt`.
- Core scoring algorithms are deterministic.
- NSGA-II uses a fixed random seed during evaluation runs.
- GitHub Actions runs the complete test suite on every push and pull request.


## References

This project builds on the following foundational works:

[1] J. Zhang, Y. Shu, and H. Yu, "Fairness in design: A framework for facilitating ethical artificial intelligence designs," Int. J. Crowd Sci., vol. 7, no. 1, pp. 32-39, 2023.

[2] European Commission High-Level Expert Group on Artificial Intelligence, "The assessment list for trustworthy artificial intelligence (ALTAI) for self-assessment," European Commission, 2020.

[3] National Institute of Standards and Technology, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, 2023.

[4] Personal Data Protection Commission Singapore, *Model Artificial Intelligence Governance Framework*, Singapore, 2020.

A complete list of references is provided in the accompanying FYP report.


## License

This project was developed as a Final Year Project (CCDS25-0582) at Nanyang Technological University. Please refer to the university's intellectual property policies for usage terms.


## Citation

If you use MEDF in academic work, please cite:

```text
B. O. Yick, "Multi-Stakeholder Ethical Decision-Making Frameworks for AI Systems (CCDS25-0582)," Final Year Project Report, College of Computing and Data Science, Nanyang Technological University, 2026.
```
