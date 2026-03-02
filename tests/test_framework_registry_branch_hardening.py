from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app import framework_registry as fr
from app.models import UNIFIED_DIMENSIONS


def _raw_dimension_payload(dimension: str, *, use_dimension_field: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": dimension.replace("_", " ").title(),
        "weight": 1.0 / len(UNIFIED_DIMENSIONS),
        "criteria_type": "benefit",
        "assessment_questions": ["q1", "q2"],
    }
    if use_dimension_field:
        payload["dimension"] = dimension
    else:
        payload["id"] = dimension
    return payload


def _valid_framework_yaml() -> dict[str, object]:
    return {
        "id": "fw",
        "name": "Framework",
        "version": "1.0",
        "source_url": "https://example.com",
        "dimensions": [_raw_dimension_payload(dimension) for dimension in UNIFIED_DIMENSIONS],
    }


def test_parse_dimensions_covers_criteria_fallback_and_runtime_errors() -> None:
    raw = {
        "criteria": [
            _raw_dimension_payload(UNIFIED_DIMENSIONS[0], use_dimension_field=False),
            *[_raw_dimension_payload(dimension) for dimension in UNIFIED_DIMENSIONS[1:]],
        ]
    }
    raw["criteria"][0]["scale_min"] = 1
    raw["criteria"][0]["scale_max"] = 7
    parsed = fr._parse_dimensions(raw, "ok.yaml")
    assert len(parsed) == len(UNIFIED_DIMENSIONS)

    with pytest.raises(RuntimeError, match="invalid dimension at index"):
        fr._parse_dimensions({"dimensions": ["nope"]}, "bad.yaml")

    with pytest.raises(RuntimeError, match="criterion missing 'dimension'"):
        fr._parse_dimensions(
            {
                "criteria": [
                    {"id": "not_a_canonical_dimension", "weight": 1.0},
                ]
            },
            "bad.yaml",
        )

    with pytest.raises(RuntimeError, match="contains no valid dimensions"):
        fr._parse_dimensions({"dimensions": []}, "bad.yaml")


def test_load_frameworks_error_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fr, "FRAMEWORK_DIR", tmp_path)

    monkeypatch.setattr(fr, "FRAMEWORK_FILES", ("missing.yaml",))
    with pytest.raises(RuntimeError, match="Missing framework definition file"):
        fr.load_frameworks()

    malformed_path = tmp_path / "malformed.yaml"
    malformed_path.write_text("id: [\n", encoding="utf-8")
    monkeypatch.setattr(fr, "FRAMEWORK_FILES", ("malformed.yaml",))
    with pytest.raises(RuntimeError, match="Failed to read framework file"):
        fr.load_frameworks()

    scalar_path = tmp_path / "scalar.yaml"
    scalar_path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    monkeypatch.setattr(fr, "FRAMEWORK_FILES", ("scalar.yaml",))
    with pytest.raises(RuntimeError, match="must define a YAML object"):
        fr.load_frameworks()

    invalid_path = tmp_path / "invalid.yaml"
    invalid_framework = _valid_framework_yaml()
    invalid_framework["dimensions"] = [{"dimension": UNIFIED_DIMENSIONS[0], "weight": 1.0}]
    invalid_path.write_text(yaml.safe_dump(invalid_framework), encoding="utf-8")
    monkeypatch.setattr(fr, "FRAMEWORK_FILES", ("invalid.yaml",))
    with pytest.raises(RuntimeError, match="missing canonical dimensions"):
        fr.load_frameworks()


def test_load_frameworks_success_and_registry_accessors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fr, "FRAMEWORK_DIR", tmp_path)

    fw_one = _valid_framework_yaml()
    fw_one["id"] = "fw_one"
    (tmp_path / "fw_one.yaml").write_text(yaml.safe_dump(fw_one), encoding="utf-8")

    fw_two = _valid_framework_yaml()
    fw_two["id"] = "fw_two"
    (tmp_path / "fw_two.yaml").write_text(yaml.safe_dump(fw_two), encoding="utf-8")

    monkeypatch.setattr(fr, "FRAMEWORK_FILES", ("fw_one.yaml", "fw_two.yaml"))

    loaded = fr.load_frameworks()
    assert {framework.id for framework in loaded} == {"fw_one", "fw_two"}

    assert fr.get_framework("fw_one") is not None
    all_frameworks = fr.get_all_frameworks()
    listed = fr.list_frameworks()
    assert len(all_frameworks) == len(listed) == 2

    mapping = fr.get_harmonisation_mapping()
    assert set(mapping.keys()) == set(UNIFIED_DIMENSIONS)
    for dimension, per_framework in mapping.items():
        assert per_framework["fw_one"] == dimension
        assert per_framework["fw_two"] == dimension
