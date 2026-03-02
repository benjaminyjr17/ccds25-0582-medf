# Evaluation Results Pack

This document records deterministic empirical outputs generated from MEDF real-deployment case studies.

## Generation Command

```bash
./.venv/bin/python scripts/generate_evidence_pack.py
```

## Generated Artifacts

- `docs/evidence/evaluation_summary.csv`
- `docs/evidence/evaluation_bundle.json`

## Content Summary

The evidence pack contains, for each case-study x framework combination:
- Evaluate output (`overall_score`, framework score breakdown).
- Conflicts output (pairwise conflict levels and rho matrices).
- Conflicts harm output (`harm_assessment` taxonomy payload).
- Pareto output (non-dominated consensus solutions, objective metadata, ablation utility).
- Provenance payload (`deployment_type`, `source_ids`).

## Determinism Settings

- Pareto payload uses deterministic mode with fixed seed.
- Case-study input scores are sourced from versioned JSON files in `case_studies/`.
- Case-study provenance is sourced from licensing-safe `evidence_manifest` entries in `case_studies/`.
- Stakeholder defaults are pulled from `/api/stakeholders`.

## Usage in Report

- Use `evaluation_summary.csv` to build compact comparison tables.
- Use `evaluation_bundle.json` for appendix-level reproducibility and traceability.
