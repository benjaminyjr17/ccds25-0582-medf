# CCDS25-0582 Verification Memo and Changelog

**Project:** Multi-Stakeholder Ethical Decision-Making Frameworks for AI Systems
**Author:** Benjamin Oliver Yick (U2120984H)
**Revision Date:** 7 March 2026
**Revision Pass:** Second-pass surgical revision (staged: verification, revision, polish)

---

## 1. Verification Process

The revision was conducted in three explicit stages, with a summary checkpoint after each.

### Stage 1: Verification (Code Audit and Claim Reconciliation)

A module truth map was built by reading every source file in the repository. Each factual claim in the report was then compared against the code truth map. The following verification checks were performed:

| Check | Method | Outcome |
|---|---|---|
| Module truth map | Read all 12 Python source files, 3 YAML files, 3 JSON case studies | Complete |
| `conflict_detection.py` status | Read code and test contract | Confirmed placeholder stub |
| Stakeholder weights (Table 11.1) | API query, `framework_registry.py` read | Match code |
| Case study scores (all 3) | Full API reproduction (27 scores) | All match to 4 decimal places |
| Conflict matrices (all 3) | API reproduction via `/api/conflicts` | Contribution-based matrices differ by case |
| Pareto resolution | API call for facial recognition | 10 solutions returned |
| CI/CD claim | Inspected `.github/workflows/` | Two workflow files confirmed |
| Framework YAML weights | Direct file read of all 3 YAML files | Appendix B had wrong weights (corrected) |
| API schema | OpenAPI spec inspection | Appendix A had wrong field names (corrected) |
| Screenshots | Playwright headless capture from localhost (1920x1080, 2x DPI) | 6 real screenshots captured |

### Stage 2: Revision (Corrections Applied)

All identified defects were corrected in the LaTeX source. No new content was fabricated; all corrections were grounded in the code truth map or reproduced API output.

### Stage 3: Polish (Honesty Check and Formatting)

A final sweep was performed for overclaims, formatting consistency, and front matter accuracy. The compiled PDF was visually inspected page by page.

---

## 2. Critical Corrections

### 2.1 Architectural Honesty (Chapter 7, Section 7.3)

**Before:** `app/conflict_detection.py` was described as the implemented conflict analysis engine.

**After:** Honestly described as a placeholder stub. All six public functions return empty or zero-valued results. The test file `test_conflict_detection_placeholder_contract.py` explicitly verifies this behavior. The actual conflict analysis logic is implemented inline within `app/routers/conflicts.py`. This is documented as technical debt in Chapter 13 (Limitations).

### 2.2 Conflict Matrices (Chapter 11)

**Before:** The same weights-only Spearman rho matrix (with rho = -0.31 for Developer-Affected Community) was presented identically for all three case studies, which was misleading because the weights-only matrix is independent of the case study data.

**After:** Replaced with case-specific contribution-based Spearman rho matrices reproduced from the API:

| Case Study | Dev-Reg rho | Dev-Aff rho | Reg-Aff rho | Conflict Level |
|---|---|---|---|---|
| Facial Recognition | 0.89 | 0.94 | 0.94 | Low |
| Hiring Algorithm | 0.54 | 0.77 | 0.54 | Moderate |
| Healthcare Diagnostic | -0.14 | 0.49 | 0.03 | High |

### 2.3 Framework YAML Weights (Appendix B)

**Before:** EU ALTAI weights shown as T=0.18, F=0.20, S=0.18, P=0.18, H=0.12, A=0.14.

**After:** Corrected to actual values: T=0.12, F=0.14, S=0.22, P=0.20, H=0.18, A=0.14. NIST AI RMF and Singapore MGAF excerpts also added with verified weights.

### 2.4 API Reference (Appendix A)

**Before:** Example used incorrect field names (e.g., `transparency` instead of `transparency_explainability`) and an incorrect request schema.

**After:** Corrected to use actual field names matching the Pydantic models in `app/models.py`, with the correct nested `ai_system` object structure.

### 2.5 Risk Threshold Tables (Chapter 8)

**Before:** A single ambiguous risk threshold table.

**After:** Split into two tables reflecting the two different threshold systems in the code: (1) evaluation router thresholds for closeness coefficient C, and (2) harm assessment module thresholds for harm score h.

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

Six real screenshots were captured from the live application running on localhost using Playwright headless browser automation:

| Figure | Description |
|---|---|
| Fig 10.1 | Evaluate tab (configuration interface) |
| Fig 10.2 | Evaluate results (demo scenario output) |
| Fig 10.3 | Conflict detection heatmap |
| Fig 10.4 | Pareto resolution interface |
| Fig 10.5 | Case study browser |
| Fig 10.6 | Case Study 1 results (overall score 0.3379) |

---

## 5. Known Limitations of Verification

The following items were **not** independently verified:

1. The baseline dimension scores for the three case studies are derived from qualitative analysis and are inherently subjective. No inter-rater reliability assessment was performed.
2. The risk level labels returned by the API are "N/A" in the current implementation; the risk classification logic in the Streamlit frontend was not independently verified.
3. The NSGA-II Pareto frontier results are stochastic (despite a fixed seed) and may vary slightly across different hardware or library versions.

---

## 6. Reproduced Scores (Reference Data)

All scores below were reproduced by calling the live MEDF API on 7 March 2026.

### Case Study 1: Facial Recognition

| Framework | Developer | Regulator | Affected Community |
|---|---|---|---|
| EU ALTAI | 0.4583 | 0.3092 | 0.2462 |
| NIST AI RMF | 0.5574 | 0.4524 | 0.3824 |
| Singapore MGAF | 0.4310 | 0.3465 | 0.2862 |
| **Average** | **0.4822** | **0.3694** | **0.3049** |
| **Overall** | | **0.3379** | |

### Case Study 2: Hiring Algorithm

| Framework | Developer | Regulator | Affected Community |
|---|---|---|---|
| EU ALTAI | 0.3185 | 0.3418 | 0.2462 |
| NIST AI RMF | 0.3185 | 0.3418 | 0.2462 |
| Singapore MGAF | 0.3185 | 0.3418 | 0.2462 |
| **Average** | **0.3185** | **0.3418** | **0.2462** |
| **Overall** | | **0.3022** | |

### Case Study 3: Healthcare Diagnostic

| Framework | Developer | Regulator | Affected Community |
|---|---|---|---|
| EU ALTAI | 0.6673 | 0.5376 | 0.5475 |
| NIST AI RMF | 0.6673 | 0.5376 | 0.5475 |
| Singapore MGAF | 0.6673 | 0.5376 | 0.5475 |
| **Average** | **0.6673** | **0.5376** | **0.5475** |
| **Overall** | | **0.5841** | |

---

## 7. Deliverables

| Deliverable | Location | Description |
|---|---|---|
| Compiled PDF | `thesis/main.pdf` | 75-page final report |
| LaTeX source | `thesis/main.tex` | Main document file |
| Chapter files | `thesis/chapters/*.tex` | 14 chapters + 3 appendices |
| Bibliography | `thesis/references.bib` | 27 verified references |
| Screenshots | `thesis/figures/screenshot_*.png` | 6 real localhost screenshots |
| NTU Logo | `thesis/figures/ntu_logo.png` | Cover page logo |
| This memo | `thesis/VERIFICATION_MEMO.md` | Verification documentation |
