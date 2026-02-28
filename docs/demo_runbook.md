# Demo Runbook (Examiner-Facing)

## Pre-Flight

1. Activate environment.
2. Start backend and verify `/api/health` returns 200.
3. Start Streamlit app.

Commands:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
python -m streamlit run streamlit_app.py
```

## Demo Flow (Deterministic)

1. Enable `Conference Mode` in sidebar.
2. Select framework (start with `eu_altai`).
3. Page: `Evaluate`
- Select stakeholder: `Developer`.
- Scoring method: `topsis`.
- Keep default weights and default case profile.
- Run evaluation and show overall score + radar.
4. Page: `Conflict Detection`
- Stakeholders: Developer, Regulator, Affected Community.
- Run conflict detection and show pairwise matrix.
5. Page: `Pareto Resolution`
- Stakeholders: all three.
- Preset: Standard.
- Generate Pareto solutions and show tradeoff chart.
6. Page: `Case Studies`
- Run each case once.
- Show Evaluate -> Conflicts -> Pareto outputs.

## Evidence Capture

- Use `Export Full Analysis Bundle (ZIP)` after each run set.
- Save screenshots for:
  - Overall KPI strip
  - Evaluate radar
  - Conflict heatmap
  - Pareto scatter and parcoords
  - Case study output sections

## Failure Handling

- If backend request fails, open `API error details` expander and capture payload.
- If framework/stakeholder list is empty, verify backend URL and server status.
- If Pareto runtime is long, use `Standard` preset and retry.
