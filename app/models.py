from __future__ import annotations

from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

UNIFIED_DIMENSIONS: tuple[str, ...] = (
    "fairness",
    "accountability",
    "transparency",
    "privacy",
    "safety",
    "human_oversight",
)
UnifiedDimension = Literal[
    "fairness",
    "accountability",
    "transparency",
    "privacy",
    "safety",
    "human_oversight",
]


class StakeholderRole(str, Enum):
    DEVELOPER = "developer"
    REGULATOR = "regulator"
    AFFECTED_COMMUNITY = "affected_community"
    CUSTOM = "custom"


class StakeholderORM(Base):
    __tablename__ = "stakeholders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class HealthResponse(BaseModel):
    status: str
    service: str


class FrameworkCriterion(BaseModel):
    id: str
    name: str
    dimension: UnifiedDimension
    description: str | None = None
    weight: float = Field(..., gt=0.0)


class FrameworkDefinition(BaseModel):
    id: str
    name: str
    version: str | None = None
    description: str | None = None
    criteria: list[FrameworkCriterion] = Field(default_factory=list)


class FrameworkSummary(BaseModel):
    id: str
    name: str
    version: str | None = None
    description: str | None = None


class Stakeholder(BaseModel):
    id: str
    name: str
    role: StakeholderRole
    description: str

    model_config = ConfigDict(from_attributes=True)


class StakeholderCreate(BaseModel):
    name: str
    role: StakeholderRole
    description: str


class EvaluationRequest(BaseModel):
    case_id: str | None = None
    framework_ids: list[str] = Field(default_factory=list)
    stakeholder_ids: list[str] = Field(default_factory=list)
    weights: dict[str, dict[UnifiedDimension, float]]
    inputs: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_weights(self) -> EvaluationRequest:
        expected_dimensions = set(UNIFIED_DIMENSIONS)
        requested_stakeholders = set(self.stakeholder_ids)
        provided_stakeholders = set(self.weights.keys())

        missing_stakeholders = requested_stakeholders - provided_stakeholders
        if missing_stakeholders:
            missing_ids = ", ".join(sorted(missing_stakeholders))
            raise ValueError(f"Missing weights for stakeholder IDs: {missing_ids}")

        for stakeholder_id, weight_vector in self.weights.items():
            present_dimensions = set(weight_vector.keys())
            if present_dimensions != expected_dimensions:
                raise ValueError(
                    f"Stakeholder '{stakeholder_id}' must define weights for all six unified dimensions."
                )

        return self


class FrameworkScore(BaseModel):
    framework_id: str
    score: float


class EvaluationResponse(BaseModel):
    case_id: str | None = None
    scores: list[FrameworkScore] = Field(default_factory=list)
    notes: str | None = None


class ConflictCheckRequest(BaseModel):
    framework_ids: list[str] = Field(default_factory=list)
    stakeholder_ids: list[str] = Field(default_factory=list)


class ConflictItem(BaseModel):
    id: str
    conflict_type: str
    message: str
    severity: str = "low"


class ConflictCheckResponse(BaseModel):
    summary: str
    conflicts: list[ConflictItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
