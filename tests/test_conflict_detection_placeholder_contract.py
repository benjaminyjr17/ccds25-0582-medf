from __future__ import annotations

from app.conflict_detection import (
    build_conflict_matrix,
    compute_pairwise_spearman,
    detect_framework_conflicts,
    detect_stakeholder_conflicts,
    find_divergent_dimensions,
    find_pareto_solutions,
)


def test_placeholder_compute_pairwise_spearman_contract() -> None:
    rho, pvalue = compute_pairwise_spearman(["a", "b", "c"], ["c", "b", "a"])
    assert rho == 0.0
    assert pvalue == 1.0


def test_placeholder_find_divergent_dimensions_contract() -> None:
    result = find_divergent_dimensions(
        {"fairness_nondiscrimination": 0.9},
        {"fairness_nondiscrimination": 0.1},
        threshold=0.25,
    )
    assert result == []


def test_placeholder_find_pareto_solutions_contract() -> None:
    result = find_pareto_solutions(
        stakeholder_scores=[{"developer": 0.2, "regulator": 0.8}],
        candidate_weights=[{"consensus": {"fairness_nondiscrimination": 0.3}}],
    )
    assert result == []


def test_placeholder_detect_framework_conflicts_sorts_and_deduplicates() -> None:
    response = detect_framework_conflicts(["sg_mgaf", "eu_altai", "sg_mgaf"])
    assert response["framework_ids"] == ["eu_altai", "sg_mgaf"]
    assert response["conflicts"] == []
    assert isinstance(response["summary"], str)


def test_placeholder_detect_stakeholder_conflicts_sorts_and_deduplicates() -> None:
    response = detect_stakeholder_conflicts(["regulator", "developer", "regulator"])
    assert response["stakeholder_ids"] == ["developer", "regulator"]
    assert response["conflicts"] == []
    assert isinstance(response["summary"], str)


def test_placeholder_build_conflict_matrix_shape_contract() -> None:
    response = build_conflict_matrix(
        stakeholder_ids=["developer", "regulator", "developer"],
        framework_ids=["eu_altai", "sg_mgaf", "eu_altai"],
    )
    assert response["stakeholder_ids"] == ["developer", "regulator"]
    assert response["framework_ids"] == ["eu_altai", "sg_mgaf"]
    assert response["matrix"] == []
