# Release Candidate Stress Verification Report

- Date/time (UTC): 2026-02-25 10:28:14 UTC
- Repository: `/Users/benjaminoliveryick/ccds25-0582-medf`
- Final outcome: **PASS**

## Commands Executed
1. `./.venv/bin/python -m compileall app streamlit_app.py`
2. `./.venv/bin/pytest -q`
3. `for i in 1 2 3 4 5; do ./.venv/bin/pytest -q || exit 1; done`
4. `./.venv/bin/pytest -q tests/test_release_candidate_invariants.py tests/test_release_candidate_stress.py`
5. `./.venv/bin/python -m compileall app streamlit_app.py`
6. `./.venv/bin/pytest -q`
7. `for i in 1 2 3; do ./.venv/bin/pytest -q || exit 1; done`

## Scope and Coverage
- Frameworks tested: **3** (from `GET /api/frameworks`)
- Deterministic random pool: **30** vectors (`random.Random(1337)`)
- Per-framework vector execution:
  - Edge vectors: **5** (`all_min`, `all_max`, `alternating_min_max`, `midpoint`, `skewed_safety`)
  - Random vectors exercised: **10** (subset of the 30-vector pool)
- Presets exercised: **baseline**, **safety-heavy**, **flipped** (transparency-heavy)

## Invariants Verified
- No `NaN`/`inf` in JSON outputs (`/api/evaluate`, `/api/conflicts`, `/api/pareto`, and base GET endpoints)
- Weight vectors are non-negative and sum to 1
- Spearman rho bounds in conflicts are within `[-1, 1]`
- Evaluate normalized dimension scores remain in `[0, 1]` (tiny tolerance)
- Pareto returned set is non-dominated under the system objective convention (`minimize`)

## Stress Parameters
- Safe-high Pareto run per framework:
  - `n_solutions=50`
  - `pop_size=120`
  - `n_gen=200`
- Additional preset Pareto run per framework:
  - `n_solutions=12`
  - `pop_size=48`
  - `n_gen=60`
- Extreme Pareto probe per framework:
  - `pop_size=250`, `n_gen=500`
  - Accepted behavior: `200` (if allowed) or `422` (guardrail reject)

## Determinism Checks
- Baseline existing-suite flake check (5 repeats): **PASS**
- RC suite repeatability (full suite x3): **PASS**
- Endpoint replay checks:
  - `/api/evaluate` (`overall_score` + per-dimension scores): **PASS** (`abs_tol=1e-12`)
  - `/api/conflicts` (`spearman_rho` + `conflict_level`): **PASS**

## Minimal Backend Fix Applied
- File: `app/routers/pareto.py`
- Change: added a non-dominance filter before final Pareto solution ranking/selection.
- Reason: stress run at max `n_solutions` surfaced dominated solutions in the returned set.
- Safety: no API shape/path/schema changes; fix is internal and bounded for high-volume runs.

## Known Limitations
- Exact byte-level replay equivalence for `/api/pareto` output ordering/content was not required and is not asserted in this RC suite; invariants and non-dominance are asserted instead.
