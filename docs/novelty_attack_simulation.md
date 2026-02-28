# MEDF — Novelty Attack Simulation (Viva Defense Stress Test)
Date: 2026-02-28
Version: 1.0.0
Scope: FYP defense rehearsal (frozen build)

## 10 Examiner Attacks and Defense Lines

### Attack 1: "This is just a wrapper over existing frameworks. Where is novelty?"
Defense:
- Novelty is the integrated pipeline: cross-framework comparison + stakeholder conflict modeling + Pareto compromise search under one API contract.

### Attack 2: "Your scoring seems arbitrary."
Defense:
- Scoring algorithms and normalization are explicit in code (`app/scoring_engine.py`) and validated in tests.

### Attack 3: "Why trust stakeholder weights?"
Defense:
- Weights are explicit user inputs/default profiles, validated for completeness and unit-sum constraints.

### Attack 4: "Conflict detection is weak."
Defense:
- Conflict outputs include pairwise Spearman correlation, conflict levels, and conflicting dimensions in reproducible metadata.

### Attack 5: "No scalability proof."
Defense:
- Stress routines and high-parameter Pareto runs are included in release smoke and RC test suites.

### Attack 6: "Why not just use one framework?"
Defense:
- Single-framework outputs can hide normative disagreement; MEDF explicitly measures cross-framework shifts.

### Attack 7: "Your harmonization mapping may bias outcomes."
Defense:
- Mapping is explicit in framework YAML + canonical dimensions and is auditable through regulatory trace docs.

### Attack 8: "This is engineering, not research contribution."
Defense:
- Contribution is computational formalization and reproducible evaluation method for multi-stakeholder ethical trade-offs.

### Attack 9: "Where is empirical validation?"
Defense:
- Evidence pack generation and case-study reproducible outputs are included and versioned for report inclusion.

### Attack 10: "How do you defend reproducibility?"
Defense:
- Deterministic mode, seed control, API schema lock, audit logging, and repeatability tests provide concrete replayability.

## Quick-Reference Defense Matrix
- Novelty: integrated governance analytics pipeline.
- Rigor: deterministic contracts, locked API surface, extensive test evidence.
- Scope: research-grade decision support; not production compliance certification.
- Risk mitigation: explicit mappings, explicit constraints, explicit artifacts.

## Rehearsal Protocol
1. 60-second system summary: problem, novelty, architecture.
2. 90-second method summary: scoring, conflicts, Pareto.
3. 90-second reproducibility summary: deterministic controls + artifact replay.
4. 3-minute attack drill: one claim + one code/doc artifact per challenge.
5. Final check: avoid overstating legal/compliance guarantees.
