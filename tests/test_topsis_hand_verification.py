from __future__ import annotations

from app.scoring_engine import compute_scores


def test_topsis_developer_facial_recognition_reference() -> None:
    # Developer stakeholder weights (Stage 1C defaults).
    weights = {
        "transparency_explainability": 0.10,
        "fairness_nondiscrimination": 0.15,
        "safety_robustness": 0.30,
        "privacy_data_governance": 0.15,
        "human_agency_oversight": 0.15,
        "accountability": 0.15,
    }

    # Facial recognition synthetic hand-verification profile (1-5 scale).
    dimension_scores = {
        "transparency_explainability": 2.0,
        "fairness_nondiscrimination": 2.0,
        "safety_robustness": 3.0,
        "privacy_data_governance": 2.0,
        "human_agency_oversight": 3.0,
        "accountability": 4.0,
    }

    result = compute_scores(dimension_scores, weights, method="topsis")
    overall = float(result["overall_score"])

    assert abs(overall - 0.4469) <= 0.05
