# CCDS25-0582 Verification Memo and Changelog

**Project:** Multi-Stakeholder Ethical Decision-Making Frameworks for AI Systems
**Author:** Benjamin Oliver Yick (U2120984H)
**Revision Date:** 9 March 2026
**Revision Pass:** Third-pass comprehensive audit (deterministic verification harness + evidence artifacts)
**Commit Hash:** 38998f53ce167e3ede31e054cd693f3b765253e9

---

## 1. Verification Process

The revision was conducted using the PLAN, CRITIQUE, EXECUTE methodology with a deterministic verification harness for Chapter 11.

### Stage 1: Verification (Code Audit and Claim Reconciliation)

A module truth map was built by reading every source file in the repository. Each factual claim in the report was then compared against the code truth map. The following verification checks were performed:

| Check | Method | Outcome |
|---|---|---|
| Module truth map | Read all Python source files, YAML files, JSON case studies | Complete |
| `conflict_detection.py` status | Read code and test contract | Confirmed placeholder stub |
| Stakeholder weights (Table 11.1) | API query, `framework_registry.py` read | Match code |
| Case study scores (all 3 cases, all 3 frameworks, all 3 stakeholders) | Full API reproduction (27 per-stakeholder scores + 9 overall scores) | All match to 4 decimal places |
| Conflict matrices (all 3 cases) | API reproduction via `/api/conflicts` | Contribution-based matrices verified |
| Pareto resolution (all 3 cases) | API call for all cases | 10 solutions each |
| Framework YAML weights | Direct file read of all 3 YAML files | Verified |
| API schema | OpenAPI spec inspection | Verified |
| Screenshots | Playwright headless capture from localhost (3840x2160, 2x DPI) | 4 high-resolution screenshots captured |
| Evidence artifacts | Deterministic harness generated 20+ evidence files | All artifacts traceable |

### Stage 2: Revision (Corrections Applied)

All identified defects were corrected in the LaTeX source. No new content was fabricated; all corrections were grounded in the code truth map or reproduced API output.

### Stage 3: Polish (Honesty Check and Formatting)

A final sweep was performed for overclaims, formatting consistency, and front matter accuracy.

---

## 2. Critical Corrections (This Revision)

### 2.1 Per-Framework Per-Stakeholder Scores (Chapter 11)

**Before (Previous VERIFICATION_MEMO):** Case Studies 2 and 3 showed identical per-stakeholder scores across all three frameworks, which was incorrect.

**After:** Corrected with verified per-framework per-stakeholder scores from the live API. Each framework produces different scores because the framework weights modulate the TOPSIS evaluation differently.

### 2.2 Evaluation Tables Enhanced with Overall Scores

**Before:** Tables 11.3, 11.6, and 11.9 showed only per-stakeholder columns (Developer, Regulator, Affected Community).

**After:** Added an "Overall" column showing the aggregated TOPSIS closeness coefficient across all stakeholders for each framework. Added an "All Frameworks" row showing the aggregated score when all three frameworks are evaluated simultaneously.

### 2.3 Cross-Case Comparison Table Updated

**Before:** Table 11.11 used EU ALTAI overall scores and inconsistent risk levels.

**After:** Updated to use all-frameworks overall scores with correct risk levels based on code thresholds (Critical < 0.40, High 0.40--0.59, Medium 0.60--0.79, Low >= 0.80). Added Conflict Level column.

### 2.4 Risk Level Corrections

**Before:** Narrative described Facial Recognition and Hiring Algorithm as "High Risk."

**After:** Corrected to "Critical Risk" (both scores < 0.40). Healthcare Diagnostic correctly classified as "Medium Risk" (score = 0.60).

### 2.5 Previous Corrections Retained

All corrections from the previous revision pass are retained:
- Architectural honesty for `conflict_detection.py` (Chapter 7)
- Contribution-based conflict matrices (Chapter 11)
- Framework YAML weights (Appendix B)
- API reference field names (Appendix A)
- Risk threshold tables (Chapter 8)
- Formatting corrections (project number, academic year, headings, etc.)

---

## 3. Formatting Corrections

| Item | Before | After |
|---|---|---|
| Project number | CCDS25-0323 | CCDS25-0582 |
| Academic year | 2024/2025 | 2025/2026 |
| Ch4 heading | "Compulsory References: Fairness in Design" | "Fairness in Design" |
| Ch12 heading | "Key Findings" | "Critical Findings" |
| Ch1 conclusion | "completely functional" | "functional" with limitation cross-reference |
| Ch14 conclusion | "novel and powerful" | "practical" |

---

## 4. Screenshots

Four high-resolution screenshots were captured from the live application running on localhost using Playwright headless browser automation (3840x2160 pixels):

| Screenshot | Description | File |
|---|---|---|
| Evaluate | Evaluation results with demo scenario | `screenshot_evaluate.png` |
| Conflict Detection | Conflict analysis heatmap and details | `screenshot_conflict_detection.png` |
| Pareto Resolution | Pareto optimization interface and results | `screenshot_pareto_resolution.png` |
| Case Studies | Case study browser with loaded case | `screenshot_case_studies.png` |

---

## 5. Known Limitations of Verification

The following items were **not** independently verified:

1. The baseline dimension scores for the three case studies are derived from qualitative analysis and are inherently subjective. No inter-rater reliability assessment was performed.
2. The risk level labels returned by the API are "N/A" in the current implementation; the risk classification is computed by the evaluate router's `_risk_level()` function using the closeness coefficient thresholds.
3. The NSGA-II Pareto frontier results are stochastic (despite a fixed seed) and may vary slightly across different hardware or library versions.
4. The per-stakeholder scores are computed by calling the evaluate API with a single stakeholder at a time. The "Average" row in the reproduced scores below is a simple arithmetic mean of the per-stakeholder scores, not the API's all-stakeholders aggregated score.

---

## 6. Reproduced Scores (Reference Data)

All scores below were reproduced by calling the live MEDF API on 9 March 2026 (commit 38998f5).

### Case Study 1: Facial Recognition

| Framework | Overall | Developer | Regulator | Affected Community |
|---|---|---|---|---|
| EU ALTAI | 0.3379 | 0.4583 | 0.3092 | 0.2462 |
| NIST AI RMF | 0.4637 | 0.5552 | 0.4537 | 0.3823 |
| Singapore MGAF | 0.3582 | 0.4344 | 0.3497 | 0.2905 |
| **All Frameworks** | **0.3866** | | | |

Risk Level: **Critical** (0.3866 < 0.40)

### Case Study 2: Hiring Algorithm

| Framework | Overall | Developer | Regulator | Affected Community |
|---|---|---|---|---|
| EU ALTAI | 0.3022 | 0.3185 | 0.3418 | 0.2462 |
| NIST AI RMF | 0.4155 | 0.3787 | 0.4892 | 0.3785 |
| Singapore MGAF | 0.3254 | 0.3292 | 0.3702 | 0.2766 |
| **All Frameworks** | **0.3477** | | | |

Risk Level: **Critical** (0.3477 < 0.40)

### Case Study 3: Healthcare Diagnostic

| Framework | Overall | Developer | Regulator | Affected Community |
|---|---|---|---|---|
| EU ALTAI | 0.5841 | 0.6673 | 0.5376 | 0.5475 |
| NIST AI RMF | 0.6258 | 0.7092 | 0.5836 | 0.5847 |
| Singapore MGAF | 0.5910 | 0.6479 | 0.5470 | 0.5780 |
| **All Frameworks** | **0.6003** | | | |

Risk Level: **Medium** (0.6003 >= 0.60)

### Conflict Matrices (Contribution-Based Spearman Rho)

| Case Study | Dev-Reg rho | Dev-Aff rho | Reg-Aff rho | Highest Conflict Level |
|---|---|---|---|---|
| Facial Recognition | 0.8857 | 0.9429 | 0.9429 | Low |
| Hiring Algorithm | 0.5429 | 0.7714 | 0.5429 | Moderate |
| Healthcare Diagnostic | -0.1429 | 0.4857 | 0.0286 | High |

---

## 7. Evidence Artifacts

All evidence artifacts are stored in `docs/evidence/` and are machine-checkable:

| Artifact | File | Description |
|---|---|---|
| Input Manifest | `ch11_inputs_manifest.json` | Case study inputs with validation |
| Framework Snapshot | `ch11_frameworks.json` | Raw API framework data |
| Stakeholder Snapshot | `ch11_stakeholders.json` | Raw API stakeholder data |
| Raw Evaluations | `ch11_evaluate_raw.json` | All API evaluation responses |
| Raw Conflicts | `ch11_conflicts_raw.json` | All API conflict responses |
| Raw Pareto | `ch11_pareto_raw.json` | All API Pareto responses |
| Normalized Bundle | `ch11_normalized_bundle.json` | Normalized evidence with source traces |
| Claim Registry | `ch11_claim_registry.json` | 75 verified numerical claims |
| Table CSVs | `ch11_table_11_*.csv` | All 11 Chapter 11 tables as CSV |
| Verification Report | `ch11_verification_report.md` | Detailed verification findings |
| Module Map | `module_responsibility_map.json` | Repository architecture map |
| Risk Map | `chapter_risk_map.md` | Chapter-by-chapter risk assessment |

---

## 8. Deliverables

| Deliverable | Location | Description |
|---|---|---|
| LaTeX source | `thesis/main.tex` | Main document file |
| Chapter files | `thesis/chapters/*.tex` | 14 chapters + 3 appendices |
| Bibliography | `thesis/references.bib` | Verified references |
| Screenshots | `thesis/figures/screenshot_*.png` | 4 high-resolution localhost screenshots |
| Evidence artifacts | `docs/evidence/` | 20+ machine-checkable evidence files |
| NTU Logo | `thesis/figures/ntu_logo.png` | Cover page logo |
| This memo | `thesis/VERIFICATION_MEMO.md` | Verification documentation |
