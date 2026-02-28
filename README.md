# MEDF: Multi-stakeholder Ethical Decision Framework for AI Systems
**NTU CCDS Final Year Project (CCDS25-0582).**
Author: Benjamin Oliver Yick.
Supervisor: Dr. Zhang Jiehuang.
Engineering freeze tag: `fyp-freeze-v1.0.0`.
Historical: fyp-freeze-v1.0.0 (superseded by v1.0.1-freeze).

---

## Executive Summary

The Multi-Stakeholder Ethical Decision Framework (MEDF) is a methodological and computational framework for governance-oriented evaluation of AI systems. It addresses a core governance problem: ethical assessment practices that treat framework selection and stakeholder perspective as fixed inputs rather than contested variables. MEDF introduces an integrated approach that combines multi-framework evaluation, stakeholder conflict modeling, and Pareto-based consensus optimization under deterministic controls. Operationally, the system provides API-driven analysis, institutional Streamlit presentation workflows, audit traceability, and repeatable validation procedures suitable for regulatory, policy, and academic review.

## Governance Context

- Multi-framework evaluation enables the same AI system to be assessed under distinct normative structures without collapsing framework semantics into a single score model.
- Stakeholder conflict modeling identifies disagreement patterns across developer, regulator, and affected-community preference vectors.
- Pre-deployment risk identification is supported through comparative scoring, conflict intensity analysis, and consensus tradeoff diagnostics before operational rollout.
- Regulatory applicability is aligned with evidence-oriented governance workflows, including auditable computations, reproducibility controls, and stable endpoint contracts.

## System Capabilities

- Multi-framework evaluation.
- Stakeholder weight validation and normalization.
- Salience-weighted conflict detection.
- Multi-objective Pareto optimization.
- Deterministic reproducibility.
- Institutional presentation mode (Conference Mode).
- Stress-tested performance under high-load parameters.
- Complete pytest validation suite.

## Formal Methodology

### Optimization Objective

The consensus optimization objective is expressed as follows.

```text
minimize sum_i s_i |w_i - w_k|.
```

- `s_i` denotes stakeholder salience coefficients.
- `w_i` denotes stakeholder-specific weight components.
- `w_k` denotes candidate consensus weight components across the unified dimension space.
- The objective minimizes salience-weighted absolute deviation between stakeholder preferences and candidate consensus vectors.

### Salience, Constraints, and Frontier Construction

- Salience vectors are constructed from stakeholder participation and weighting context so that stakeholder influence is explicitly represented during conflict and optimization analysis.
- Stakeholder weight validation enforces numeric inputs, complete unified-dimension coverage, bounded values, and near-unit sum constraints.
- Simplex normalization is applied so accepted weight vectors are non-negative and sum to 1.0 within model tolerance.
- Pareto frontier generation is performed with NSGA-II and non-dominated filtering over stakeholder objective scores.
- Deterministic seed control is exposed through request parameters and deterministic mode flags for repeatable optimization behavior.
- Ablation utility recording is retained through evaluation study procedures and stress-test artifacts to isolate the contribution of modeling components.

## System Architecture

- Streamlit presentation layer for governance-facing visualization and review workflows.
- FastAPI orchestration layer for validation, routing, and response serialization.
- Scoring engine implementing TOPSIS and WSM pathways with AHP-supported weighting workflows.
- Conflict engine implementing salience-weighted stakeholder disagreement analysis.
- Pareto optimization engine implementing NSGA-II consensus search.
- Framework YAML registry for framework metadata and unified-dimension mappings.
- SQLite stakeholder store for persisted stakeholder profiles and defaults.
- Audit logging layer for request-response traceability.
- Separation of concerns is maintained by isolating presentation, orchestration, scoring, conflict, optimization, registry, and persistence responsibilities.

## Validation and Robustness

- Complete pytest validation suite execution at freeze time.
- Deterministic stress testing with repeated endpoint calls.
- High-limit Pareto configuration validation (`n_solutions=50`, `pop_size=256`, `n_gen=300`).
- Smoke test runner execution through `scripts/release_smoke.sh`.
- Reproducibility guarantees verified through repeated deterministic runs and invariant checks.

## Determinism and Reproducibility

- Seed control is provided through Pareto request parameters.
- Deterministic mode enforces repeatable optimization behavior when enabled.
- Non-flaky test behavior was observed during release validation runs.
- Stress-run verification was conducted under repeated deterministic configurations.

## Engineering Freeze and Governance Stability

- Freeze tag: `fyp-freeze-v1.0.0`.
- Historical: fyp-freeze-v1.0.0 (superseded by v1.0.1-freeze).
- Repository state at freeze validation: clean and traceable.
- Feature development policy: no post-freeze feature additions.
- Hotfix policy: only critical defect remediation under a new release tag.
- Scope boundaries: freeze constraints apply to API surface, scoring pathways, conflict logic, optimization behavior, and governance UI contracts.

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

## Backend Execution

Use the backend command below.

```bash
uvicorn app.main:app --reload --port 8000
```

Backend documentation endpoint.

```text
http://localhost:8000/api/docs
```

## Frontend Execution

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

## Case Studies

- Facial Recognition for Law Enforcement.
- Hiring Recommendation Algorithm.
- Healthcare Diagnostic AI.

## Requirements Traceability

- Canonical requirement ledger: `docs/requirements_traceability.md`.
- Regulatory mapping annex: `docs/regulatory_traceability.md`.
- Reproducibility audit: `docs/reproducibility_audit.md`.

## Limitations and Scope Boundaries

- No authentication or authorization layer is implemented in this release.
- Execution guidance targets localhost deployment configurations.
- Framework normative priors are not directly embedded in the Pareto objective function.
- The platform remains a research-grade prototype for evaluation and policy analysis workflows.
- High-load Pareto configurations can require multi-second execution time.

## Repository Description (Short Version)

Cross-framework ethical AI assessment platform with stakeholder-weighted MCDA scoring, salience-weighted conflict detection, Pareto tradeoff analysis with NSGA-II, deterministic reproducibility controls, and institutional governance-oriented presentation support.
