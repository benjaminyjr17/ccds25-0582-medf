# MEDF: Multi-stakeholder Ethical Decision Framework for AI Systems
**NTU CCDS Final Year Project (CCDS25-0582).**
Author: Benjamin Oliver Yick.
Supervisor: Dr. Zhang Jiehuang.
Engineering freeze tag: `fyp-freeze-v1.0.0`.

---

## Project Description

The Multi-Stakeholder Ethical Decision Framework (MEDF) is an academic evaluation platform for AI governance analysis across multiple ethical frameworks and stakeholder perspectives. The frozen release includes multi-framework scoring, conflict detection, Pareto-based consensus optimization with NSGA-II, deterministic mode for reproducibility, an institutional-grade Streamlit interface, audit logging for traceability, and release smoke and stress validation for stability assurance.

## System Capabilities

- Multi-framework evaluation.
- Stakeholder weight validation and normalization.
- Salience-weighted conflict detection.
- Multi-objective Pareto optimization.
- Deterministic reproducibility.
- Institutional presentation mode (Conference Mode).
- Stress-tested performance under high-load parameters.
- Complete pytest validation suite.

## Architecture Overview

- Streamlit UI layer for institutional analytics presentation and governance review workflows.
- FastAPI orchestration layer for request validation, routing, and response serialization.
- Scoring engine for MCDA-based evaluation using TOPSIS, WSM, and AHP-supported workflows.
- Conflict engine for stakeholder disagreement quantification using salience-weighted ranking analysis.
- Pareto engine for NSGA-II consensus weight search with deterministic execution controls.
- Framework YAML registry for harmonized ethical dimension mapping and framework metadata loading.
- SQLite stakeholder store for default profiles and persisted stakeholder configuration state.
- Audit log for endpoint-level request and response traceability.

## Methodological Foundation

This project follows Design Science Research (Peffers et al., 2007).

- Problem Identification.
- Objective Definition.
- Design and Development.
- Demonstration with case studies.
- Evaluation with expert validation, usability testing, and ablation analysis.
- Communication.

Validation includes the following statistical and methodological checks.

- Content Validity Index (I-CVI, S-CVI/Ave).
- Krippendorff’s Alpha with bootstrapped confidence intervals.
- System Usability Scale (SUS).
- Wilcoxon signed-rank test.
- Friedman test.
- Cliff’s Delta effect size.

## Installation

### Step 1: Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Running Backend

Use the backend command below.

```bash
uvicorn app.main:app --reload --port 8000
```

Backend documentation endpoint.

```text
http://localhost:8000/api/docs
```

## Running Frontend

Use the dashboard command below.

```bash
streamlit run dashboard/app.py
```

Institutional interface entry point used in the freeze release.

```bash
python -m streamlit run streamlit_app.py
```

## API Endpoints

- `GET /api/health` for service status checks.
- `GET /api/frameworks` for framework registry listing.
- `GET /api/frameworks/{framework_id}` for framework detail retrieval.
- `GET /api/stakeholders` for stakeholder profile listing.
- `POST /api/stakeholders` for stakeholder profile creation.
- `POST /api/evaluate` for multi-framework ethical scoring.
- `POST /api/conflicts` for stakeholder conflict analysis.
- `POST /api/pareto` for Pareto-based consensus optimization.

## Testing Instructions

Run the complete test suite.

```bash
pytest -q
```

Run release smoke and stress validation.

```bash
bash scripts/release_smoke.sh
```

## Determinism and Validation

- Seed control is exposed through Pareto request parameters.
- Deterministic mode enforces repeatable optimization behavior when enabled.
- Stress validation is executed with high-load settings (`n_solutions=50`, `pop_size=256`, `n_gen=300`).
- Reproducibility guarantees are validated through repeated deterministic runs and invariant checks.

## Engineering Freeze State

- Tag name: `fyp-freeze-v1.0.0`.
- Test status: complete pytest suite passing at freeze time.
- Smoke validation status: release smoke and stress runner passing.
- Freeze policy: post-tag changes are limited to critical defect remediation under a new tag.

## Case Studies

- Facial Recognition for Law Enforcement.
- Hiring Recommendation Algorithm.
- Healthcare Diagnostic AI.

## Limitations

- The platform targets academic research and evaluation, not production hardening.
- Authentication and access control are not implemented in this release.
- Deployment guidance is centered on localhost execution.
- Maximum-parameter Pareto runs can require multiple seconds.
- Framework normative priors are not directly embedded in the Pareto objective function.

## Repository Description (Short Version)

Cross-framework ethical AI assessment platform with stakeholder-weighted MCDA scoring, salience-weighted conflict detection, Pareto tradeoff analysis with NSGA-II, deterministic reproducibility controls, and institutional governance-oriented presentation support.
