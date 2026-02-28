# Engineering Freeze Notice — FYP Release

## Tag Information

- Tag name: v1.0.1-freeze.
- Commit SHA: 96b6a4b94b876bd8b96744688d96cf6708b40d19.
- Freeze date: 2026-02-28.
- Freeze rationale: presentation/provenance/UI rendering cleanup; no API or computation changes.

This tag represents the finalized engineering state of the Multi-Stakeholder Ethical Decision Framework (MEDF) platform submitted for academic evaluation.

## Scope of Implementation

The frozen release includes the following components.

- A FastAPI backend supporting multi-framework ethical evaluation, stakeholder conflict detection, and Pareto-based consensus optimization.
- A unified ethical dimension space derived from registered framework definitions.
- Strict stakeholder weight validation with normalization and constraint enforcement.
- Deterministic mode enabling reproducible Pareto optimization runs.
- NSGA-II multi-objective optimization for consensus weight generation.
- Conflict detection using pairwise stakeholder ranking agreement metrics.
- Comprehensive audit logging of API requests and responses for traceability.
- An institutional-grade Streamlit interface with structured KPI strip and governance-oriented layout.
- A visibility-only Conference Mode for presentation contexts.
- UI contract assertions ensuring presentation-layer integrity without altering backend logic.
- A complete pytest suite with all tests passing at freeze time.
- A release smoke and stress runner validating backend stability and UI robustness under high-load configurations.

## Execution Instructions (Local Environment)

### Backend Execution

- Navigate to the project root directory.
- Activate the virtual environment using source .venv/bin/activate.
- Start the backend with python -m uvicorn app.main:app --reload --port 8000.

### Frontend Execution

- Activate the virtual environment using source .venv/bin/activate.
- Launch the dashboard with python -m streamlit run streamlit_app.py.

## Release Smoke and Stress Validation

To execute the full pre-freeze validation suite.

- Run bash scripts/release_smoke.sh.

This script performs the following.

- Full syntax compilation checks.
- Complete pytest execution.
- Deterministic API stress testing.
- High-parameter Pareto evaluation.
- Headless Streamlit smoke validation.
- Verification of clean repository state.

## Determinism and Stress Profile

The system has been validated under the following stress parameters.

- Pareto optimization with n_solutions=50.
- Pareto optimization with pop_size=256.
- Pareto optimization with n_gen=300.
- Deterministic mode enabled with fixed seed values.
- Stable performance observed across repeated runs.
- No flaky behavior detected.

All optimization outputs remain reproducible when deterministic mode is enabled.

## Methodological Clarifications

- Pareto consensus weights are solver-derived compromise weight vectors.
- Consensus weights are simplex-normalized and non-negative.
- Optimization minimizes salience-weighted distance to stakeholder weight vectors.
- Framework selection defines the ethical dimension semantics and evaluation context.
- Framework priors do not directly constrain Pareto optimization in this release.
- Consensus weights represent stakeholder tradeoff balancing rather than framework-imposed weighting.

## Known Limitations

- The platform is designed for research and evaluation purposes and is not production-hardened.
- No authentication or access-control layer is implemented.
- Deployment configuration targets localhost execution.
- Pareto optimization may require several seconds under maximum parameter settings.
- Framework normative priors are not embedded directly into the Pareto objective function.

## Freeze Policy

- No further feature changes are permitted after this tag.
- Only critical defect fixes are allowed.
- Any post-freeze fixes require a new tag such as v1.0.2-freeze.
- The freeze state reflects the validated configuration presented for academic assessment.
