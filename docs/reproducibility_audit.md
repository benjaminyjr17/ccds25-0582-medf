# Reproducibility Audit

## Scope

This audit captures controls and commands required to reproduce MEDF outputs for FYP defense.

## Determinism Controls

- Pareto endpoint deterministic mode: `deterministic_mode=true` with explicit `seed` (`app/routers/pareto.py`).
- Stable stakeholder defaults are seeded at startup (`app/framework_registry.py`).
- Unified dimension order is fixed in `UNIFIED_DIMENSIONS` (`app/models.py`).
- API surface and OpenAPI fingerprint are frozen by tests (`tests/test_api_contract_lock.py`).

## Reproducible Command Set

```bash
./.venv/bin/python -m pytest -q --strict-markers
bash scripts/release_smoke.sh
./.venv/bin/python scripts/generate_evidence_pack.py
./.venv/bin/python scripts/run_research_statistics.py --seed 42 --n-boot 2000
```

## Replay Evidence

- Backend audit records: `data/audit_logs/audit.jsonl` (runtime artifact, ignored by git).
- UI run records and exported bundles: `data/ui_runs/*` and Streamlit bundle ZIP export.
- Deterministic repeatability checks: `tests/test_api_pareto.py`, `tests/test_release_candidate_stress.py`.
- Research statistics outputs: `docs/research/statistical_results.json`, `docs/research/statistical_summary.md`.

## Known Sources of Variation

- Runtime performance timings vary by host hardware and system load.
- Pareto runtime in high-load mode can vary while returning deterministic content for fixed seed/settings.

## Auditor Checklist

- `pytest` status: all tests pass.
- API contract lock and schema hash pass at the current freeze baseline.
- Smoke runner returns `RESULT: PASS`.
- Evidence pack files are generated under `docs/evidence/` with expected case/framework coverage.
- Research statistics runner generates committed outputs from `research/data/raw/*`.
