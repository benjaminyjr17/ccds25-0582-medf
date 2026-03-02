# MEDF Engineering Freeze — v1.1.0-freeze

**Date:** 2026-03-02
**Project:** CCDS25-0582 — Multi-stakeholder Ethical Decision Framework for AI Systems
**Status:** Feature-frozen. No further code changes permitted.

## Scope of v1.1.0-freeze

This release includes all functionality developed for the MEDF platform:

- Three regulatory frameworks (EU AI Act ALTAI, NIST AI RMF, Singapore MGAF)
- Six ethical dimensions with 1–7 Likert scoring
- Stakeholder conflict detection with pairwise alignment
- Multi-objective Pareto resolution (NSGA-II)
- Three embedded case studies with evidence manifests
- Interactive Streamlit dashboard
- Full audit logging and evidence pack generation
- Research statistics pipeline

## Changes Since v1.0.1

- UI string standardization: 46+ edits across three batches (Title Case, en dashes, terminology precision, formal case study identifiers, correct abbreviations)
- Computational Budget slider: range widened to 500–50,000 with step precision of 1
- HARD_CAP_EVALS raised to 50,000 (symmetric with auto mode)
- Repo cleanup: removed dead dashboard module, development artifacts, runtime telemetry data
- README rewritten for dual audience (FYP examiner + open-source)

## Test Results

- All tests passing (54+ tests)
- Categories: unit, integration, property-based, stress, end-to-end
- CI: GitHub Actions workflow at `.github/workflows/test.yml`

## Post-Freeze Policy

No code changes are permitted after this tag. Only documentation updates to the FYP report are allowed. If a critical bug is discovered, it must be documented in the report rather than fixed in code.
