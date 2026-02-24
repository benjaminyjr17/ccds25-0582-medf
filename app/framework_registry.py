from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    DBStakeholderProfile,
    DIMENSION_DISPLAY_NAMES,
    EthicalDimension,
    EthicalFramework,
    StakeholderRole,
    UNIFIED_DIMENSIONS,
)

FRAMEWORK_DIR = Path(__file__).resolve().parent / "frameworks"
FRAMEWORK_FILES = ("eu_altai.yaml", "nist_ai_rmf.yaml", "sg_mgaf.yaml")

_FRAMEWORKS: dict[str, EthicalFramework] = {}

_DEFAULT_STAKEHOLDER_WEIGHTS: dict[str, dict[str, float]] = {
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
    "affected_community": {
        "transparency_explainability": 0.10,
        "fairness_nondiscrimination": 0.30,
        "safety_robustness": 0.10,
        "privacy_data_governance": 0.15,
        "human_agency_oversight": 0.20,
        "accountability": 0.15,
    },
}


def _parse_dimensions(raw_framework: dict[str, Any], file_name: str) -> list[EthicalDimension]:
    raw_dimensions = raw_framework.get("dimensions")
    if not isinstance(raw_dimensions, list):
        raw_dimensions = raw_framework.get("criteria")

    if not isinstance(raw_dimensions, list):
        raise RuntimeError(
            f"Framework file '{file_name}' must contain a 'dimensions' or 'criteria' list."
        )

    dimension_map: dict[str, EthicalDimension] = {}

    for index, item in enumerate(raw_dimensions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Framework file '{file_name}' has an invalid dimension at index {index}."
            )

        raw_dimension = item.get("dimension")
        if raw_dimension is None:
            raw_dimension = item.get("id")

        if raw_dimension is None:
            raise RuntimeError(
                f"Framework file '{file_name}' has a dimension without id at index {index}."
            )

        dimension_id = str(raw_dimension).strip().lower()
        dimension_name = str(
            item.get("name")
            or DIMENSION_DISPLAY_NAMES.get(dimension_id)
            or dimension_id.replace("_", " ").title()
        )

        raw_description = item.get("description")
        description = str(raw_description) if raw_description is not None else None

        raw_criteria_type = item.get("criteria_type", "benefit")
        raw_weight = item.get("weight", 1.0)

        try:
            dimension = EthicalDimension(
                id=dimension_id,
                name=dimension_name,
                criteria_type=str(raw_criteria_type).lower(),
                description=description,
                weight=float(raw_weight),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Invalid dimension '{dimension_id}' in framework file '{file_name}': {exc}"
            ) from exc

        dimension_map[dimension.id] = dimension

    if not dimension_map:
        raise RuntimeError(f"Framework file '{file_name}' contains no valid dimensions.")

    ordered_dimensions = [
        dimension_map[dimension]
        for dimension in UNIFIED_DIMENSIONS
        if dimension in dimension_map
    ]

    if len(ordered_dimensions) != len(UNIFIED_DIMENSIONS):
        missing = [
            dimension for dimension in UNIFIED_DIMENSIONS if dimension not in dimension_map
        ]
        raise RuntimeError(
            f"Framework file '{file_name}' is missing canonical dimensions: {', '.join(missing)}"
        )

    weight_sum = sum(dimension.weight for dimension in ordered_dimensions)
    if abs(weight_sum - 1.0) > 0.01:
        raise RuntimeError(
            f"Framework file '{file_name}' dimension weights must sum to 1.0 (±0.01); got {weight_sum:.4f}."
        )

    return ordered_dimensions


def load_frameworks() -> list[EthicalFramework]:
    _FRAMEWORKS.clear()

    for file_name in FRAMEWORK_FILES:
        file_path = FRAMEWORK_DIR / file_name
        if not file_path.exists():
            raise RuntimeError(f"Missing framework definition file: {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                raw_framework = yaml.safe_load(file_obj) or {}
        except Exception as exc:
            raise RuntimeError(f"Failed to read framework file '{file_path}': {exc}") from exc

        if not isinstance(raw_framework, dict):
            raise RuntimeError(f"Framework file '{file_path}' must define a YAML object.")

        framework_id = str(raw_framework.get("id") or file_path.stem).strip()
        framework_name = str(raw_framework.get("name") or framework_id).strip()

        raw_version = raw_framework.get("version")
        version = str(raw_version) if raw_version is not None else None

        raw_description = raw_framework.get("description")
        description = str(raw_description) if raw_description is not None else None

        dimensions = _parse_dimensions(raw_framework, file_name)

        try:
            framework = EthicalFramework(
                id=framework_id,
                name=framework_name,
                version=version,
                description=description,
                dimensions=dimensions,
            )
        except Exception as exc:
            raise RuntimeError(f"Invalid framework definition in '{file_name}': {exc}") from exc

        _FRAMEWORKS[framework.id] = framework

    return list(_FRAMEWORKS.values())


def get_framework(framework_id: str) -> EthicalFramework | None:
    if not _FRAMEWORKS:
        load_frameworks()
    return _FRAMEWORKS.get(framework_id)


def get_all_frameworks() -> list[EthicalFramework]:
    if not _FRAMEWORKS:
        load_frameworks()
    return list(_FRAMEWORKS.values())


def list_frameworks() -> list[EthicalFramework]:
    return get_all_frameworks()


def get_harmonisation_mapping() -> dict[str, dict[str, str]]:
    frameworks = get_all_frameworks()
    return {
        framework.id: {dimension: dimension for dimension in UNIFIED_DIMENSIONS}
        for framework in frameworks
    }


def seed_default_stakeholders(db: Session | None = None) -> None:
    owns_session = db is None
    session = db or SessionLocal()

    try:
        defaults = (
            {
                "id": "developer",
                "name": "Developer",
                "role": StakeholderRole.DEVELOPER.value,
                "description": "Represents AI system builders and maintainers.",
                "weights": _DEFAULT_STAKEHOLDER_WEIGHTS["developer"],
            },
            {
                "id": "regulator",
                "name": "Regulator",
                "role": StakeholderRole.REGULATOR.value,
                "description": "Represents governance, policy, and compliance oversight.",
                "weights": _DEFAULT_STAKEHOLDER_WEIGHTS["regulator"],
            },
            {
                "id": "affected_community",
                "name": "Affected Community",
                "role": StakeholderRole.AFFECTED_COMMUNITY.value,
                "description": "Represents impacted individuals and communities.",
                "weights": _DEFAULT_STAKEHOLDER_WEIGHTS["affected_community"],
            },
        )

        default_ids = [entry["id"] for entry in defaults]
        existing_rows = {
            row.id: row
            for row in session.query(DBStakeholderProfile)
            .filter(DBStakeholderProfile.id.in_(default_ids))
            .all()
        }

        for entry in defaults:
            existing = existing_rows.get(entry["id"])
            if existing is not None:
                existing.name = entry["name"]
                existing.role = entry["role"]
                existing.description = entry["description"]
                existing.is_default = True
                existing.weights = entry["weights"]
                continue

            row = DBStakeholderProfile(
                id=entry["id"],
                name=entry["name"],
                role=entry["role"],
                description=entry["description"],
                is_default=True,
            )
            row.weights = entry["weights"]
            session.add(row)

        session.commit()
    finally:
        if owns_session:
            session.close()


def get_stakeholder(stakeholder_id: str, db: Session) -> DBStakeholderProfile | None:
    return (
        db.query(DBStakeholderProfile)
        .filter(DBStakeholderProfile.id == stakeholder_id)
        .first()
    )
