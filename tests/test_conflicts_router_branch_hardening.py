from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException

from app.models import ConflictRequest, EthicalDimension, EthicalFramework, UNIFIED_DIMENSIONS
from app.routers import conflicts as cf


def _uniform_weight_map() -> dict[str, float]:
    n_dims = len(UNIFIED_DIMENSIONS)
    return {dimension: 1.0 / n_dims for dimension in UNIFIED_DIMENSIONS}


def _dimension_scores(value: float = 4.0) -> dict[str, float]:
    return {dimension: value for dimension in UNIFIED_DIMENSIONS}


def _framework(criteria_type: str = "benefit") -> EthicalFramework:
    n_dims = len(UNIFIED_DIMENSIONS)
    dimensions = [
        EthicalDimension(
            name=dimension,
            display_name=dimension,
            weight_default=1.0 / n_dims,
            criteria_type=criteria_type,
            assessment_questions=["q"],
        )
        for dimension in UNIFIED_DIMENSIONS
    ]
    return EthicalFramework(id="fw", name="Framework", dimensions=dimensions)


def _valid_conflict_request() -> ConflictRequest:
    return ConflictRequest(
        framework_ids=["fw"],
        stakeholder_ids=["developer", "regulator"],
        ai_system={
            "id": "sys",
            "name": "System",
            "description": "desc",
            "context": {"dimension_scores": _dimension_scores(4.0)},
        },
        weights={
            "developer": _uniform_weight_map(),
            "regulator": _uniform_weight_map(),
        },
    )


def test_resolve_framework_id_branches() -> None:
    payload_direct = SimpleNamespace(framework_id="fw1", framework_ids=[])
    assert cf._resolve_framework_id(payload_direct) == "fw1"  # type: ignore[arg-type]

    payload_fallback = SimpleNamespace(framework_id=None, framework_ids=["fw2"])
    assert cf._resolve_framework_id(payload_fallback) == "fw2"  # type: ignore[arg-type]

    payload_missing = SimpleNamespace(framework_id=None, framework_ids=[])
    with pytest.raises(HTTPException, match="Either framework_id"):
        cf._resolve_framework_id(payload_missing)  # type: ignore[arg-type]


def test_extract_dimension_scores_validation_paths() -> None:
    with pytest.raises(HTTPException, match="ai_system is required"):
        cf._extract_dimension_scores(SimpleNamespace(ai_system=None))  # type: ignore[arg-type]

    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": []}))
    with pytest.raises(HTTPException, match="dimension_scores is required"):
        cf._extract_dimension_scores(payload)  # type: ignore[arg-type]

    missing_scores = _dimension_scores(3.0)
    missing_scores.pop(UNIFIED_DIMENSIONS[-1])
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": missing_scores}))
    with pytest.raises(HTTPException, match="Missing ai_system.context.dimension_scores"):
        cf._extract_dimension_scores(payload)  # type: ignore[arg-type]

    invalid_scores = _dimension_scores(3.0)
    invalid_scores[UNIFIED_DIMENSIONS[0]] = "bad"  # type: ignore[assignment]
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": invalid_scores}))
    with pytest.raises(HTTPException, match="Invalid score"):
        cf._extract_dimension_scores(payload)  # type: ignore[arg-type]

    out_of_range = _dimension_scores(3.0)
    out_of_range[UNIFIED_DIMENSIONS[0]] = 99.0
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": out_of_range}))
    with pytest.raises(HTTPException, match="must be between"):
        cf._extract_dimension_scores(payload)  # type: ignore[arg-type]


def test_ordered_criteria_types_and_weight_validation_errors() -> None:
    missing_dimensions = [
        EthicalDimension(
            name=dimension,
            display_name=dimension,
            weight_default=1.0 / len(UNIFIED_DIMENSIONS),
            criteria_type="benefit",
            assessment_questions=["q"],
        )
        for dimension in UNIFIED_DIMENSIONS[:-1]
    ]
    with pytest.raises(HTTPException, match="missing criteria types"):
        cf._ordered_criteria_types("fw", missing_dimensions)

    invalid_dimensions = [
        SimpleNamespace(name=dimension, criteria_type=("invalid" if idx == 0 else "benefit"))
        for idx, dimension in enumerate(UNIFIED_DIMENSIONS)
    ]
    with pytest.raises(HTTPException, match="invalid criteria type"):
        cf._ordered_criteria_types("fw", invalid_dimensions)

    with pytest.raises(HTTPException, match="must be an object"):
        cf._validate_weights([], "stakeholder")  # type: ignore[arg-type]

    incomplete = _uniform_weight_map()
    incomplete.pop(UNIFIED_DIMENSIONS[0])
    with pytest.raises(HTTPException, match="missing dimensions"):
        cf._validate_weights(incomplete, "stakeholder")

    invalid = _uniform_weight_map()
    invalid[UNIFIED_DIMENSIONS[1]] = "bad"  # type: ignore[assignment]
    with pytest.raises(HTTPException, match="Invalid weight"):
        cf._validate_weights(invalid, "stakeholder")

    out_of_range = _uniform_weight_map()
    out_of_range[UNIFIED_DIMENSIONS[1]] = 1.5
    with pytest.raises(HTTPException, match=r"must be in \[0, 1\]"):
        cf._validate_weights(out_of_range, "stakeholder")

    wrong_sum = _uniform_weight_map()
    wrong_sum[UNIFIED_DIMENSIONS[0]] = 0.5
    with pytest.raises(HTTPException, match="must sum to 1.0"):
        cf._validate_weights(wrong_sum, "stakeholder")


def test_spearman_rho_paths_cover_fallback_and_nan_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    def _nan_spearman(_: np.ndarray, __: np.ndarray) -> tuple[float, float]:
        return float("nan"), 1.0

    monkeypatch.setattr(cf, "_scipy_spearmanr", _nan_spearman)
    rho_nan = cf._spearman_rho(np.array([1.0, 2.0]), np.array([2.0, 1.0]))
    assert rho_nan == 0.0

    monkeypatch.setattr(cf, "_scipy_spearmanr", None)
    rho_zero = cf._spearman_rho(np.array([1.0, 1.0]), np.array([2.0, 2.0]))
    assert rho_zero == 0.0

    rho_valid = cf._spearman_rho(np.array([0.0, 1.0, 2.0]), np.array([2.0, 1.0, 0.0]))
    assert -1.0 <= rho_valid <= 1.0


def test_analyze_conflicts_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _valid_conflict_request()

    monkeypatch.setattr(cf, "get_framework", lambda _: None)
    with pytest.raises(HTTPException, match="not found"):
        cf.analyze_conflicts(payload, db=object())

    monkeypatch.setattr(cf, "get_framework", lambda _: _framework("benefit"))
    monkeypatch.setattr(cf, "get_stakeholder", lambda _sid, _db: None)
    with pytest.raises(HTTPException, match="Stakeholder 'developer' not found"):
        cf.analyze_conflicts(payload, db=object())

    fake_stakeholder = SimpleNamespace(weights=_uniform_weight_map())
    monkeypatch.setattr(cf, "get_stakeholder", lambda _sid, _db: fake_stakeholder)

    def _bad_topsis(*_: object, **__: object) -> np.ndarray:
        raise ValueError("bad topsis")

    monkeypatch.setattr(cf, "topsis_score", _bad_topsis)
    with pytest.raises(HTTPException, match="Invalid scoring inputs"):
        cf.analyze_conflicts(payload, db=object())
