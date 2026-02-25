# Likert Scale Safety Check (1–7 Active)

## Decision
GO.

## Summary
- Runtime validation now enforces `LIKERT_MIN=1.0` and `LIKERT_MAX=7.0` from `app/models.py`.
- Router normalization paths now use shared helpers (`validate_likert`, `normalize_likert`) from `app/scoring_engine.py`.
- Synthetic TOPSIS reference rows use `LIKERT_MAX` and `LIKERT_MIN`.
- Streamlit labels, slider bounds, and demo presets are aligned to Likert 1–7.
- Tests and documentation were migrated to match the active scale.

## Remaining Risks
- Historical screenshots or report text that reference the legacy scale should be refreshed.
- Any external client hard-coded to legacy bounds should be updated.
