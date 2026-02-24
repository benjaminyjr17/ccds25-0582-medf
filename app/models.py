from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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
    description: str | None = None
    weight: float = 1.0


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
    id: int
    name: str
    role: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class StakeholderCreate(BaseModel):
    name: str
    role: str
    description: str


class EvaluationRequest(BaseModel):
    case_id: str | None = None
    framework_ids: list[str] = Field(default_factory=list)
    stakeholder_ids: list[int] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)


class FrameworkScore(BaseModel):
    framework_id: str
    score: float


class EvaluationResponse(BaseModel):
    case_id: str | None = None
    scores: list[FrameworkScore] = Field(default_factory=list)
    notes: str | None = None


class ConflictCheckRequest(BaseModel):
    framework_ids: list[str] = Field(default_factory=list)
    stakeholder_ids: list[int] = Field(default_factory=list)


class ConflictItem(BaseModel):
    id: str
    conflict_type: str
    message: str
    severity: str = "low"


class ConflictCheckResponse(BaseModel):
    summary: str
    conflicts: list[ConflictItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
