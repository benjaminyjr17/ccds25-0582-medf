# Requirements Traceability (CCDS25-0582)

Source document: `/Users/benjaminoliveryick/Downloads/document_pdf.pdf` (NTU WIS export, accessed 2026-02-28).

## Requirement Ledger

| Requirement ID | Official Requirement Text | Pass Condition | Evidence (Code + Artifact) | Status |
|---|---|---|---|---|
| RQ-01 | Design a platform to evaluate AI applications against multiple ethical frameworks, regulatory requirements, and stakeholder values. | The system accepts one AI system profile and evaluates it under multiple frameworks with stakeholder-specific weights in a single workflow. | `app/routers/evaluate.py`, `app/frameworks/*.yaml`, `tests/test_api_evaluate.py`, `tests/test_system_e2e_top_tier.py` | PASS |
| RQ-02 | Capture different perspectives. | At least three stakeholder profiles can be loaded/persisted and used during evaluation, conflict detection, and Pareto analysis. | `app/framework_registry.py`, `app/routers/stakeholders.py`, `app/routers/conflicts.py`, `app/routers/pareto.py` | PASS |
| RQ-03 | Help identify potential conflicts or harms before deployment. | System provides pairwise stakeholder conflict outputs and interpretable disagreement metadata from pre-deployment input scores. | `app/routers/conflicts.py`, `tests/test_api_conflicts.py`, `tests/test_release_candidate_invariants.py` | PASS (conflict), PARTIAL (explicit harm taxonomy not separated) |
| RQ-04 | Specific detail (a): Design component — designing an ethical AI framework. | Unified ethical-dimension ontology and framework registry are implemented and validated. | `app/models.py`, `app/framework_registry.py`, `app/frameworks/*.yaml`, `docs/regulatory_traceability.md` | PASS |
| RQ-05 | Specific detail (b): Implementation component — testing the framework against real-world AI deployments. | At least three deployment-grounded case studies are defined with provenance and reproducible outputs across Evaluate/Conflicts/Pareto. | `case_studies/*.json`, `streamlit_app.py`, `scripts/generate_evidence_pack.py`, `docs/evaluation_results.md` | PASS |
| RQ-06 | Specific detail (a): Research component. | Methodological decisions, assumptions, and reproducible empirical outputs are documented and auditable. | `implementation_log.md`, `docs/assumptions.md`, `docs/reproducibility_audit.md`, `docs/evaluation_results.md` | PASS |
| RQ-07 | Specific detail (b): Development component. | Full software stack is runnable, tested, and CI-validated with deterministic controls and freeze checks. | `app/`, `streamlit_app.py`, `.github/workflows/test.yml`, `tests/`, `scripts/release_smoke.sh`, `FREEZE.md` | PASS |

## Notes

- This project is a software-only FYP (`Category: Software Only`, `Type: Design & Implementation`) per the official project record.
- No additional rubric document was provided in-repo; this ledger tracks only requirements explicitly present in the official project PDF and executable evidence in this repository.
