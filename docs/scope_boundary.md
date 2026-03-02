# Scope Boundary

## In Scope (FYP Submission Build)

- Multi-framework ethical evaluation over a unified six-dimension model.
- Stakeholder profile persistence, override weights, and validation.
- Conflict analysis via pairwise stakeholder rank correlation.
- Pareto-based consensus weight generation with deterministic controls.
- Streamlit governance UI with Conference Mode and evidence bundle export.
- CI-backed test suite and release smoke validation.

## Out of Scope (Intentional)

- Authentication/authorization and production security hardening.
- Distributed deployment, multi-tenant orchestration, and cloud SRE tooling.
- Real-time streaming inference integration.
- Legal compliance certification automation.
- Fine-grained domain-specific harm ontologies beyond the current six-domain harm taxonomy.

## Evaluation Interpretation Boundary

- The platform supports governance-oriented pre-deployment analysis.
- Outputs are decision-support diagnostics, not legal determinations.
- Case studies are real deployments with curated public-source provenance for reproducible governance analysis.

## Freeze Policy Boundary

- No API path/schema changes within freeze tag without explicit version bump and lock hash update.
- Only defect-level fixes are permitted post-freeze; no scope expansion.
