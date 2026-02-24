# Consistency Audit
Date: 2026-02-24

## Scope
Repo-wide audit across `*.py`, `*.yaml`, and `*.json` for:
- Canonical dimension keys:
  - `transparency_explainability`
  - `fairness_nondiscrimination`
  - `safety_robustness`
  - `privacy_data_governance`
  - `human_agency_oversight`
  - `accountability`
- Canonical stakeholder IDs: `developer`, `regulator`, `affected_community` (string IDs)

## Changes Applied
1. Updated canonical dimension constants and validation rules.
- File: `app/models.py`
- Changes:
  - Replaced old unified keys (`fairness`, `transparency`, `privacy`, `safety`, `human_oversight`) with canonical keys.
  - Updated `DIMENSION_DISPLAY_NAMES` to canonical key map.
  - Enforced stakeholder weight sum validation: weights must sum to `1.0 ± 0.01` when full six-dimension vectors are required.

2. Updated default stakeholder weight vectors to canonical keys.
- File: `app/framework_registry.py`
- Changes:
  - Replaced old key names in `_DEFAULT_STAKEHOLDER_WEIGHTS`.
  - Preserved three canonical stakeholder IDs: `developer`, `regulator`, `affected_community`.

3. Enforced framework integrity checks.
- File: `app/framework_registry.py`
- Changes:
  - `load_frameworks()` now validates each framework has all 6 canonical dimensions.
  - Validates framework dimension weights sum to `1.0 ± 0.01`.

4. Normalized all framework YAML dimension keys and weights.
- Files:
  - `app/frameworks/eu_altai.yaml`
  - `app/frameworks/nist_ai_rmf.yaml`
  - `app/frameworks/sg_mgaf.yaml`
- Changes:
  - Replaced non-canonical `dimension:` values with canonical keys.
  - Adjusted weights so each framework has exactly 6 dimensions and total weight sum is `1.0`.

5. Hardened default stakeholder seeding consistency.
- File: `app/framework_registry.py`
- Changes:
  - `seed_default_stakeholders()` now updates existing default rows as well as inserts missing ones.
  - Ensures defaults always have canonical IDs, canonical roles, canonical 6-key weights, and `is_default=true`.

## Verification Results
1. Old key pattern scan (`dimension: fairness|transparency|privacy|safety|human_oversight` and quoted-key variants):
- Result: no matches in `*.py`, `*.yaml`, `*.json`.

2. Framework structure checks:
- `eu_altai.yaml`: 6 dimensions, weight sum `1.0000`
- `nist_ai_rmf.yaml`: 6 dimensions, weight sum `1.0000`
- `sg_mgaf.yaml`: 6 dimensions, weight sum `1.0000`

3. Default stakeholder vector checks:
- `developer`: 6 keys, sum `1.0000`
- `regulator`: 6 keys, sum `1.0000`
- `affected_community`: 6 keys, sum `1.0000`

4. Syntax/import check:
- `python -m compileall app`: pass
- Note: Strings like `human_oversight` may appear in YAML criterion IDs.
- These are identifier labels and are not treated as unified dimension keys.
