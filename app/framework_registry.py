from __future__ import annotations

from app.models import FrameworkDefinition, FrameworkSummary


def load_frameworks() -> list[FrameworkDefinition]:
    return []


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
