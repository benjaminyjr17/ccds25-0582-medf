# MEDF — Multi-stakeholder Ethical Decision Framework for AI Systems

> NTU Final Year Project CCDS25-0582
> `v1.1.0-freeze` baseline with post-freeze repository cleanup for deployment readiness

## Overview
MEDF is a decision-support platform for evaluating AI applications against policy and governance frameworks in a consistent, auditable workflow. It integrates the EU AI Act ALTAI, NIST AI RMF, and Singapore MGAF into a unified evaluation pipeline that produces framework-level and dimension-level outputs across six ethical dimensions: transparency and explainability, accountability, fairness and non-discrimination, safety and robustness, privacy and data governance, and human agency and oversight.

The platform includes:

- A FastAPI backend for evaluation, conflict analysis, Pareto resolution, framework loading, and stakeholder APIs.
- A Streamlit frontend for analyst-facing interaction and visual review.
- Three embedded case studies with assumptions and evidence-manifest metadata.
- Audit logging, evidence-pack generation, and a reproducible research statistics pipeline.

## Historical Note
The repository preserves the `v1.1.0-freeze` milestone documented in [FREEZE.md](FREEZE.md) as a historical baseline dated March 2, 2026. Subsequent commits after that freeze are limited to repository hygiene, deployment-readiness cleanup, and documentation/configuration alignment, and are not intended to change MEDF core scoring logic, API contracts, or workflow behavior.

## Architecture
MEDF uses a three-tier architecture:

1. FastAPI backend in `app/` for evaluation logic, validation, optimization, and API contracts.
2. Streamlit frontend in `streamlit_app.py` for analyst-facing interaction and visual review.
3. Shared data layer in `case_studies/`, `data/`, `research/`, and `app/frameworks/` for scenario inputs, runtime outputs, framework definitions, and reproducibility assets.

Core routers are implemented in `app/routers/` and exposed as `evaluate`, `conflicts`, `pareto`, `frameworks`, and `stakeholders` endpoints. The canonical architecture diagram is available at [docs/architecture/system_architecture.svg](docs/architecture/system_architecture.svg).

## Local Development
Use the following commands from the repository root:

```bash
git clone https://github.com/<user>/ccds25-0582-medf.git
cd ccds25-0582-medf
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the backend:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend startup automatically initializes the database, framework registry, and default stakeholders.

In a separate terminal, start the Streamlit frontend:

```bash
source .venv/bin/activate
python -m streamlit run streamlit_app.py
```

For local development, the Streamlit sidebar defaults the backend URL to `http://127.0.0.1:8000`, which matches the local FastAPI server above.

### Makefile Shortcuts
For local development, the provided `Makefile` wraps the most common commands.
Use `make dev` to start the FastAPI backend and Streamlit frontend together in one terminal session.
Use `make test` to run the test suite, and `make doctor` to perform a quick environment health check before troubleshooting.

```bash
make dev
```

### Docker Compose
If you prefer containerized development, `docker-compose up --build` starts both services in Docker.
The FastAPI backend is exposed on port `8000`, and the Streamlit frontend is exposed on port `8501`.
This mirrors the split local stack without requiring a local virtual environment.

```bash
docker-compose up --build
```

## Deployed Split-Stack Configuration
Preserve the local development workflow above, but treat deployment as a split stack: the Streamlit frontend requires a separately reachable FastAPI backend.

The Streamlit `Backend URL` field is prefilled in this order:

1. `backend_url` from `.streamlit/secrets.toml`
2. `MEDF_BACKEND_URL`
3. `http://127.0.0.1:8000`

These settings only prefill the editable UI field. They do not provision, start, or proxy the backend service.

For deployed Streamlit:

- Point `backend_url` or `MEDF_BACKEND_URL` at the deployed FastAPI service.
- Keep the backend reachable from the deployed Streamlit environment.
- Use [.env.example](.env.example) only as a truthful variable reference, not as evidence of automatic dotenv loading.

## Testing
Run the full local suite:

```bash
python -m pytest
```

Run the fast CI-equivalent gate:

```bash
python -m pytest -q --strict-markers -m "not extreme and not property and not soak"
```

Run the heavy marker gate:

```bash
MEDF_EXTREME=1 python -m pytest -q --strict-markers -m "extreme or property or soak"
```

Run the freeze-level smoke and coverage gate:

```bash
bash scripts/freeze_extreme_gate.sh
bash scripts/release_smoke.sh
```

The repository includes unit, integration, property-based, stress, and end-to-end tests, with CI gates for strict marker validation and freeze-level coverage checks.

## Project Structure
```text
ccds25-0582-medf/
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── extreme-tests.yml
├── .streamlit/
│   └── config.toml
├── app/
│   ├── frameworks/
│   ├── routers/
│   ├── main.py
│   ├── models.py
│   ├── scoring_engine.py
│   ├── harm_assessment.py
│   ├── framework_registry.py
│   └── database.py
├── case_studies/
├── data/
│   ├── audit_logs/
│   └── ui_runs/
├── docs/
│   ├── architecture/
│   │   ├── system_architecture.mmd
│   │   └── system_architecture.svg
│   ├── evidence/
│   ├── research/
│   └── *.md
├── research/
│   └── data/
│       └── raw/
├── scripts/
│   ├── doctor_env.sh
│   ├── freeze_extreme_gate.sh
│   ├── generate_evidence_pack.py
│   ├── release_smoke.sh
│   └── run_research_statistics.py
├── tests/
├── thesis/
├── .env.example
├── plot_theme.py
├── streamlit_app.py
├── README.md
├── FREEZE.md
├── requirements.txt
└── pytest.ini
```

## Research Data
Raw study data is stored under `research/data/raw/` as six CSV datasets used by the statistical validation pipeline: Friedman repeated scores, Wilcoxon paired scores, Cliff’s delta groups, Krippendorff annotations, SUS responses, and CVI expert ratings. Consolidated analysis outputs and interpretation are documented in [docs/research/statistical_summary.md](docs/research/statistical_summary.md).

## Documentation
- `docs/architecture_description.md`: system architecture narrative and component responsibilities.
- `docs/assumptions.md`: operational assumptions, scope assumptions, and modeling constraints.
- `docs/data_model_spec.md`: schema details for core entities and request/response payloads.
- `docs/design_decisions.md`: engineering decision log and rationale for key trade-offs.
- `docs/demo_runbook.md`: reproducible steps for live demonstration and validation.
- `docs/evaluation_results.md`: benchmark and case-study evaluation outcomes.
- `docs/regulatory_traceability.md`: mapping from framework clauses to implementation artifacts.
- `docs/reproducibility_audit.md`: reproducibility controls, CI gate design, and audit evidence.
- `docs/requirements_traceability.md`: traceability matrix linking requirements to implementation and tests.

## License
This project is released under the terms in [LICENSE](LICENSE).

## Citation
```text
Yick, B. O. (2026). Multi-stakeholder Ethical Decision Framework for AI Systems.
NTU Final Year Project CCDS25-0582. Nanyang Technological University.
```
