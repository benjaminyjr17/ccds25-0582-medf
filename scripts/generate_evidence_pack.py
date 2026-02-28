from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any
import sys


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS

CASE_STUDY_FILES: tuple[str, ...] = (
    "facial_recognition.json",
    "hiring_algorithm.json",
    "healthcare_diagnostic.json",
)
EVIDENCE_DIR = ROOT / "docs" / "evidence"
SUMMARY_CSV = EVIDENCE_DIR / "evaluation_summary.csv"
BUNDLE_JSON = EVIDENCE_DIR / "evaluation_bundle.json"


def _load_case_studies() -> list[dict[str, Any]]:
    case_dir = ROOT / "case_studies"
    out: list[dict[str, Any]] = []
    for file_name in CASE_STUDY_FILES:
        path = case_dir / file_name
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Case study '{path}' must be a JSON object.")
        out.append(payload)
    return out


def _extract_top_consensus_dimension(pareto_json: dict[str, Any]) -> str:
    solutions = pareto_json.get("pareto_solutions")
    if not isinstance(solutions, list) or not solutions:
        return ""
    top = solutions[0]
    if not isinstance(top, dict):
        return ""
    weights = top.get("weights")
    if not isinstance(weights, dict):
        return ""
    consensus = weights.get("consensus")
    if not isinstance(consensus, dict) or not consensus:
        return ""
    best = max(consensus.items(), key=lambda item: float(item[1]))
    return str(best[0])


def _mean_rho(conflicts_json: dict[str, Any]) -> float:
    conflicts = conflicts_json.get("conflicts")
    if not isinstance(conflicts, list) or not conflicts:
        return 1.0
    rho_values: list[float] = []
    for item in conflicts:
        if isinstance(item, dict) and isinstance(item.get("spearman_rho"), (int, float)):
            rho_values.append(float(item["spearman_rho"]))
    if not rho_values:
        return 1.0
    return float(mean(rho_values))


def _require_ok(response, *, context: str) -> dict[str, Any]:
    if response.status_code != 200:
        raise RuntimeError(
            f"{context} failed: status={response.status_code} body={response.text[:1000]}"
        )
    payload = response.json()
    if not isinstance(payload, dict) and context != "GET /api/frameworks" and context != "GET /api/stakeholders":
        raise RuntimeError(f"{context} returned non-object payload.")
    return payload


def generate() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    cases = _load_case_studies()
    bundle: dict[str, Any] = {
        "meta": {
            "generator": "scripts/generate_evidence_pack.py",
            "framework_count": 0,
            "case_count": len(cases),
            "stakeholder_ids": ["developer", "regulator", "affected_community"],
        },
        "rows": [],
    }
    rows_for_csv: list[dict[str, Any]] = []

    with TestClient(app) as client:
        frameworks_resp = client.get("/api/frameworks")
        if frameworks_resp.status_code != 200:
            raise RuntimeError(
                f"GET /api/frameworks failed: status={frameworks_resp.status_code} body={frameworks_resp.text[:800]}"
            )
        frameworks_json = frameworks_resp.json()
        if not isinstance(frameworks_json, list) or not frameworks_json:
            raise RuntimeError("GET /api/frameworks returned empty payload.")

        stakeholders_resp = client.get("/api/stakeholders")
        if stakeholders_resp.status_code != 200:
            raise RuntimeError(
                f"GET /api/stakeholders failed: status={stakeholders_resp.status_code} body={stakeholders_resp.text[:800]}"
            )
        stakeholders_json = stakeholders_resp.json()
        if not isinstance(stakeholders_json, list) or not stakeholders_json:
            raise RuntimeError("GET /api/stakeholders returned empty payload.")

        stakeholder_ids = ["developer", "regulator", "affected_community"]
        by_id = {
            str(item.get("id")): item
            for item in stakeholders_json
            if isinstance(item, dict) and item.get("id")
        }
        weights_payload: dict[str, dict[str, float]] = {}
        for stakeholder_id in stakeholder_ids:
            stakeholder = by_id.get(stakeholder_id)
            if not isinstance(stakeholder, dict):
                raise RuntimeError(f"Missing stakeholder '{stakeholder_id}' from /api/stakeholders.")
            raw_weights = stakeholder.get("weights")
            if not isinstance(raw_weights, dict):
                raise RuntimeError(f"Stakeholder '{stakeholder_id}' has invalid weights payload.")
            weights_payload[stakeholder_id] = {
                dimension: float(raw_weights[dimension])
                for dimension in UNIFIED_DIMENSIONS
            }

        framework_ids = [str(item["id"]) for item in frameworks_json if isinstance(item, dict) and item.get("id")]
        bundle["meta"]["framework_count"] = len(framework_ids)

        for case in cases:
            case_id = str(case.get("id", "")).strip()
            case_name = str(case.get("name", "")).strip()
            case_desc = str(case.get("description", "")).strip()
            raw_scores = case.get("dimension_scores")
            if not isinstance(raw_scores, dict):
                raise RuntimeError(f"Case '{case_id}' missing dimension_scores.")
            score_map = {dimension: float(raw_scores[dimension]) for dimension in UNIFIED_DIMENSIONS}

            for framework_id in framework_ids:
                evaluate_payload = {
                    "ai_system": {
                        "id": f"evidence_{case_id}",
                        "name": case_name,
                        "description": case_desc,
                        "context": {"dimension_scores": score_map},
                    },
                    "framework_ids": [framework_id],
                    "stakeholder_ids": stakeholder_ids,
                    "weights": weights_payload,
                    "scoring_method": "topsis",
                }
                conflicts_payload = {
                    "ai_system": {
                        "id": f"evidence_{case_id}",
                        "name": case_name,
                        "description": case_desc,
                        "context": {"dimension_scores": score_map},
                    },
                    "framework_ids": [framework_id],
                    "stakeholder_ids": stakeholder_ids,
                }
                pareto_payload = {
                    "ai_system": {
                        "id": f"evidence_{case_id}",
                        "name": case_name,
                        "description": case_desc,
                        "context": {"dimension_scores": score_map},
                    },
                    "framework_ids": [framework_id],
                    "stakeholder_ids": stakeholder_ids,
                    "n_solutions": 8,
                    "pop_size": 40,
                    "n_gen": 80,
                    "seed": 42,
                    "deterministic_mode": True,
                }

                evaluate_json = _require_ok(
                    client.post("/api/evaluate", json=evaluate_payload),
                    context=f"POST /api/evaluate [{case_id}/{framework_id}]",
                )
                conflicts_json = _require_ok(
                    client.post("/api/conflicts", json=conflicts_payload),
                    context=f"POST /api/conflicts [{case_id}/{framework_id}]",
                )
                pareto_json = _require_ok(
                    client.post("/api/pareto", json=pareto_payload),
                    context=f"POST /api/pareto [{case_id}/{framework_id}]",
                )

                overall_score = float(evaluate_json.get("overall_score", 0.0))
                conflict_count = len(conflicts_json.get("conflicts", [])) if isinstance(conflicts_json.get("conflicts"), list) else 0
                pareto_count = len(pareto_json.get("pareto_solutions", [])) if isinstance(pareto_json.get("pareto_solutions"), list) else 0
                rho_mean = _mean_rho(conflicts_json)
                top_consensus_dimension = _extract_top_consensus_dimension(pareto_json)

                row = {
                    "case_id": case_id,
                    "framework_id": framework_id,
                    "overall_score": round(overall_score, 6),
                    "conflict_pairs": conflict_count,
                    "mean_spearman_rho": round(rho_mean, 6),
                    "pareto_solutions": pareto_count,
                    "top_consensus_dimension": top_consensus_dimension,
                }
                rows_for_csv.append(row)
                bundle["rows"].append(
                    {
                        "summary": row,
                        "evaluate": evaluate_json,
                        "conflicts": conflicts_json,
                        "pareto": pareto_json,
                    }
                )

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "framework_id",
                "overall_score",
                "conflict_pairs",
                "mean_spearman_rho",
                "pareto_solutions",
                "top_consensus_dimension",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_for_csv)

    with BUNDLE_JSON.open("w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2, sort_keys=True)

    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {BUNDLE_JSON}")


if __name__ == "__main__":
    generate()
