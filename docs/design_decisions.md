# MEDF — Design Decisions Document
Date: 2026-02-24  
Version: 1.0.0  
Scope: Aligned to Stage 1 prompts

## Decision 1
**CHOICE**: FastAPI for backend API layer.

**ALTERNATIVES**:
- Flask
- Django

**JUSTIFICATION**:
- Native Pydantic integration for strict schema validation.
- Built-in OpenAPI docs for examiner-visible API transparency.
- Async-capable architecture without heavy framework overhead.

**TRADE-OFF**:
- Less built-in admin/auth scaffolding than Django.
- Slightly higher model strictness requires disciplined schema updates.

**EXAMINER ATTACK**:
"Why not use Flask if this is only a prototype?"

**DEFENSE**:
FastAPI reduces integration risk between typed request/response contracts and algorithm modules, which is central to reproducible evaluation outcomes.

## Decision 2
**CHOICE**: Streamlit for research dashboard.

**ALTERNATIVES**:
- React (with separate API client)
- Flask/Jinja templates

**JUSTIFICATION**:
- Faster iteration for experiment visualization.
- Tight Python-native integration with analytical outputs.
- Lower setup overhead for a single-repo academic prototype.

**TRADE-OFF**:
- Less frontend customization and component granularity than React.
- Not ideal for production-scale UX complexity.

**EXAMINER ATTACK**:
"Why not React for professional-grade UI?"

**DEFENSE**:
Stage 1 prioritizes methodological validation and reproducibility over production UI sophistication; Streamlit optimizes that objective.

## Decision 3
**CHOICE**: SQLite + SQLAlchemy ORM for persistence.

**ALTERNATIVES**:
- PostgreSQL
- Pure in-memory store

**JUSTIFICATION**:
- Zero-infrastructure local reproducibility for examiners.
- SQLAlchemy gives future migration path without rewriting data access.
- Sufficient for Stage 1 dataset size and access patterns.

**TRADE-OFF**:
- Limited write concurrency and operational scaling compared to PostgreSQL.

**EXAMINER ATTACK**:
"SQLite is not enterprise-grade."

**DEFENSE**:
Correct; this is a controlled research prototype. Architecture keeps persistence abstraction thin so migration to PostgreSQL is straightforward when scaling is required.

## Decision 4
**CHOICE**: YAML-based framework definitions.

**ALTERNATIVES**:
- Hardcoded framework criteria in Python
- Database-only framework metadata

**JUSTIFICATION**:
- Human-readable, version-controlled governance criteria.
- Easier audit and change tracking for framework evolution.
- Allows non-code updates to criteria definitions.

**TRADE-OFF**:
- Requires robust parse/validation guards at load time.

**EXAMINER ATTACK**:
"YAML introduces parsing fragility."

**DEFENSE**:
The registry enforces strict conversion to typed models and fails fast on missing/invalid files, making failures explicit rather than silent.

## Decision 5
**CHOICE**: Deterministic placeholder scoring/conflict modules in Stage 1.

**ALTERNATIVES**:
- Implement full MCDA and statistical methods immediately

**JUSTIFICATION**:
- Validates end-to-end API contracts and orchestration first.
- Minimizes confounding factors during integration testing.
- Supports incremental delivery and staged verification.

**TRADE-OFF**:
- Current scores/conflicts are not methodologically final.

**EXAMINER ATTACK**:
"This is not yet real ethical scoring."

**DEFENSE**:
Agreed; Stage 1 explicitly targets architecture correctness and interface stability. Full algorithms are layered next without changing endpoint contracts.
