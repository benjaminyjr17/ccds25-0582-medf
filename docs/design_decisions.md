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
**CHOICE**: Deterministic TOPSIS/WSM scoring and Spearman-based conflict analysis with stable contracts.

**ALTERNATIVES**:
- Defer algorithm implementation and focus on API shape only.
- Implement highly customized methods with breaking contract iterations.

**JUSTIFICATION**:
- Provides mathematically explicit, testable outputs for evaluation and viva defense.
- Preserves deterministic behavior and reproducibility under fixed seeds and payloads.
- Keeps endpoint contracts stable while allowing non-breaking method improvements.

**TRADE-OFF**:
- Harm-taxonomy specialization and broader empirical validation remain future extensions.

**EXAMINER ATTACK**:
"How do you justify trust in these scoring and conflict outputs?"

**DEFENSE**:
Algorithms are explicit in code, validated by tests, and deterministic under controlled inputs. The system is positioned as governance decision support with clear scope boundaries and reproducibility guarantees.
