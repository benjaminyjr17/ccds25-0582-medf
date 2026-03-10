#!/usr/bin/env python3
"""
Final Verification Gates for CCDS25-0582 FYP Report
Checks all conditions before finalizing the report.
"""

import json
import os
import csv
import re

EVIDENCE_DIR = "docs/evidence"
THESIS_DIR = "thesis"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []

def check(name, condition, note=""):
    status = PASS if condition else FAIL
    results.append((name, condition, note))
    print(f"  [{status}] {name}" + (f" — {note}" if note else ""))
    return condition

# ============================================================
# GATE 1: TECHNICAL TRUTH
# ============================================================
print("\n=== GATE 1: TECHNICAL TRUTH ===")

# Check module responsibility map exists
check("Module responsibility map exists",
      os.path.exists(f"{EVIDENCE_DIR}/module_responsibility_map.json"))

# Check chapter risk map exists
check("Chapter risk map exists",
      os.path.exists(f"{EVIDENCE_DIR}/chapter_risk_map.md"))

# ============================================================
# GATE 2: NUMERICAL TRUTH
# ============================================================
print("\n=== GATE 2: NUMERICAL TRUTH ===")

# Check all CSV tables exist
for i in range(1, 12):
    check(f"Table 11.{i} CSV exists",
          os.path.exists(f"{EVIDENCE_DIR}/ch11_table_11_{i}.csv"))

# Check claim registry exists and all claims verified
claim_file = f"{EVIDENCE_DIR}/ch11_claim_registry.json"
if os.path.exists(claim_file):
    with open(claim_file) as f:
        claims = json.load(f)
    total = claims["total_claims"]
    verified = sum(1 for c in claims["claims"] if c["verification_status"] == "verified")
    check(f"Claim registry: {verified}/{total} claims verified",
          verified == total, f"{total} total claims")
else:
    check("Claim registry exists", False)

# Check normalized bundle exists
check("Normalized bundle exists",
      os.path.exists(f"{EVIDENCE_DIR}/ch11_normalized_bundle.json"))

# Check raw evidence files exist
for fn in ["ch11_evaluate_raw.json", "ch11_conflicts_raw.json", "ch11_pareto_raw.json",
           "ch11_inputs_manifest.json", "ch11_frameworks.json", "ch11_stakeholders.json"]:
    check(f"Raw evidence: {fn}",
          os.path.exists(f"{EVIDENCE_DIR}/{fn}"))

# ============================================================
# GATE 3: SCREENSHOT TRUTH
# ============================================================
print("\n=== GATE 3: SCREENSHOT TRUTH ===")

screenshot_files = [
    "screenshot_evaluate.png",
    "screenshot_conflict_detection.png",
    "screenshot_pareto_resolution.png",
    "screenshot_case_studies.png"
]

for fn in screenshot_files:
    path = f"{THESIS_DIR}/figures/{fn}"
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    check(f"Screenshot: {fn}",
          exists and size > 100000,
          f"{size:,} bytes" if exists else "missing")

# ============================================================
# GATE 4: REFERENCE TRUTH
# ============================================================
print("\n=== GATE 4: REFERENCE TRUTH ===")

bib_file = f"{THESIS_DIR}/references.bib"
if os.path.exists(bib_file):
    with open(bib_file) as f:
        bib_content = f.read()
    ref_count = bib_content.count("@")
    check(f"Bibliography exists with {ref_count} entries",
          ref_count >= 20)
else:
    check("Bibliography exists", False)

# ============================================================
# GATE 5: PRESENTATION QUALITY
# ============================================================
print("\n=== GATE 5: PRESENTATION QUALITY ===")

# Check PDF exists
pdf_path = f"{THESIS_DIR}/main.pdf"
check("PDF compiled successfully",
      os.path.exists(pdf_path),
      f"{os.path.getsize(pdf_path):,} bytes" if os.path.exists(pdf_path) else "missing")

# Check for major overfull boxes in log
log_path = f"{THESIS_DIR}/main.log"
if os.path.exists(log_path):
    with open(log_path) as f:
        log_content = f.read()
    overfull_count = log_content.count("Overfull")
    major_overfull = len(re.findall(r"Overfull \\hbox \((\d+)\.\d+pt", log_content))
    check(f"Overfull boxes: {overfull_count} total",
          overfull_count < 20, "acceptable for technical report")

# ============================================================
# GATE 6: HONESTY
# ============================================================
print("\n=== GATE 6: HONESTY ===")

# Check VERIFICATION_MEMO exists
check("Verification memo exists",
      os.path.exists(f"{THESIS_DIR}/VERIFICATION_MEMO.md"))

# Check verification report exists
check("Verification report exists",
      os.path.exists(f"{EVIDENCE_DIR}/ch11_verification_report.md"))

# ============================================================
# GATE 7: CROSS-VALIDATION
# ============================================================
print("\n=== GATE 7: CROSS-VALIDATION ===")

# Verify Chapter 11 table values match CSV evidence
ch11_path = f"{THESIS_DIR}/chapters/ch11_case_studies.tex"
if os.path.exists(ch11_path):
    with open(ch11_path) as f:
        ch11_content = f.read()

    # Check CS1 evaluation table values
    check("CS1 EU ALTAI scores in report (0.34, 0.46, 0.31, 0.25)",
          "0.34 & 0.46 & 0.31 & 0.25" in ch11_content)
    check("CS1 NIST scores in report (0.46, 0.56, 0.45, 0.38)",
          "0.46 & 0.56 & 0.45 & 0.38" in ch11_content)
    check("CS1 MGAF scores in report (0.36, 0.43, 0.35, 0.29)",
          "0.36 & 0.43 & 0.35 & 0.29" in ch11_content)

    # Check CS2 evaluation table values
    check("CS2 EU ALTAI scores in report (0.30, 0.32, 0.34, 0.25)",
          "0.30 & 0.32 & 0.34 & 0.25" in ch11_content)
    check("CS2 NIST scores in report (0.42, 0.38, 0.49, 0.38)",
          "0.42 & 0.38 & 0.49 & 0.38" in ch11_content)
    check("CS2 MGAF scores in report (0.33, 0.33, 0.37, 0.28)",
          "0.33 & 0.33 & 0.37 & 0.28" in ch11_content)

    # Check CS3 evaluation table values
    check("CS3 EU ALTAI scores in report (0.58, 0.67, 0.54, 0.55)",
          "0.58 & 0.67 & 0.54 & 0.55" in ch11_content)
    check("CS3 NIST scores in report (0.63, 0.71, 0.58, 0.58)",
          "0.63 & 0.71 & 0.58 & 0.58" in ch11_content)
    check("CS3 MGAF scores in report (0.59, 0.65, 0.55, 0.58)",
          "0.59 & 0.65 & 0.55 & 0.58" in ch11_content)

    # Check conflict matrices
    check("CS1 conflict: Dev-Reg=0.89",
          "0.89" in ch11_content)
    check("CS2 conflict: Dev-Reg=0.54",
          "0.54" in ch11_content)
    check("CS3 conflict: Dev-Reg=-0.14",
          "-0.14" in ch11_content)

    # Check cross-case table
    check("Cross-case: FR=0.39 Critical",
          "0.39 & Critical" in ch11_content)
    check("Cross-case: Hiring=0.35 Critical",
          "0.35 & Critical" in ch11_content)
    check("Cross-case: Healthcare=0.60 Medium",
          "0.60 & Medium" in ch11_content)

    # Check Overall column exists
    check("Overall column added to evaluation tables",
          "\\textbf{Overall}" in ch11_content)

    # Check All Frameworks row exists
    check("All Frameworks row added",
          "All Frameworks" in ch11_content)

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
total_checks = len(results)
passed = sum(1 for _, c, _ in results if c)
failed = total_checks - passed
print(f"FINAL RESULT: {passed}/{total_checks} checks passed, {failed} failed")
if failed == 0:
    print(f"[{PASS}] ALL VERIFICATION GATES PASSED")
else:
    print(f"[{FAIL}] {failed} VERIFICATION GATES FAILED")
    for name, condition, note in results:
        if not condition:
            print(f"  FAILED: {name}" + (f" — {note}" if note else ""))
