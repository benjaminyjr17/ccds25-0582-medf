# MEDF — Multi-stakeholder Ethical Decision Framework for AI Systems

> NTU Final Year Project CCDS25-0582  
> v1.1.0-freeze · Feature-frozen reproducible artifact

## Overview
MEDF is a decision-support platform for evaluating AI applications against policy and governance frameworks in a consistent, auditable workflow. It integrates the EU AI Act ALTAI, NIST AI RMF, and Singapore MGAF into a unified evaluation pipeline that produces framework-level and dimension-level outputs. The system operationalizes governance requirements into quantifiable, comparable scores on a 1–7 Likert scale over six ethical dimensions: transparency and explainability, accountability, fairness and non-discrimination, safety and robustness, privacy and data governance, and human agency and oversight. MEDF also surfaces multi-stakeholder disagreement and produces Pareto-optimal consensus recommendations for trade-off analysis.

## Key Features
MEDF supports three regulatory frameworks and computes dimension-level plus aggregate ethical scores for each AI system under analysis. The evaluation flow is deterministic under fixed seeds and captures the full scoring context required for reproducible review.

Conflict analysis compares stakeholder priorities through pairwise alignment metrics and structured disagreement summaries. This allows evaluators to trace where decision tensions arise and which dimensions drive divergence.

Pareto resolution is implemented as a multi-objective optimization problem using NSGA-II, producing candidate consensus weight vectors and objective surfaces that remain inspectable through API responses and dashboard analytics.

The repository includes three embedded case studies: Metropolitan Police live facial recognition, iTutorGroup automated hiring screening, and Royal Free NHS–DeepMind Streams deployment. Each case includes assumptions, evidence manifest metadata, and runnable scenario payloads.

The Streamlit interface provides configurable stakeholder weights, scoring and search controls, presets, conference presentation mode, and screenshot mode for report-grade figures. The backend records audit logs and supports evidence-pack generation for traceability.

The research pipeline includes statistical analysis assets for Friedman, Wilcoxon, Cliff’s delta, Krippendorff’s alpha, SUS, and CVI, supporting the empirical sections of the FYP report.

## Architecture
MEDF uses a three-tier architecture:

1. FastAPI backend in `app/` for evaluation logic, validation, optimization, and API contracts.
2. Streamlit frontend in `streamlit_app.py` for analyst-facing interaction and visual review.
3. Shared data layer in `case_studies/`, `data/`, and `app/frameworks/` for scenario inputs, runtime outputs, and framework definitions.

Core routers are implemented in `app/routers/` and exposed as `evaluate`, `conflicts`, `pareto`, `frameworks`, and `stakeholders` endpoints. The canonical architecture diagram is available at [docs/architecture/system_architecture.svg](docs/architecture/system_architecture.svg).
Conflict analysis is implemented in `app/routers/conflicts.py` in the current codebase.

## Quick Start
```bash
# Clone and set up
git clone https://github.com/<user>/ccds25-0582-medf.git
cd ccds25-0582-medf
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed the database and start the API server
python scripts/seed_db.py
uvicorn app.main:app --reload

# In a separate terminal, launch the Streamlit dashboard
streamlit run streamlit_app.py
```

## Testing
```bash
# Run the full test suite
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=term-missing
```

The repository maintains 54+ tests spanning unit, integration, property-based, stress, and end-to-end categories, with CI gates for strict marker validation and freeze-level coverage checks.

## Reproducibility and CI Gates
MEDF uses a two-tier CI strategy to balance development velocity with freeze-level rigor. The fast gate runs on every push and pull request, while the heavy gate runs on nightly schedule and manual dispatch for extended stress and property-based validation.

```bash
# Fast CI-equivalent gate
python -m pytest -q --strict-markers -m "not extreme and not property and not soak"

# Heavy marker gate
MEDF_EXTREME=1 python -m pytest -q --strict-markers -m "extreme or property or soak"

# Freeze gate (coverage + module thresholds + smoke checks)
bash scripts/freeze_extreme_gate.sh
```

Coverage policy enforces both a global threshold and module-level minimums for core implementation files, including `app/routers/evaluate.py`, `app/routers/conflicts.py`, `app/routers/pareto.py`, `app/scoring_engine.py`, and `app/framework_registry.py`. This ensures the project can be revalidated as a reproducible artifact instead of a best-effort prototype.

## Project Structure
```text
ccds25-0582-medf/
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── extreme-tests.yml
├── app/
│   ├── frameworks/
│   ├── routers/
│   │   ├── evaluate.py
│   │   ├── conflicts.py
│   │   ├── pareto.py
│   │   ├── frameworks.py
│   │   └── stakeholders.py
│   ├── main.py
│   ├── models.py
│   ├── scoring_engine.py
│   ├── harm_assessment.py
│   ├── framework_registry.py
│   └── database.py
├── case_studies/
│   ├── facial_recognition.json
│   ├── hiring_algorithm.json
│   └── healthcare_diagnostic.json
├── data/
│   ├── audit_logs/
│   │   └── .gitkeep
│   └── ui_runs/
│       └── .gitkeep
├── docs/
│   ├── architecture/
│   │   └── system_architecture.svg
│   ├── evidence/
│   ├── research/
│   └── *.md
├── research/
│   └── data/
│       └── raw/
├── scripts/
│   ├── release_smoke.sh
│   ├── freeze_extreme_gate.sh
│   └── seed_db.py
├── tests/
├── plot_theme.py
├── streamlit_app.py
├── README.md
├── FREEZE.md
├── requirements.txt
└── pytest.ini
```

## Research Data
Raw study data is stored under `research/data/raw/` as six CSV datasets used by the project’s statistical validation pipeline: Friedman repeated scores, Wilcoxon paired scores, Cliff’s delta groups, Krippendorff annotations, SUS responses, and CVI expert ratings. Consolidated analysis outputs and interpretation are documented in [docs/research/statistical_summary.md](docs/research/statistical_summary.md).

## Documentation
- `docs/architecture_description.md`: system architecture narrative and component responsibilities.
- `docs/assumptions.md`: operational assumptions, scope assumptions, and modeling constraints.
- `docs/data_model_spec.md`: schema details for core entities and request/response payloads.
- `docs/design_decisions.md`: engineering decision log and rationale for key trade-offs.
- `docs/evaluation_results.md`: benchmark and case-study evaluation outcomes.
- `docs/demo_runbook.md`: reproducible steps for live demonstration and validation.
- `docs/scope_boundary.md`: explicit in-scope and out-of-scope boundaries.
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
