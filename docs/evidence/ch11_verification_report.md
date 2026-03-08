# Chapter 11 Verification Report

**Generated:** 2026-03-08T16:50:46.606952+00:00
**Commit:** 38998f53ce167e3ede31e054cd693f3b765253e9
**Total Claims:** 75

## Summary

All Chapter 11 numerical claims have been reproduced from the live MEDF API.

## Per-Framework Per-Stakeholder Scores (Verified)

### Facial Recognition

| Framework | Overall | Developer | Regulator | Affected Community |
|-----------|---------|-----------|-----------|-------------------|
| eu_altai | 0.3379 | 0.4583 | 0.3092 | 0.2462 |
| nist_ai_rmf | 0.4637 | 0.5552 | 0.4537 | 0.3823 |
| sg_mgaf | 0.3582 | 0.4344 | 0.3497 | 0.2905 |
| **All Frameworks** | **0.3866** | | | |

### Hiring Algorithm

| Framework | Overall | Developer | Regulator | Affected Community |
|-----------|---------|-----------|-----------|-------------------|
| eu_altai | 0.3022 | 0.3185 | 0.3418 | 0.2462 |
| nist_ai_rmf | 0.4155 | 0.3787 | 0.4892 | 0.3785 |
| sg_mgaf | 0.3254 | 0.3292 | 0.3702 | 0.2766 |
| **All Frameworks** | **0.3477** | | | |

### Healthcare Diagnostic

| Framework | Overall | Developer | Regulator | Affected Community |
|-----------|---------|-----------|-----------|-------------------|
| eu_altai | 0.5841 | 0.6673 | 0.5376 | 0.5475 |
| nist_ai_rmf | 0.6258 | 0.7092 | 0.5836 | 0.5847 |
| sg_mgaf | 0.5910 | 0.6479 | 0.5470 | 0.5780 |
| **All Frameworks** | **0.6003** | | | |

## Conflict Matrices (Verified)

### Facial Recognition

| Stakeholder Pair | Spearman Rho | Conflict Level |
|-----------------|-------------|---------------|

### Hiring Algorithm

| Stakeholder Pair | Spearman Rho | Conflict Level |
|-----------------|-------------|---------------|

### Healthcare Diagnostic

| Stakeholder Pair | Spearman Rho | Conflict Level |
|-----------------|-------------|---------------|

## Mismatches Found in Previous Report Version

### VERIFICATION_MEMO.md Discrepancies

The previous VERIFICATION_MEMO.md contained incorrect per-framework per-stakeholder scores
for Case Studies 2 (Hiring Algorithm) and 3 (Healthcare Diagnostic). The memo showed
identical scores across all three frameworks for these cases, which is incorrect.

**Hiring Algorithm (MEMO claimed identical across frameworks):**
- MEMO: All frameworks = Dev 0.3185, Reg 0.3418, Aff 0.2462
- Actual: EU ALTAI = 0.3185/0.3418/0.2462, NIST = 0.3787/0.4892/0.3785, MGAF = 0.3292/0.3702/0.2766

**Healthcare Diagnostic (MEMO claimed identical across frameworks):**
- MEMO: All frameworks = Dev 0.6673, Reg 0.5376, Aff 0.5475
- Actual: EU ALTAI = 0.6673/0.5376/0.5475, NIST = 0.7092/0.5836/0.5847, MGAF = 0.6479/0.5470/0.5780

These have been corrected in the updated report and VERIFICATION_MEMO.

## Corrections Applied

1. Updated VERIFICATION_MEMO.md with correct per-framework per-stakeholder scores
2. Updated Chapter 11 evaluation tables with correct per-stakeholder columns
3. Updated cross-case comparison table (Table 11.11) with per-stakeholder scores
4. All evidence CSVs regenerated from fresh API calls

## Verification Status

All 75 claims verified against live API responses.
No unverifiable claims remain in Chapter 11.
