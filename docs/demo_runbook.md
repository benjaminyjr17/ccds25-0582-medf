# Demo Runbook (Deterministic, Examiner-Facing)

## Preconditions

- Python environment is available at `.venv`.
- Backend API is reachable at `http://localhost:8000`.
- Case studies exist under `case_studies/*.json`.

## Start Services

Open terminal A:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Open terminal B:

```bash
source .venv/bin/activate
python -m streamlit run streamlit_app.py
```

## Deterministic Demo Sequence

1. In Streamlit sidebar, set:
- Framework: `eu_altai`
- Stakeholders: `developer`, `regulator`, `affected_community`
- Conference Mode: `ON`
2. Navigate pages in this order:
- `Evaluate`
- `Conflict Detection`
- `Pareto Resolution`
- `Case Studies`

## Page Steps and Expected Outputs

### Evaluate

1. Use the default demo profile and scoring method `topsis`.
2. Run evaluation once.

Expected output:
- A non-empty overall score/KPI summary.
- Dimension-level visual(s) rendered (radar/score chart).
- No API errors shown.

### Conflict Detection

1. Keep the same framework and stakeholder set.
2. Run conflict analysis once.

Expected output:
- Pairwise stakeholder conflict entries appear.
- Spearman-based disagreement metrics are shown.
- At least one matrix/heatmap-style visualization is rendered.

### Pareto Resolution

1. Keep all three stakeholders selected.
2. Use preset `Standard` and run once.

Expected output:
- Non-empty Pareto solution set.
- Tradeoff visualization(s) render (scatter and/or parallel coordinates).
- Selected solution details are shown with valid weight vectors.

### Case Studies

1. Confirm all three cases are listed (file-driven from `case_studies/*.json`).
2. For each case, click `Run Case Study` once.

Expected output:
- Each case produces Evaluate -> Conflict -> Pareto outputs.
- Case details display includes source reference and assumptions.
- No missing-case loader error is shown.

## Export Evidence Bundle

1. Use `Export Full Analysis Bundle (ZIP)` from the UI.
2. Save the ZIP artifact for defense evidence.

Expected output:
- Download succeeds.
- ZIP contains run metadata and generated analysis artifacts.

## Failure Handling

- If UI cannot fetch API data, check `http://localhost:8000/api/health`.
- If case studies do not appear, verify JSON files in `case_studies/` and restart Streamlit.
- If Pareto run takes longer than expected, keep `Standard` preset and rerun once.

## Optional Reproducibility Gate (Pre-Demo)

```bash
./.venv/bin/python -m pytest -q --strict-markers
bash scripts/release_smoke.sh
```
