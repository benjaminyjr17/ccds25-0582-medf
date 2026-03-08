# MEDF — Architecture Description
Date: 2026-02-28
Version: 1.0.0
Scope: FYP freeze candidate

## 1. Architecture Overview

MEDF uses a modular three-layer architecture:
- Presentation layer: Streamlit UI (`streamlit_app.py`) for governance-facing workflows.
- API/orchestration layer: FastAPI routes (`app/routers/*`) for validation, execution, serialization.
- Data/config layer: SQLite stakeholder store + YAML framework registry.

Design goal: deterministic, auditable, and testable multi-framework ethical assessment for FYP evaluation.

## 2. Component Design

Core backend components:
- `app/main.py`: app startup, DB init, framework load, default stakeholder seeding.
- `app/models.py`: API schemas and ORM models.
- `app/database.py`: SQLAlchemy engine/session/base.
- `app/framework_registry.py`: framework ingestion and canonical-dimension enforcement.
- `app/scoring_engine.py`: TOPSIS/WSM/AHP utilities and Likert normalization.
- `app/routers/evaluate.py`: multi-framework scoring orchestration.
- `app/routers/conflicts.py`: stakeholder disagreement analysis.
- `app/routers/pareto.py`: NSGA-II/non-dominated consensus generation.
- `app/audit_log.py`: request/response audit persistence.

Conflict analysis is currently implemented inside `app/routers/conflicts.py` rather than in a separate engine module.

## 3. Runtime Flow

1. Startup: initialize DB, load framework YAMLs, seed default stakeholders.
2. Request validation: Pydantic schema checks + route-level constraints.
3. Domain execution:
   - `/api/evaluate`: framework-weighted stakeholder scoring.
   - `/api/conflicts`: pairwise conflict metrics, metadata, and typed harm-assessment output.
   - `/api/pareto`: deterministic consensus optimization.
4. Audit write: run metadata and payload snapshots to JSONL.
5. Streamlit layer renders outputs and allows bundle export.

## 4. Diagram Source of Truth

- Canonical source: `docs/architecture/system_architecture.mmd`
- Committed export: `docs/architecture/system_architecture.svg`

## 5. Validation Boundary

- API contract lock: `tests/test_api_contract_lock.py`
- Determinism and invariants: release-candidate test modules in `tests/`
- End-to-end smoke/stress execution: `scripts/release_smoke.sh`
