# Engineering Freeze Notice — FYP Release Line

## Active Freeze Successor (Post-Remediation)

- Target tag name: `v1.1.0-freeze`.
- Baseline commit SHA for freeze preparation: `e274fc7146f1de1db4c46c8490479dcf1d0454d1`.
- Freeze preparation date: `2026-03-02`.
- Freeze rationale: strict requirement remediation for RQ-03 (typed harm output), RQ-05 (real-deployment provenance manifests), and RQ-06 (committed raw-data-to-results statistics runner).

This release line supersedes prior freeze constraints that prohibited feature additions in `v1.0.1-freeze`.

## Historical Freeze Record

- Prior tag name: `v1.0.1-freeze`.
- Prior commit SHA: `96b6a4b94b876bd8b96744688d96cf6708b40d19`.
- Prior freeze date: `2026-02-28`.

## Scope of the v1.1.0 Successor

- FastAPI backend with evaluation, conflict, and Pareto workflows.
- Typed harm-taxonomy output in `/api/conflicts`.
- Real-deployment case-study manifests with licensing-safe provenance policy.
- Deterministic research statistics pipeline from committed raw CSV inputs.
- Streamlit evidence rendering that surfaces deployment manifest and per-dimension rationale.
- Contract-lock and OpenAPI fingerprint updated to the new freeze baseline.

## Execution Instructions (Local)

### Backend

- Activate environment: `source .venv/bin/activate`
- Start backend: `python -m uvicorn app.main:app --reload --port 8000`

### Frontend

- Activate environment: `source .venv/bin/activate`
- Start interface: `python -m streamlit run streamlit_app.py`

## Reproducibility Commands

```bash
./.venv/bin/python -m pytest -q --strict-markers
bash scripts/release_smoke.sh
./.venv/bin/python scripts/generate_evidence_pack.py
./.venv/bin/python scripts/run_research_statistics.py --seed 42 --n-boot 2000
```

## Freeze Policy

- API path/schema changes are permitted only with version bump and updated lock hash.
- `v1.1.0-freeze` becomes the governing baseline after tag creation.
- Post-`v1.1.0-freeze` changes are limited to critical defect fixes under a new tag.
