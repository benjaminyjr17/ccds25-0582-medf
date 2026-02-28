# Presentation Checklist

This checklist aligns with `docs/evidence_index.md` screenshot IDs and closeout traceability artifacts.

## Live Technical Gate

- [ ] `./.venv/bin/python -m pytest -q --strict-markers` passes.
- [ ] `bash scripts/release_smoke.sh` returns `RESULT: PASS`.
- [ ] API docs reachable at `/api/docs`.

## Screenshot List (Aligned IDs)

- [ ] `SS-01` Evaluate page overall score + dimension visualization.
- [ ] `SS-02` Stakeholder selection and profile context in UI.
- [ ] `SS-03` Conflict matrix/heatmap with pairwise stakeholder metrics.
- [ ] `SS-04` Framework/regulatory mapping evidence (`/api/frameworks` + `docs/regulatory_traceability.md`).
- [ ] `SS-05` Case Studies page outputs for all three scenarios.
- [ ] `SS-06` Reproducibility evidence (`docs/evidence/evaluation_summary.csv`, smoke PASS summary).
- [ ] `SS-07` Freeze evidence (`FREEZE.md` + API contract lock test reference).

## Evidence Artifacts to Bring

- [ ] `docs/requirements_traceability.md`
- [ ] `docs/evidence_index.md`
- [ ] `docs/regulatory_traceability.md`
- [ ] `docs/evaluation_results.md`
- [ ] `docs/evidence/evaluation_bundle.json`
- [ ] `docs/evidence/evaluation_summary.csv`
- [ ] `FREEZE.md`

## Backup Plan (If Live Demo Fails)

- [ ] Use latest exported analysis ZIP from UI bundle export.
- [ ] Use static evidence artifacts in `docs/evidence/` and walk through SS-01..SS-07 sequence.
- [ ] Re-run health check `curl -s http://localhost:8000/api/health` and continue with evidence-only narration if service startup fails.
- [ ] Keep a pre-recorded local walkthrough available (maintainer-provided) and reference the same screenshot IDs and artifacts.
