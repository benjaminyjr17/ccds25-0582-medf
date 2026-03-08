# Chapter Risk Map — CCDS25-0582 FYP Report Audit

## Chapter 11 Numerical Discrepancies

The current report presents per-stakeholder scores in the evaluation tables (e.g., Table 11.3 shows Developer=0.46, Regulator=0.31, Affected Community=0.25 for EU ALTAI on facial recognition). However, the live API returns a single **overall score per framework** (e.g., eu_altai=0.3379), not per-stakeholder scores. The report's table structure (with per-stakeholder columns) does not match the API's output format.

### Key Findings

**Evaluation Results — Facial Recognition (Case 1)**

| Metric | Report Claims | Verified API |
|--------|--------------|-------------|
| EU ALTAI overall | ~0.39 (avg of 0.46, 0.31, 0.25) | 0.3379 |
| NIST AI RMF overall | ~0.46 (avg of 0.56, 0.45, 0.38) | 0.4637 |
| Singapore MGAF overall | ~0.36 (avg of 0.43, 0.35, 0.29) | 0.3582 |
| Risk Level | High | Critical (eu_altai, sg_mgaf), High (nist_ai_rmf) |

**Evaluation Results — Hiring Algorithm (Case 2)**

| Metric | Report Claims | Verified API |
|--------|--------------|-------------|
| EU ALTAI overall | ~0.30 (avg of 0.32, 0.34, 0.25) | 0.3022 |
| NIST AI RMF overall | ~0.42 (avg of 0.38, 0.49, 0.38) | 0.4155 |
| Singapore MGAF overall | ~0.33 (avg of 0.33, 0.37, 0.28) | 0.3254 |
| Risk Level | High | Critical (eu_altai, sg_mgaf), High (nist_ai_rmf) |

**Evaluation Results — Healthcare Diagnostic (Case 3)**

| Metric | Report Claims | Verified API |
|--------|--------------|-------------|
| EU ALTAI overall | ~0.59 (avg of 0.67, 0.54, 0.55) | 0.5841 |
| NIST AI RMF overall | ~0.62 (avg of 0.71, 0.58, 0.58) | 0.6258 |
| Singapore MGAF overall | ~0.59 (avg of 0.65, 0.55, 0.58) | 0.5910 |
| Risk Level | Medium | High (eu_altai, sg_mgaf), Medium (nist_ai_rmf) |

**Conflict Matrices — All cases match API output closely:**

| Case | Pair | Report ρ | API ρ | Match? |
|------|------|----------|-------|--------|
| Facial Recognition | Dev-Reg | 0.89 | 0.8857 | YES (rounded) |
| Facial Recognition | Dev-AC | 0.94 | 0.9429 | YES (rounded) |
| Facial Recognition | Reg-AC | 0.94 | 0.9429 | YES (rounded) |
| Hiring Algorithm | Dev-Reg | 0.54 | 0.5429 | YES (rounded) |
| Hiring Algorithm | Dev-AC | 0.77 | 0.7714 | YES (rounded) |
| Hiring Algorithm | Reg-AC | 0.54 | 0.5429 | YES (rounded) |
| Healthcare | Dev-Reg | -0.14 | -0.1429 | YES (rounded) |
| Healthcare | Dev-AC | 0.49 | 0.4857 | YES (rounded) |
| Healthcare | Reg-AC | 0.03 | 0.0286 | YES (rounded) |

**Baseline Dimension Scores — All match JSON files exactly.**

**Cross-Case Table (Table 11.11):**

| Case | Report Overall | Verified Overall | Report Risk | Verified Risk |
|------|---------------|-----------------|-------------|---------------|
| Facial Recognition | 0.34 | 0.3379 (eu_altai) | Critical | Critical |
| Hiring Algorithm | 0.30 | 0.3022 (eu_altai) | Critical | Critical |
| Healthcare | 0.58 | 0.5841 (eu_altai) | High | High |

## Risk Classification

### CRITICAL ISSUES
1. **Table structure mismatch**: Report shows per-stakeholder scores but API returns overall scores per framework. The per-stakeholder breakdown is fabricated or from an earlier API version. Must restructure tables to match actual API output.
2. **Risk level discrepancy for Case 1**: Report says "High Risk" but API returns "Critical" for eu_altai and sg_mgaf.
3. **Risk level discrepancy for Case 3**: Report says "Medium Risk" but API returns "High" for eu_altai and sg_mgaf.

### MODERATE ISSUES
4. **Normalized scores in baseline tables**: The normalized values (e.g., 0.250 for 2.5) use formula (x-1)/6, which should be verified against the code's normalization function.
5. **Cross-case overall scores**: Report uses approximate values that are close but not exact.

### LOW ISSUES
6. **Conflict matrix values**: All match API output when rounded to 2 decimal places. Acceptable.
7. **Baseline dimension scores**: All match JSON files exactly. No issues.

## Other Chapters — Risk Assessment

Chapters 1-10 and 12-14 need review for:
- Architecture descriptions matching the actual codebase
- Algorithm descriptions matching the implementation
- Screenshot accuracy
- Reference authenticity
- Formatting compliance with NTU guidelines
