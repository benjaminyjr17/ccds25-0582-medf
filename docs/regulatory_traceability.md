# Regulatory Traceability Annex

This annex documents how framework-specific regulatory/control items are mapped into the MEDF unified six-dimension ontology.

## Mapping Principle

- Source frameworks define requirement-like units under structure keys such as `requirements`, `subcategories`, and `principles`.
- Each framework criterion is normalized to one of the canonical dimensions in `UNIFIED_DIMENSIONS`.
- Framework priors used in `/api/evaluate` are derived from section coverage counts in `_framework_section_weights` (`app/routers/evaluate.py`).

Formula:

```text
w_fw[i] = c_i / sum_j c_j
```

where `c_i` is the counted section coverage for dimension `i`.

## Framework Coverage Mapping

### EU ALTAI (`eu_altai`)

| Requirement Group | YAML Key | Unified Dimension |
|---|---|---|
| ALTAI-FR-* | `requirements` | `fairness_nondiscrimination` |
| ALTAI-AC-* | `requirements` | `accountability` |
| ALTAI-TR-* | `requirements` | `transparency_explainability` |
| ALTAI-PR-* | `requirements` | `privacy_data_governance` |
| ALTAI-SF-* | `requirements` | `safety_robustness` |
| ALTAI-HO-* | `requirements` | `human_agency_oversight` |

Source: `app/frameworks/eu_altai.yaml`.

### NIST AI RMF (`nist_ai_rmf`)

| Requirement Group | YAML Key | Unified Dimension |
|---|---|---|
| MAP / MEASURE fairness controls | `subcategories` | `fairness_nondiscrimination` |
| GOVERN / MANAGE governance controls | `subcategories` | `accountability` |
| MAP / MANAGE explainability controls | `subcategories` | `transparency_explainability` |
| MAP / MEASURE data/privacy controls | `subcategories` | `privacy_data_governance` |
| MEASURE / MANAGE robustness controls | `subcategories` | `safety_robustness` |
| GOVERN / MANAGE oversight controls | `subcategories` | `human_agency_oversight` |

Source: `app/frameworks/nist_ai_rmf.yaml`.

### Singapore Model AIGF (`sg_mgaf`)

| Requirement Group | YAML Key | Unified Dimension |
|---|---|---|
| SG-FAIR-* | `principles` | `fairness_nondiscrimination` |
| SG-GOV-* | `principles` | `accountability` |
| SG-TRN-* | `principles` | `transparency_explainability` |
| SG-DG-* | `principles` | `privacy_data_governance` |
| SG-OPS-* | `principles` | `safety_robustness` |
| SG-HO-* | `principles` | `human_agency_oversight` |

Source: `app/frameworks/sg_mgaf.yaml`.

## Implementation Hooks

- Framework parsing and canonical dimension enforcement: `app/framework_registry.py`.
- Framework prior derivation in evaluate route: `app/routers/evaluate.py` (`_framework_section_weights`).
- Framework-agnostic scoring over unified dimensions: `app/scoring_engine.py`.
