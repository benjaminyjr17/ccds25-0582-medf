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

    # Facial recognition synthetic hand-verification profile (Likert 1-7 scale).
    dimension_scores = {
        "transparency_explainability": 2.5,
        "fairness_nondiscrimination": 2.5,
        "safety_robustness": 4.0,
        "privacy_data_governance": 2.5,
        "human_agency_oversight": 4.0,
        "accountability": 5.5,
    }

    result = compute_scores(dimension_scores, weights, method="topsis")
    overall = float(result["overall_score"])

    assert abs(overall - 0.4469) <= 0.05
