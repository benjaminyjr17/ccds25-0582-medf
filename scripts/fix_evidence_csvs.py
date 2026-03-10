#!/usr/bin/env python3
"""Fix evidence CSVs with correct conflict matrix data and per-stakeholder scores."""
import json, csv

EVIDENCE_DIR = "docs/evidence"

# Load the raw conflicts data
with open(f"{EVIDENCE_DIR}/ch11_conflicts_raw.json") as f:
    conflicts_data = json.load(f)

# Build a lookup: case_id -> {pair -> rho}
conflict_lookup = {}
for entry in conflicts_data["cases"]:
    case_id = entry["case_id"]
    fw_id = entry["framework_id"]
    if fw_id != "eu_altai":
        continue  # Use eu_altai as primary

    meta = entry["raw_response"].get("metadata", {})
    corr_matrix = meta.get("correlation_matrix", {})

    conflict_lookup[case_id] = {}
    pairs = [("developer", "regulator"), ("developer", "affected_community"), ("regulator", "affected_community")]
    for sh1, sh2 in pairs:
        rho = corr_matrix.get(sh1, {}).get(sh2, 0.0)
        conflict_lookup[case_id][(sh1, sh2)] = rho

# Fix conflict CSV tables
case_table_nums = {
    "facial_recognition": 4,
    "hiring_algorithm": 7,
    "healthcare_diagnostic": 10
}

for case_id, table_num in case_table_nums.items():
    with open(f"{EVIDENCE_DIR}/ch11_table_11_{table_num}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Stakeholder Pair", "Spearman Rho", "Conflict Level"])

        pairs = [("developer", "regulator"), ("developer", "affected_community"), ("regulator", "affected_community")]
        for sh1, sh2 in pairs:
            rho = conflict_lookup[case_id][(sh1, sh2)]
            if rho >= 0.7:
                level = "low"
            elif rho >= 0.3:
                level = "moderate"
            else:
                level = "high"
            w.writerow([f"{sh1} vs {sh2}", f"{rho:.4f}", level])
    print(f"Fixed ch11_table_11_{table_num}.csv ({case_id} conflicts)")

# Fix evaluation tables to include per-stakeholder scores
with open(f"{EVIDENCE_DIR}/ch11_evaluate_raw.json") as f:
    eval_data = json.load(f)

FRAMEWORK_ORDER = ["eu_altai", "nist_ai_rmf", "sg_mgaf"]
STAKEHOLDER_ORDER = ["developer", "regulator", "affected_community"]
CASE_ORDER = ["facial_recognition", "hiring_algorithm", "healthcare_diagnostic"]

eval_table_nums = {
    "facial_recognition": 3,
    "hiring_algorithm": 6,
    "healthcare_diagnostic": 9
}

for case_entry in eval_data["cases"]:
    case_id = case_entry["case_id"]
    table_num = eval_table_nums[case_id]

    # Build per-stakeholder lookup
    per_sh = {}
    for pse in case_entry["per_stakeholder_evaluations"]:
        key = (pse["framework_id"], pse["stakeholder_id"])
        per_sh[key] = pse["overall_score"]

    with open(f"{EVIDENCE_DIR}/ch11_table_11_{table_num}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Framework", "Overall Score", "Risk Level", "Developer", "Regulator", "Affected Community"])

        for eval_entry in case_entry["overall_evaluations"]:
            fw_id = eval_entry["framework_id"]
            overall = eval_entry["raw_response"]["overall_score"]

            if overall >= 0.80:
                risk = "low"
            elif overall >= 0.60:
                risk = "medium"
            elif overall >= 0.40:
                risk = "high"
            else:
                risk = "critical"

            dev = per_sh.get((fw_id, "developer"), 0)
            reg = per_sh.get((fw_id, "regulator"), 0)
            aff = per_sh.get((fw_id, "affected_community"), 0)

            w.writerow([fw_id, f"{overall:.4f}", risk, f"{dev:.4f}", f"{reg:.4f}", f"{aff:.4f}"])

    print(f"Fixed ch11_table_11_{table_num}.csv ({case_id} evaluation)")

# Fix cross-case comparison table 11.11
with open(f"{EVIDENCE_DIR}/ch11_table_11_11.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Case Study", "Framework", "Overall Score", "Risk Level",
                "Dev Score", "Reg Score", "Aff Score",
                "Highest Conflict Pair", "Highest Conflict Rho"])

    case_names = {
        "facial_recognition": "Facial Recognition",
        "hiring_algorithm": "Hiring Algorithm",
        "healthcare_diagnostic": "Healthcare Diagnostic"
    }

    for case_entry in eval_data["cases"]:
        case_id = case_entry["case_id"]

        per_sh = {}
        for pse in case_entry["per_stakeholder_evaluations"]:
            key = (pse["framework_id"], pse["stakeholder_id"])
            per_sh[key] = pse["overall_score"]

        for eval_entry in case_entry["overall_evaluations"]:
            fw_id = eval_entry["framework_id"]
            overall = eval_entry["raw_response"]["overall_score"]

            if overall >= 0.80:
                risk = "low"
            elif overall >= 0.60:
                risk = "medium"
            elif overall >= 0.40:
                risk = "high"
            else:
                risk = "critical"

            dev = per_sh.get((fw_id, "developer"), 0)
            reg = per_sh.get((fw_id, "regulator"), 0)
            aff = per_sh.get((fw_id, "affected_community"), 0)

            # Get conflict info
            conflicts = conflict_lookup.get(case_id, {})
            min_rho = 1.0
            min_pair = "N/A"
            for (sh1, sh2), rho in conflicts.items():
                if rho < min_rho:
                    min_rho = rho
                    min_pair = f"{sh1} vs {sh2}"

            w.writerow([case_names[case_id], fw_id, f"{overall:.4f}", risk,
                       f"{dev:.4f}", f"{reg:.4f}", f"{aff:.4f}",
                       min_pair, f"{min_rho:.4f}"])

print("Fixed ch11_table_11_11.csv (cross-case comparison)")

# Also update the normalized bundle with correct conflict data
with open(f"{EVIDENCE_DIR}/ch11_normalized_bundle.json") as f:
    bundle = json.load(f)

for case_id in CASE_ORDER:
    if case_id in bundle["cases"]:
        for entry in conflicts_data["cases"]:
            if entry["case_id"] == case_id:
                fw_id = entry["framework_id"]
                meta = entry["raw_response"].get("metadata", {})
                corr_matrix = meta.get("correlation_matrix", {})
                bundle["cases"][case_id]["conflict_matrices"][fw_id] = {
                    "raw_matrix": corr_matrix,
                    "source_trace": {
                        "artifact": f"{EVIDENCE_DIR}/ch11_conflicts_raw.json",
                        "case_id": case_id,
                        "framework_id": fw_id,
                        "endpoint": "/api/conflicts",
                        "json_path": "$.raw_response.metadata.correlation_matrix"
                    }
                }

with open(f"{EVIDENCE_DIR}/ch11_normalized_bundle.json", "w") as f:
    json.dump(bundle, f, indent=2)

print("\nAll evidence CSVs and normalized bundle fixed.")
