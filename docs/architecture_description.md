# MEDF — Architecture Description
Date: 2026-02-24  
Version: 1.0.0  
Scope: Aligned to Stage 1 prompts

## 1. Architecture Overview
The MEDF system uses a modular three-layer architecture:
- API and orchestration layer (`FastAPI`) for request handling and contract enforcement.
- Domain logic layer for framework loading, scoring, and conflict analysis.
- Data layer (`SQLite` + SQLAlchemy ORM) for stakeholder profile persistence.

Design goal: produce deterministic, auditable Stage 1 outputs while preserving extensibility for advanced scoring and optimization in later stages.

## 2. Component Design
Core backend components:
- `app/main.py`: app bootstrap, startup initialization, health endpoint, router wiring.
- `app/models.py`: Stage 1C schemas (Pydantic v2) + ORM table for stakeholder profiles.
- `app/database.py`: SQLAlchemy engine/session/base setup.
- `app/framework_registry.py`: YAML framework ingestion, in-memory registry, harmonisation mapping, default stakeholder seeding.
- `app/scoring_engine.py`: deterministic placeholder scoring function.
- `app/conflict_detection.py`: deterministic placeholder conflict and Pareto interfaces.
- Routers:
  - `app/routers/frameworks.py`
  - `app/routers/stakeholders.py`
  - `app/routers/evaluate.py`
  - `app/routers/conflicts.py`

## 3. Runtime Flow
1. Startup initializes DB schema (`init_db()`), loads framework YAMLs (`load_frameworks()`), and seeds default stakeholders (`seed_default_stakeholders()`).
2. Client requests are validated against Stage 1C request schemas.
3. Routers call domain services:
   - frameworks endpoints query in-memory registry,
   - stakeholders endpoints query/update SQLite,
   - evaluate endpoint invokes deterministic scoring,
   - conflicts endpoint computes placeholder conflict report.
4. Responses return strongly typed Stage 1C response models.

## 4. Architecture Diagram
```mermaid
flowchart TD
    A[Client / Dashboard] --> B[FastAPI App]

    subgraph API[API Routers]
      B --> R1[/api/frameworks]
      B --> R2[/api/stakeholders]
      B --> R3[/api/evaluate]
      B --> R4[/api/conflicts]
      B --> RH[/api/health]
    end

    subgraph Domain[Domain Services]
      R1 --> FR[framework_registry]
      R2 --> FR2[framework_registry.get_stakeholder]
      R3 --> SE[scoring_engine.compute_scores]
      R3 --> FR3[framework_registry.get_framework/get_stakeholder]
      R4 --> CD[conflict_detection placeholders]
      R4 --> SE2[scoring_engine.compute_scores]
      R4 --> FR4[framework_registry.get_framework/get_stakeholder]
    end

    subgraph Data[Data Layer]
      DB[(SQLite medf.db)]
      YM[(YAML frameworks/*.yaml)]
    end

    FR --> YM
    FR3 --> YM
    FR4 --> YM
    FR2 --> DB
    R2 --> DB
    R3 --> DB
    R4 --> DB

    B --> S[Startup]
    S --> D1[init_db]
    S --> D2[load_frameworks]
    S --> D3[seed_default_stakeholders]
    D1 --> DB
    D2 --> YM
    D3 --> DB
```
