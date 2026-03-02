from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import ParetoSolution, UNIFIED_DIMENSIONS
from app.routers import pareto as pr


def _uniform_weight_map() -> dict[str, float]:
    n_dims = len(UNIFIED_DIMENSIONS)
    return {dimension: 1.0 / n_dims for dimension in UNIFIED_DIMENSIONS}


def _dimension_scores(value: float = 4.0) -> dict[str, float]:
    return {dimension: value for dimension in UNIFIED_DIMENSIONS}


def _valid_payload_dict() -> dict[str, object]:
    return {
        "ai_system": {
            "id": "sys",
            "name": "System",
            "description": "desc",
            "context": {"dimension_scores": _dimension_scores(4.0)},
        },
        "framework_ids": ["fw"],
        "stakeholder_ids": ["developer", "regulator"],
        "weights": {
            "developer": _uniform_weight_map(),
            "regulator": _uniform_weight_map(),
        },
        "n_solutions": 4,
        "pop_size": 16,
        "n_gen": 10,
        "seed": 7,
        "deterministic_mode": True,
    }


def _valid_request() -> pr.ParetoRequest:
    return pr.ParetoRequest(**_valid_payload_dict())


def _fake_framework() -> object:
    dims = [
        SimpleNamespace(name=dimension, weight_default=1.0 / len(UNIFIED_DIMENSIONS), criteria_type="benefit")
        for dimension in UNIFIED_DIMENSIONS
    ]
    return SimpleNamespace(id="fw", dimensions=dims)


def _fake_stakeholder() -> object:
    return SimpleNamespace(weights=_uniform_weight_map())


def test_resolve_framework_id_and_extract_x_validation_paths() -> None:
    payload_direct = SimpleNamespace(framework_id="fw1", framework_ids=[])
    assert pr._resolve_framework_id_or_422(payload_direct) == "fw1"  # type: ignore[arg-type]

    payload_fallback = SimpleNamespace(framework_id=None, framework_ids=["fw2"])
    assert pr._resolve_framework_id_or_422(payload_fallback) == "fw2"  # type: ignore[arg-type]

    payload_missing = SimpleNamespace(framework_id=None, framework_ids=[])
    with pytest.raises(HTTPException, match="Either framework_id"):
        pr._resolve_framework_id_or_422(payload_missing)  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="dimension_scores is required"):
        pr._extract_x_normalized_or_422(SimpleNamespace(context={"dimension_scores": []}))  # type: ignore[arg-type]

    missing = _dimension_scores(3.0)
    missing.pop(UNIFIED_DIMENSIONS[-1])
    with pytest.raises(HTTPException, match="Missing ai_system.context.dimension_scores"):
        pr._extract_x_normalized_or_422(SimpleNamespace(context={"dimension_scores": missing}))  # type: ignore[arg-type]

    invalid = _dimension_scores(3.0)
    invalid[UNIFIED_DIMENSIONS[0]] = "bad"  # type: ignore[assignment]
    with pytest.raises(HTTPException, match="Invalid score"):
        pr._extract_x_normalized_or_422(SimpleNamespace(context={"dimension_scores": invalid}))  # type: ignore[arg-type]

    out_of_range = _dimension_scores(3.0)
    out_of_range[UNIFIED_DIMENSIONS[0]] = 100.0
    with pytest.raises(HTTPException, match="must be between"):
        pr._extract_x_normalized_or_422(SimpleNamespace(context={"dimension_scores": out_of_range}))  # type: ignore[arg-type]


def test_validate_weight_vector_and_simplex_helpers() -> None:
    with pytest.raises(HTTPException, match="must be a key/value object"):
        pr._validate_weight_vector_or_422([], "stakeholder")  # type: ignore[arg-type]

    incomplete = _uniform_weight_map()
    incomplete.pop(UNIFIED_DIMENSIONS[0])
    with pytest.raises(HTTPException, match="missing dimensions"):
        pr._validate_weight_vector_or_422(incomplete, "stakeholder")

    invalid = _uniform_weight_map()
    invalid[UNIFIED_DIMENSIONS[0]] = "oops"  # type: ignore[assignment]
    with pytest.raises(HTTPException, match="Invalid weight"):
        pr._validate_weight_vector_or_422(invalid, "stakeholder")

    out_of_range = _uniform_weight_map()
    out_of_range[UNIFIED_DIMENSIONS[0]] = -0.1
    with pytest.raises(HTTPException, match=r"must be in \[0, 1\]"):
        pr._validate_weight_vector_or_422(out_of_range, "stakeholder")

    wrong_sum = _uniform_weight_map()
    wrong_sum[UNIFIED_DIMENSIONS[0]] = 0.5
    with pytest.raises(HTTPException, match="must sum to 1.0"):
        pr._validate_weight_vector_or_422(wrong_sum, "stakeholder")

    normalized = pr._validate_weight_vector_or_422(_uniform_weight_map(), "stakeholder")
    assert np.isclose(sum(normalized.values()), 1.0, atol=1e-9)

    one_dim_zero = pr._normalize_simplex(np.array([0.0, 0.0, 0.0], dtype=float))
    assert np.allclose(one_dim_zero, np.array([1.0 / 3.0] * 3, dtype=float), atol=1e-9)

    matrix = np.array([[0.0, 0.0, 0.0], [2.0, 1.0, 1.0]], dtype=float)
    normalized_matrix = pr._normalize_simplex(matrix)
    assert np.isclose(float(np.sum(normalized_matrix[0])), 1.0, atol=1e-9)
    assert np.isclose(float(np.sum(normalized_matrix[1])), 1.0, atol=1e-9)


def test_filter_nondominated_and_domination_paths() -> None:
    rows = [
        (
            np.array([0.6, 0.4], dtype=float),
            np.array([0.1, 0.2], dtype=float),
            0.9,
            (0.6, 0.4),
        ),
        (
            np.array([0.5, 0.5], dtype=float),
            np.array([0.3, 0.3], dtype=float),
            0.7,
            (0.5, 0.5),
        ),
    ]
    frontier = pr._filter_nondominated(rows)
    assert len(frontier) == 1
    assert frontier[0][3] == (0.6, 0.4)


def test_pareto_request_validators_cover_error_cases() -> None:
    bad = _valid_payload_dict()
    bad["stakeholder_ids"] = ["developer"]
    with pytest.raises(ValidationError, match="at least two"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    bad["weights"] = {"developer": []}
    with pytest.raises(ValidationError, match="valid dictionary"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    bad_weights = dict(_uniform_weight_map())
    bad_weights.pop(UNIFIED_DIMENSIONS[0])
    bad["weights"] = {"developer": bad_weights, "regulator": _uniform_weight_map()}
    with pytest.raises(ValidationError, match="missing dimensions"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    broken = _uniform_weight_map()
    broken[UNIFIED_DIMENSIONS[0]] = "x"  # type: ignore[assignment]
    bad["weights"] = {"developer": broken, "regulator": _uniform_weight_map()}
    with pytest.raises(ValidationError, match="valid number"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    broken = _uniform_weight_map()
    broken[UNIFIED_DIMENSIONS[0]] = 2.0
    bad["weights"] = {"developer": broken, "regulator": _uniform_weight_map()}
    with pytest.raises(ValidationError, match=r"must be in \[0, 1\]"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    broken = _uniform_weight_map()
    broken[UNIFIED_DIMENSIONS[0]] = 0.5
    bad["weights"] = {"developer": broken, "regulator": _uniform_weight_map()}
    with pytest.raises(ValidationError, match="must sum to 1.0"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    bad["framework_ids"] = []
    bad["framework_id"] = None
    with pytest.raises(ValidationError, match="Either framework_id"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    bad["ai_system"] = {
        "id": "sys",
        "name": "System",
        "context": {"dimension_scores": []},
    }
    with pytest.raises(ValidationError, match="dimension_scores is required"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    ds = _dimension_scores(4.0)
    ds.pop(UNIFIED_DIMENSIONS[0])
    bad["ai_system"] = {"id": "sys", "name": "System", "context": {"dimension_scores": ds}}
    with pytest.raises(ValidationError, match="is missing dimensions"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    ds = _dimension_scores(4.0)
    ds[UNIFIED_DIMENSIONS[0]] = "bad"  # type: ignore[assignment]
    bad["ai_system"] = {"id": "sys", "name": "System", "context": {"dimension_scores": ds}}
    with pytest.raises(ValidationError, match="Invalid ai_system.context.dimension_scores value"):
        pr.ParetoRequest(**bad)

    bad = _valid_payload_dict()
    ds = _dimension_scores(4.0)
    ds[UNIFIED_DIMENSIONS[0]] = 99.0
    bad["ai_system"] = {"id": "sys", "name": "System", "context": {"dimension_scores": ds}}
    with pytest.raises(ValidationError, match="must be between"):
        pr.ParetoRequest(**bad)


def test_generate_pareto_error_and_algorithm_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _valid_request()

    monkeypatch.setattr(pr, "get_framework", lambda _: None)
    with pytest.raises(HTTPException, match="not found"):
        pr.generate_pareto_solutions(payload, db=object())

    monkeypatch.setattr(pr, "get_framework", lambda _: _fake_framework())
    monkeypatch.setattr(pr, "get_stakeholder", lambda _sid, _db: None)
    with pytest.raises(HTTPException, match="Stakeholder 'developer' not found"):
        pr.generate_pareto_solutions(payload, db=object())

    monkeypatch.setattr(pr, "get_stakeholder", lambda _sid, _db: _fake_stakeholder())
    monkeypatch.setattr(pr, "write_audit_record", lambda **_: None)

    monkeypatch.setattr(pr, "_HAS_PYMOO", False)
    fallback_result = pr.generate_pareto_solutions(payload, db=object())
    assert fallback_result.pareto_solutions
    assert all(isinstance(item, ParetoSolution) for item in fallback_result.pareto_solutions)

    class _DummyNSGA2:
        def __init__(self, pop_size: int):
            self.pop_size = pop_size

    class _Result:
        X = np.array([0.2, 0.2, 0.2, 0.1, 0.2, 0.1], dtype=float)
        F = np.array([0.1, 0.2], dtype=float)

    monkeypatch.setattr(pr, "_HAS_PYMOO", True)
    monkeypatch.setattr(pr, "NSGA2", _DummyNSGA2)
    monkeypatch.setattr(pr, "get_termination", lambda *_: "term")
    monkeypatch.setattr(pr, "minimize", lambda *_args, **_kwargs: _Result())

    pymoo_result = pr.generate_pareto_solutions(payload, db=object())
    assert pymoo_result.pareto_solutions
