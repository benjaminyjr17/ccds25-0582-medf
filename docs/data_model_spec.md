# MEDF Data Model Spec (Reference)

This repository implements a minimal backend skeleton for the Multi-stakeholder Ethical Decision Framework (MEDF) with:

- FastAPI API layer.
- Pydantic v2 request/response models.
- SQLAlchemy 2.0 ORM with SQLite.
- YAML-based framework registry.

## Core Entities

### FrameworkDefinition (YAML + API)
- `id: str`
- `name: str`
- `version: str | None`
- `description: str | None`
- `criteria: list[FrameworkCriterion]`

### FrameworkCriterion
- `id: str`
- `name: str`
- `dimension: "fairness" | "accountability" | "transparency" | "privacy" | "safety" | "human_oversight"`
- `description: str | None`
- `weight: float` (required)

### Stakeholder (SQLite + API)
- `id: str` (API response; sourced from internal DB key)
- `name: str` (unique)
- `role: "developer" | "regulator" | "affected_community" | "custom"`
- `description: str`

Default seeded stakeholders:
- Developer
- Regulator
- Affected Community

### EvaluationRequest / EvaluationResponse (API)
- Input: `case_id`, selected `framework_ids: list[str]`, selected `stakeholder_ids: list[str]`, required `weights` (full six-dimension vector per stakeholder), optional `inputs`.
- Output: deterministic placeholder `scores` by framework ID.

### ConflictCheckRequest / ConflictCheckResponse (API)
- Input: selected `framework_ids`, selected `stakeholder_ids`.
- Output: placeholder conflict summary + metadata until full algorithm integration.

## Implemented Endpoints
- `GET /api/health`
- `GET /api/frameworks`
- `GET /api/stakeholders`
- `POST /api/evaluate` (stub scoring)
- `POST /api/conflicts` (stub conflict detection)
