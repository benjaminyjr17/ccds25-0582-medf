# Verification Memo and Changelog

**Project:** CCDS25-0582 Multi-Stakeholder Ethical Decision-Making Frameworks for AI Systems  
**Author:** Benjamin Oliver Yick (U2120984H)  
**Date:** 7 March 2026  

---

## 1. Verification Process

This memo documents the systematic verification process applied to the revised FYP report. The verification was conducted in six phases, each targeting a specific category of potential errors or inconsistencies.

### Phase 0: Source Discovery

The GitHub repository (`benjaminyjr17/ccds25-0582-medf`) was cloned and all source files were catalogued. No LaTeX source files were found in the repository; the original report existed only as a compiled PDF. Consequently, the entire LaTeX thesis was created from scratch, faithfully reproducing and correcting the content of the original PDF.

### Phase 1: Report-to-Code Verification

Every technical claim in the report was cross-referenced against the actual source code. The following discrepancies were identified and corrected:

| Item | Original Report | Actual Code | Action Taken |
|------|----------------|-------------|--------------|
| Project Number | CCDS25-0323 (throughout) | CCDS25-0582 | Corrected to CCDS25-0582 in all locations |
| Stakeholder Weights (Table 11.1) | Developer Safety=0.25, Regulator Accountability=0.20, etc. | Developer Safety=0.30, Regulator Accountability=0.25, etc. | Corrected Table 11.1 to match `framework_registry.py` |
| Conflict Detection | Described as computing Spearman rho between "score contribution vectors" | Code computes both weights-only and contribution-based correlations | Clarified dual conflict analysis in Chapter 11 |

### Phase 2: Score Reproduction

All three case studies were independently reproduced by running the MEDF scoring engine against the case study JSON files. The reproduced scores were used to update all evaluation result tables in Chapter 11.

### Phase 3: Reference Audit

All 13 original references were verified against their original sources. One citation was found to be incorrect:

| Ref | Original Title | Correct Title | Action |
|-----|---------------|---------------|--------|
| [2] Floridi 2018 | "AI and its new challenges for human rights" | "AI4People: An Ethical Framework for a Good AI Society" | Corrected title, added full author list and DOI |

The reference list was expanded from 13 to 27 entries, adding foundational works on stakeholder theory (Freeman 1984, Mitchell et al. 1997), MCDM methods (Saaty 1980, Behzadian et al. 2012), AI governance (Jobin et al. 2019, Mittelstadt 2019, Hagendorff 2020, Smuha 2019), algorithmic fairness (Buolamwini and Gebru 2018), and software engineering for ML (Amershi et al. 2019).

### Phase 4: Application Testing

The MEDF application was successfully installed and run locally. Both the FastAPI backend (port 8000) and Streamlit frontend (port 8501) were started. All three case studies were executed through the UI, and the results were verified against the reproduced scores.

### Phase 5: Wording Normalization

The following terminology was standardized throughout the report:

| Before | After | Rationale |
|--------|-------|-----------|
| CCDS25-0323 | CCDS25-0582 | Correct project number |
| "ALTAI" / "EU ALTAI" / "the ALTAI" | "ALTAI" (consistently) | Standardized framework name |
| "NIST RMF" / "AI RMF" / "NIST AI RMF" | "NIST AI RMF" (consistently) | Standardized framework name |
| "Singapore MGAF" / "MGAF" / "the MGAF" | "MGAF" (consistently) | Standardized framework name |
| "affected community" / "Affected Community" | "Affected Community" (capitalized when referring to the stakeholder role) | Consistent capitalization |

---

## 2. Summary of Changes

### Critical Corrections
1. **Project number** corrected from CCDS25-0323 to CCDS25-0582 throughout all pages and headers.
2. **Stakeholder weight table** corrected to match actual source code values.
3. **Reference [2]** corrected from wrong title to correct Floridi et al. (2018) AI4People paper.

### Structural Improvements
4. **LaTeX source created from scratch** with proper NTU CCDS formatting, including cover page with NTU logo, running headers, and professional typography.
5. **Three appendices added:** API Reference (Appendix A), Framework YAML Definitions (Appendix B), and Verification Memo (Appendix C).
6. **TikZ diagrams created** for system architecture (Figure 7.1), module diagram (Figure 7.2), stakeholder decision flow (Figure 6.1), scoring aggregation process (Figure 8.1), and end-to-end evaluation pipeline (Figure 8.2).

### Content Enhancements
7. **References expanded** from 13 to 27 verified entries.
8. **Literature review strengthened** with additional citations to Jobin et al. (2019), Mittelstadt (2019), Hagendorff (2020), Freeman (1984), Mitchell et al. (1997), Behzadian et al. (2012), and others.
9. **Case study evaluation tables updated** with scores reproduced from actual code execution.
10. **Cross-case comparison table corrected** with accurate overall scores and risk levels.
11. **Conflict analysis clarified** to distinguish between weights-only and contribution-based correlation matrices.

### Formatting and Style
12. **Professional LaTeX formatting** with booktabs tables, proper mathematical typesetting, numbered equations, and consistent use of `\enquote{}` for quotations.
13. **Running header** displays correct project number and title on every page.
14. **Table of Contents, List of Figures, and List of Tables** automatically generated.
15. **IEEE-style bibliography** with proper formatting via biblatex.

---

## 3. Deliverables

| Deliverable | Location | Description |
|-------------|----------|-------------|
| Compiled PDF | `thesis/main.pdf` | 67-page final report |
| LaTeX source | `thesis/main.tex` | Main document file |
| Chapter files | `thesis/chapters/*.tex` | 14 chapters + 3 appendices |
| Bibliography | `thesis/references.bib` | 27 verified references |
| NTU Logo | `thesis/figures/ntu_logo.png` | Cover page logo |
| This memo | `thesis/VERIFICATION_MEMO.md` | Verification documentation |
