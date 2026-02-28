# Evidence Index (Examiner Navigation)

This index maps requirement IDs from `docs/requirements_traceability.md` to executable evidence and screenshot placeholders.

| RQ-ID | Evidence Artifact(s) | Reproduce Command(s) | Screenshot ID |
|---|---|---|---|
| RQ-01 | `app/routers/evaluate.py`, `tests/test_api_evaluate.py`, `tests/test_system_e2e_top_tier.py` | `./.venv/bin/python -m pytest -q tests/test_api_evaluate.py tests/test_system_e2e_top_tier.py` | SS-01 |
| RQ-02 | `app/routers/stakeholders.py`, `app/routers/conflicts.py`, `app/routers/pareto.py`, `tests/test_system_e2e_top_tier.py` | `./.venv/bin/python -m pytest -q tests/test_system_e2e_top_tier.py` | SS-02 |
| RQ-03 | `app/routers/conflicts.py`, `tests/test_api_conflicts.py`, `tests/test_release_candidate_invariants.py` | `./.venv/bin/python -m pytest -q tests/test_api_conflicts.py tests/test_release_candidate_invariants.py` | SS-03 |
| RQ-04 | `app/models.py`, `app/framework_registry.py`, `app/frameworks/eu_altai.yaml`, `app/frameworks/nist_ai_rmf.yaml`, `app/frameworks/sg_mgaf.yaml`, `docs/regulatory_traceability.md` | `./.venv/bin/python -m pytest -q tests/test_framework_registry.py` | SS-04 |
| RQ-05 | `case_studies/facial_recognition.json`, `case_studies/hiring_algorithm.json`, `case_studies/healthcare_diagnostic.json`, `streamlit_app.py`, `tests/test_case_studies_schema.py`, `scripts/generate_evidence_pack.py`, `docs/evaluation_results.md` | `./.venv/bin/python -m pytest -q tests/test_case_studies_schema.py && ./.venv/bin/python scripts/generate_evidence_pack.py` | SS-05 |
| RQ-06 | `implementation_log.md`, `docs/assumptions.md`, `docs/reproducibility_audit.md`, `docs/evaluation_results.md`, `docs/evidence/evaluation_summary.csv` | `./.venv/bin/python scripts/generate_evidence_pack.py && bash scripts/release_smoke.sh` | SS-06 |
| RQ-07 | `app/main.py`, `streamlit_app.py`, `.github/workflows/test.yml`, `tests/test_api_contract_lock.py`, `FREEZE.md` | `./.venv/bin/python -m pytest -q --strict-markers` | SS-07 |

## Screenshot Placeholder Guide

- `SS-01`: Evaluate page overall score and radar for one framework.
- `SS-02`: Stakeholder selection and loaded profiles in UI.
- `SS-03`: Conflict matrix/heatmap with pairwise disagreement summary.
- `SS-04`: Framework registry/API listing (`/api/frameworks`) and regulatory mapping table.
- `SS-05`: Case Studies page output and exported bundle evidence.
- `SS-06`: Reproducibility outputs (`evaluation_summary.csv`, smoke `PASS`).
- `SS-07`: API contract lock test and freeze metadata snapshot.
