from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models import EthicalDimension, EthicalFramework, LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from app.routers import evaluate as ev


def _uniform_weight_map() -> dict[str, float]:
    n_dims = len(UNIFIED_DIMENSIONS)
    return {dimension: 1.0 / n_dims for dimension in UNIFIED_DIMENSIONS}


def _base_dimension_scores(value: float = 4.0) -> dict[str, float]:
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


def _evaluate_payload(scoring_method: str = "topsis") -> dict[str, object]:
    return {
        "ai_system": {
            "id": "sys_eval",
            "name": "System",
            "description": "desc",
            "context": {"dimension_scores": _base_dimension_scores(4.0)},
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer"],
        "weights": {"developer": _uniform_weight_map()},
        "scoring_method": scoring_method,
    }


def test_get_dimension_scores_covers_validation_errors() -> None:
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": []}))
    with pytest.raises(HTTPException, match="dimension_scores is required"):
        ev._get_dimension_scores(payload)  # type: ignore[arg-type]

    missing_scores = _base_dimension_scores(3.0)
    missing_scores.pop(UNIFIED_DIMENSIONS[-1])
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": missing_scores}))
    with pytest.raises(HTTPException, match="is missing dimensions"):
        ev._get_dimension_scores(payload)  # type: ignore[arg-type]

    invalid_scores = _base_dimension_scores(3.0)
    invalid_scores[UNIFIED_DIMENSIONS[0]] = "bad"  # type: ignore[assignment]
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": invalid_scores}))
    with pytest.raises(HTTPException, match="Invalid dimension score"):
        ev._get_dimension_scores(payload)  # type: ignore[arg-type]

    out_of_range = _base_dimension_scores(3.0)
    out_of_range[UNIFIED_DIMENSIONS[0]] = LIKERT_MAX + 1.0
    payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": out_of_range}))
    with pytest.raises(HTTPException, match="must be in"):
        ev._get_dimension_scores(payload)  # type: ignore[arg-type]

    valid_payload = SimpleNamespace(ai_system=SimpleNamespace(context={"dimension_scores": _base_dimension_scores(5.0)}))
    scores = ev._get_dimension_scores(valid_payload)  # type: ignore[arg-type]
    assert set(scores) == set(UNIFIED_DIMENSIONS)


def test_validate_weights_covers_validation_errors() -> None:
    with pytest.raises(HTTPException, match="must be a key/value object"):
        ev._validate_weights([], "stakeholder")  # type: ignore[arg-type]

    incomplete = _uniform_weight_map()
    incomplete.pop(UNIFIED_DIMENSIONS[0])
    with pytest.raises(HTTPException, match="missing dimensions"):
        ev._validate_weights(incomplete, "stakeholder")

    invalid = _uniform_weight_map()
    invalid[UNIFIED_DIMENSIONS[1]] = "x"  # type: ignore[assignment]
    with pytest.raises(HTTPException, match="Invalid weight"):
        ev._validate_weights(invalid, "stakeholder")

    out_of_range = _uniform_weight_map()
    out_of_range[UNIFIED_DIMENSIONS[1]] = -0.1
    with pytest.raises(HTTPException, match=r"must be in \[0, 1\]"):
        ev._validate_weights(out_of_range, "stakeholder")

    wrong_sum = _uniform_weight_map()
    wrong_sum[UNIFIED_DIMENSIONS[0]] = 0.5
    with pytest.raises(HTTPException, match="must sum to 1.0"):
        ev._validate_weights(wrong_sum, "stakeholder")


def test_ordered_criteria_types_covers_missing_and_invalid_types() -> None:
    dimensions_missing = [
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
        ev._ordered_criteria_types("fw", dimensions_missing)

    invalid_dimensions = [
        SimpleNamespace(name=dimension, criteria_type=("invalid" if idx == 0 else "benefit"))
        for idx, dimension in enumerate(UNIFIED_DIMENSIONS)
    ]
    with pytest.raises(HTTPException, match="invalid criteria type"):
        ev._ordered_criteria_types("fw", invalid_dimensions)


def test_framework_section_weights_covers_file_and_fallback_paths(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    framework = _framework("benefit")
    monkeypatch.setattr(ev, "_FRAMEWORKS_DIR", tmp_path)

    raw = {
        "criteria": [
            "skip-me",
            {"dimension": None},
            {"dimension": UNIFIED_DIMENSIONS[0], "requirements": [1, 2]},
            {
                "dimension": UNIFIED_DIMENSIONS[1],
                "assessment_questions": [
                    {"section_id": "A", "text": "q1"},
                    {"section_id": "B", "text": "q2"},
                ],
            },
            {
                "dimension": UNIFIED_DIMENSIONS[2],
                "assessment_questions": [{"text": "q1"}, {"text": "q2"}],
            },
        ]
    }
    (tmp_path / "fw.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    weights = ev._framework_section_weights(framework)
    assert set(weights) == set(UNIFIED_DIMENSIONS)
    assert np.isclose(sum(weights.values()), 1.0, atol=1e-9)

    framework_missing = SimpleNamespace(id="fw", dimensions=framework.dimensions[:-1])
    with pytest.raises(HTTPException, match="missing dimensions"):
        ev._framework_section_weights(framework_missing)

    def _boom(_: object) -> object:
        raise RuntimeError("yaml fail")

    monkeypatch.setattr(ev.yaml, "safe_load", _boom)
    with pytest.raises(HTTPException, match="Failed to parse framework YAML"):
        ev._framework_section_weights(framework)


def test_effective_weights_covers_invalid_sum_and_non_finite_output(monkeypatch: pytest.MonkeyPatch) -> None:
    zeros = {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}
    with pytest.raises(HTTPException, match="non-finite or zero sum"):
        ev._effective_weights(zeros, _uniform_weight_map())

    def _always_false(_: object) -> bool:
        return False

    monkeypatch.setattr(ev.np, "all", _always_false)
    with pytest.raises(HTTPException, match="non-finite values"):
        ev._effective_weights(_uniform_weight_map(), _uniform_weight_map())


def test_risk_level_threshold_boundaries() -> None:
    assert ev._risk_level(0.80).value == "low"
    assert ev._risk_level(0.60).value == "medium"
    assert ev._risk_level(0.40).value == "high"
    assert ev._risk_level(0.39).value == "critical"


def test_evaluate_endpoint_covers_wsm_and_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestClient(app) as client:
        response_wsm = client.post("/api/evaluate", json=_evaluate_payload("wsm"))
        assert response_wsm.status_code == 200

        response_ahp = client.post("/api/evaluate", json=_evaluate_payload("ahp"))
        assert response_ahp.status_code == 400

        missing_framework = _evaluate_payload("topsis")
        missing_framework["framework_ids"] = ["does_not_exist"]
        response_framework = client.post("/api/evaluate", json=missing_framework)
        assert response_framework.status_code == 404

        missing_stakeholder = _evaluate_payload("topsis")
        missing_stakeholder["stakeholder_ids"] = ["nobody"]
        missing_stakeholder["weights"] = {"nobody": _uniform_weight_map()}
        response_stakeholder = client.post("/api/evaluate", json=missing_stakeholder)
        assert response_stakeholder.status_code == 404

        def _bad_topsis(*_: object, **__: object) -> np.ndarray:
            raise ValueError("bad topsis")

        monkeypatch.setattr(ev, "topsis_score", _bad_topsis)
        response_bad_topsis = client.post("/api/evaluate", json=_evaluate_payload("topsis"))
        assert response_bad_topsis.status_code == 422

        def _bad_wsm(*_: object, **__: object) -> np.ndarray:
            raise ValueError("bad wsm")

        monkeypatch.setattr(ev, "wsm_scores", _bad_wsm)
        response_bad_wsm = client.post("/api/evaluate", json=_evaluate_payload("wsm"))
        assert response_bad_wsm.status_code == 422


def test_evaluate_rejects_unsupported_scoring_method_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_framework = _framework("benefit")
    fake_stakeholder = SimpleNamespace(weights=_uniform_weight_map())

    payload = SimpleNamespace(
        ai_system=SimpleNamespace(id="sys", context={"dimension_scores": _base_dimension_scores(4.0)}),
        framework_ids=["fw"],
        stakeholder_ids=["stakeholder"],
        weights={"stakeholder": _uniform_weight_map()},
        scoring_method=SimpleNamespace(value="custom"),
    )

    monkeypatch.setattr(ev, "get_framework", lambda _: fake_framework)
    monkeypatch.setattr(ev, "get_stakeholder", lambda _sid, _db: fake_stakeholder)

    with pytest.raises(HTTPException, match="Unsupported scoring method"):
        ev.evaluate(payload, db=object())  # type: ignore[arg-type]
