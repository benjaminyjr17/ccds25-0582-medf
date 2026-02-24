from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.models import FrameworkCriterion, FrameworkDefinition, FrameworkSummary

FRAMEWORK_DIR = Path(__file__).resolve().parent / "frameworks"
FRAMEWORK_FILES = ("eu_altai.yaml", "nist_ai_rmf.yaml", "sg_mgaf.yaml")


def _parse_criteria(raw_criteria: Any) -> list[FrameworkCriterion]:
    if not isinstance(raw_criteria, list):
        return []

    criteria: list[FrameworkCriterion] = []
    for index, criterion in enumerate(raw_criteria, start=1):
        if not isinstance(criterion, dict):
            continue

        criterion_id = str(criterion.get("id") or f"criterion_{index}")
        criterion_name = str(criterion.get("name") or criterion_id)

        raw_description = criterion.get("description")
        description = str(raw_description) if raw_description is not None else None

        raw_dimension = criterion.get("dimension")
        raw_weight = criterion.get("weight")
        if raw_dimension is None or raw_weight is None:
            continue

        try:
            parsed = FrameworkCriterion.model_validate(
                {
                    "id": criterion_id,
                    "name": criterion_name,
                    "dimension": str(raw_dimension),
                    "description": description,
                    "weight": float(raw_weight),
                }
            )
        except (TypeError, ValueError, ValidationError):
            continue

        criteria.append(parsed)

    return criteria


def _parse_framework(raw_framework: Any, default_id: str) -> FrameworkDefinition | None:
    if not isinstance(raw_framework, dict):
        return None

    framework_id = str(raw_framework.get("id") or default_id)
    framework_name = str(raw_framework.get("name") or framework_id)

    raw_version = raw_framework.get("version")
    version = str(raw_version) if raw_version is not None else None

    raw_description = raw_framework.get("description")
    description = str(raw_description) if raw_description is not None else None

    return FrameworkDefinition(
        id=framework_id,
        name=framework_name,
        version=version,
        description=description,
        criteria=_parse_criteria(raw_framework.get("criteria")),
    )


@lru_cache(maxsize=1)
def load_frameworks() -> list[FrameworkDefinition]:
    frameworks: list[FrameworkDefinition] = []

    for filename in FRAMEWORK_FILES:
        file_path = FRAMEWORK_DIR / filename
        if not file_path.exists():
            continue

        with file_path.open("r", encoding="utf-8") as file_obj:
            raw_framework = yaml.safe_load(file_obj) or {}

        parsed_framework = _parse_framework(raw_framework, file_path.stem)
        if parsed_framework is not None:
            frameworks.append(parsed_framework)

    return frameworks


def list_frameworks() -> list[FrameworkSummary]:
    frameworks = load_frameworks()
    return [
        FrameworkSummary(
            id=framework.id,
            name=framework.name,
            version=framework.version,
            description=framework.description,
        )
        for framework in frameworks
    ]


def get_framework(framework_id: str) -> FrameworkDefinition | None:
    for framework in load_frameworks():
        if framework.id == framework_id:
            return framework
    return None
