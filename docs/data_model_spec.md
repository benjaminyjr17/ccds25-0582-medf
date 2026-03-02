# MEDF Data Model Spec (Frozen Build)

This repository implements the MEDF backend for multi-framework ethical AI assessment with reproducible API contracts.

## Core Entities

### FrameworkDefinition (YAML + API)
- `id: str`
- `name: str`
- `version: str | None`
- `dimensions: list[EthicalDimension]`

### EthicalDimension
- `name`: one of the 6 unified dimensions
- `display_name: str`
- `description: str | None`
- `weight_default: float` (framework-level prior)
- `criteria_type: "benefit" | "cost"`
- `assessment_questions: list[str]`

### Stakeholder (SQLite + API)
- `id: str`
- `name: str`
- `role: "developer" | "regulator" | "affected_community" | "custom"`
- `description: str | None`
- `weights: dict[dimension, float]` (sum to 1.0 ± 0.01)

Default seeded stakeholders:
- Developer
- Regulator
- Affected Community

### EvaluateRequest / EvaluationResult
- Input: `ai_system`, `framework_ids`, `stakeholder_ids`, `weights`, `scoring_method`
- Output: `framework_scores`, `overall_score`, run metadata notes

### ConflictRequest / ConflictReport
- Input: `ai_system`, selected framework, stakeholder ids, optional weight overrides
- Output: pairwise conflict list, Spearman rho, conflict levels, correlation matrices, typed `harm_assessment` payload

### ParetoRequest / ConflictReport(pareto payload)
- Input: `ai_system`, selected framework, stakeholder ids, optimization controls (`n_solutions`, `pop_size`, `n_gen`, `seed`, deterministic mode)
- Output: non-dominated Pareto consensus solutions + objective metadata

## Implemented Endpoints
- `GET /api/health`
- `GET /api/frameworks`
- `GET /api/frameworks/{framework_id}`
- `GET /api/stakeholders`
- `POST /api/stakeholders`
- `POST /api/evaluate`
- `POST /api/conflicts`
- `POST /api/pareto`

## Contract Stability

The `/api` surface and OpenAPI fingerprint are locked by `tests/test_api_contract_lock.py`.
