from __future__ import annotations

from app.harm_assessment import _severity, build_harm_assessment
from app.models import HarmSeverity, UNIFIED_DIMENSIONS


def _uniform_weights() -> dict[str, float]:
    return {dimension: 1.0 / len(UNIFIED_DIMENSIONS) for dimension in UNIFIED_DIMENSIONS}


def test_harm_assessment_outputs_expected_shape_and_bounds() -> None:
    dimension_scores = {dimension: 4.0 for dimension in UNIFIED_DIMENSIONS}
    stakeholder_weights = {
        "developer": _uniform_weights(),
        "regulator": _uniform_weights(),
        "affected_community": _uniform_weights(),
    }
    framework_weights = _uniform_weights()

    result = build_harm_assessment(
        dimension_scores=dimension_scores,
        stakeholder_weights=stakeholder_weights,
        framework_weights=framework_weights,
    )

    assert 0.0 <= float(result.overall_score) <= 1.0
    assert len(result.domain_scores) == len(UNIFIED_DIMENSIONS)
    assert set(result.top_risk_domains).issubset(set(UNIFIED_DIMENSIONS))
    assert result.model_version == "harm_taxonomy_v1"

    seen_dimensions: set[str] = set()
    for item in result.domain_scores:
        seen_dimensions.add(item.unified_dimension)
        assert 0.0 <= float(item.score) <= 1.0
        assert item.severity in {
            HarmSeverity.LOW,
            HarmSeverity.MODERATE,
            HarmSeverity.HIGH,
            HarmSeverity.CRITICAL,
        }
    assert seen_dimensions == set(UNIFIED_DIMENSIONS)


def test_harm_assessment_is_deterministic_for_same_inputs() -> None:
    dimension_scores = {
        "transparency_explainability": 2.5,
        "fairness_nondiscrimination": 2.0,
        "safety_robustness": 5.5,
        "privacy_data_governance": 2.0,
        "human_agency_oversight": 3.0,
        "accountability": 4.0,
    }
    stakeholder_weights = {
        "developer": {
            "transparency_explainability": 0.10,
            "fairness_nondiscrimination": 0.15,
            "safety_robustness": 0.30,
            "privacy_data_governance": 0.15,
            "human_agency_oversight": 0.15,
            "accountability": 0.15,
        },
        "regulator": {
            "transparency_explainability": 0.20,
            "fairness_nondiscrimination": 0.20,
            "safety_robustness": 0.10,
            "privacy_data_governance": 0.15,
            "human_agency_oversight": 0.10,
            "accountability": 0.25,
        },
    }
    framework_weights = _uniform_weights()

    first = build_harm_assessment(
        dimension_scores=dimension_scores,
        stakeholder_weights=stakeholder_weights,
        framework_weights=framework_weights,
    )
    second = build_harm_assessment(
        dimension_scores=dimension_scores,
        stakeholder_weights=stakeholder_weights,
        framework_weights=framework_weights,
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_harm_severity_thresholds_are_stable() -> None:
    assert _severity(0.10) == HarmSeverity.LOW
    assert _severity(0.30) == HarmSeverity.MODERATE
    assert _severity(0.60) == HarmSeverity.HIGH
    assert _severity(0.90) == HarmSeverity.CRITICAL
