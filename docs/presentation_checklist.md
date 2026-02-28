# Presentation Checklist

## Technical Gate

- [ ] `pytest -q --strict-markers` passes.
- [ ] `bash scripts/release_smoke.sh` returns `RESULT: PASS`.
- [ ] API docs reachable at `/api/docs`.

## Slides / Figures

- [ ] System architecture figure from `docs/architecture/system_architecture.svg`.
- [ ] Evaluate radar chart screenshot.
- [ ] Conflict heatmap screenshot.
- [ ] Pareto tradeoff visual screenshot.
- [ ] Case studies page screenshots for all three scenarios.

## Tables

- [ ] Requirements traceability table (from `docs/requirements_traceability.md`).
- [ ] Regulatory mapping table (from `docs/regulatory_traceability.md`).
- [ ] Result summary table (from `docs/evidence/evaluation_summary.csv`).
- [ ] Freeze checklist table with YES/NO results.

## Narrative Sequence

- [ ] Problem and requirement baseline.
- [ ] Architecture and implementation.
- [ ] Determinism and QA evidence.
- [ ] Empirical case-study outputs.
- [ ] Scope limits and future work.

## Artifacts to Bring

- [ ] Latest analysis bundle ZIP.
- [ ] `docs/evidence/evaluation_bundle.json`.
- [ ] `docs/evidence/evaluation_summary.csv`.
- [ ] `FREEZE.md` and contract-lock test reference.
