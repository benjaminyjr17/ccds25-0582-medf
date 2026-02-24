from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

UNIFIED_DIMENSIONS: tuple[str, ...] = (
    "transparency_explainability",
    "fairness_nondiscrimination",
    "safety_robustness",
    "privacy_data_governance",
    "human_agency_oversight",
    "accountability",
)

DIMENSION_DISPLAY_NAMES: Dict[str, str] = {
    "transparency_explainability": "Transparency and Explainability",
    "fairness_nondiscrimination": "Fairness and Non-discrimination",
    "safety_robustness": "Safety and Robustness",
    "privacy_data_governance": "Privacy and Data Governance",
    "human_agency_oversight": "Human Agency and Oversight",
    "accountability": "Accountability",
}

WEIGHT_MIN: float = 0.0
WEIGHT_MAX: float = 1.0
LIKERT_MIN: float = 1.0
LIKERT_MAX: float = 5.0

# Backward-compatible aliases for unchanged validators/fields in this file.
SCORE_MIN: float = WEIGHT_MIN
SCORE_MAX: float = WEIGHT_MAX


class CriteriaType(str, Enum):
    BENEFIT = "benefit"
    COST = "cost"


class ConflictLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScoringMethod(str, Enum):
    TOPSIS = "topsis"
    WSM = "wsm"
    AHP = "ahp"


class StakeholderRole(str, Enum):
    DEVELOPER = "developer"
    REGULATOR = "regulator"
    AFFECTED_COMMUNITY = "affected_community"
    CUSTOM = "custom"


def _normalize_dimension_scores(
    value: Dict[str, float],
    *,
    require_all_dimensions: bool,
) -> Dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError("Weights must be a key/value object.")

    normalized: Dict[str, float] = {}
    for dimension, raw_score in value.items():
        if dimension not in UNIFIED_DIMENSIONS:
            raise ValueError(f"Unknown dimension '{dimension}'.")

        try:
            score = float(raw_score)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid score for dimension '{dimension}'.") from exc

        if score < SCORE_MIN or score > SCORE_MAX:
            raise ValueError(
                f"Dimension '{dimension}' score must be between {SCORE_MIN} and {SCORE_MAX}."
            )

        normalized[dimension] = score

    if require_all_dimensions:
        missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in normalized]
        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"Missing scores for dimensions: {missing_str}.")
        ordered = {dimension: normalized[dimension] for dimension in UNIFIED_DIMENSIONS}
        total = sum(ordered.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0 (±0.01).")
        return ordered

    return normalized


class DBStakeholderProfile(Base):
    __tablename__ = "stakeholder_profiles"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"sp_{uuid4().hex}",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weights_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    @property
    def weights(self) -> Dict[str, float]:
        if not self.weights_json:
            return {}

        try:
            loaded = json.loads(self.weights_json)
        except json.JSONDecodeError:
            return {}

        if not isinstance(loaded, dict):
            return {}

        parsed: Dict[str, float] = {}
        for key, raw_value in loaded.items():
            if key not in UNIFIED_DIMENSIONS:
                continue
            try:
                parsed[key] = float(raw_value)
            except (TypeError, ValueError):
                continue

        return parsed

    @weights.setter
    def weights(self, value: Dict[str, float]) -> None:
        normalized = _normalize_dimension_scores(value, require_all_dimensions=True)
        self.weights_json = json.dumps(normalized)


class EthicalDimension(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    weight_default: float = Field(1.0, ge=WEIGHT_MIN, le=WEIGHT_MAX)
    scale_min: float = LIKERT_MIN
    scale_max: float = LIKERT_MAX
    criteria_type: CriteriaType = CriteriaType.BENEFIT
    assessment_questions: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_dimension_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in UNIFIED_DIMENSIONS:
            raise ValueError(f"Dimension name must be one of: {', '.join(UNIFIED_DIMENSIONS)}")
        return normalized

    @field_validator("assessment_questions")
    @classmethod
    def validate_assessment_questions(cls, value: List[str]) -> List[str]:
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:5]


class EthicalFramework(BaseModel):
    id: str
    name: str
    version: Optional[str] = None
    source_url: Optional[str] = None
    dimensions: List[EthicalDimension] = Field(default_factory=list)

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value: List[EthicalDimension]) -> List[EthicalDimension]:
        seen: set[str] = set()
        for dimension in value:
            if dimension.name in seen:
                raise ValueError(f"Duplicate dimension name '{dimension.name}' in framework.")
            seen.add(dimension.name)
        if len(value) != len(UNIFIED_DIMENSIONS):
            raise ValueError(f"Framework must define {len(UNIFIED_DIMENSIONS)} dimensions.")
        total = sum(d.weight_default for d in value)
        if abs(total - 1.0) > 0.01:
            raise ValueError("Framework dimension default weights must sum to 1.0 (±0.01).")
        return value


class StakeholderProfile(BaseModel):
    id: str
    name: str
    role: StakeholderRole
    description: Optional[str] = None
    weights: Dict[str, float]
    is_default: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: Dict[str, float]) -> Dict[str, float]:
        return _normalize_dimension_scores(value, require_all_dimensions=True)


class AISystemInput(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    ai_system: AISystemInput
    framework_ids: List[str]
    stakeholder_ids: List[str]
    weights: Dict[str, Dict[str, float]]
    scoring_method: ScoringMethod = ScoringMethod.TOPSIS

    @field_validator("framework_ids")
    @classmethod
    def validate_framework_ids(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("framework_ids must contain at least one framework id.")
        return list(dict.fromkeys(cleaned))

    @field_validator("stakeholder_ids")
    @classmethod
    def validate_stakeholder_ids(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("stakeholder_ids must contain at least one stakeholder id.")
        return list(dict.fromkeys(cleaned))

    @field_validator("weights")
    @classmethod
    def validate_nested_weights(
        cls,
        value: Dict[str, Dict[str, float]],
        info: ValidationInfo,
    ) -> Dict[str, Dict[str, float]]:
        normalized: Dict[str, Dict[str, float]] = {}
        for stakeholder_id, weight_vector in value.items():
            normalized[stakeholder_id] = _normalize_dimension_scores(
                weight_vector,
                require_all_dimensions=True,
            )

        stakeholder_ids = info.data.get("stakeholder_ids")
        if isinstance(stakeholder_ids, list):
            missing = [stakeholder_id for stakeholder_id in stakeholder_ids if stakeholder_id not in normalized]
            if missing:
                raise ValueError(f"Missing weights for stakeholder ids: {', '.join(missing)}")

        return normalized


class ConflictRequest(BaseModel):
    framework_ids: List[str]
    stakeholder_ids: List[str]


class CompareRequest(BaseModel):
    ai_systems: List[AISystemInput]
    framework_ids: List[str]
    stakeholder_ids: List[str]
    weights: Dict[str, Dict[str, float]]
    scoring_method: ScoringMethod = ScoringMethod.TOPSIS

    @field_validator("ai_systems")
    @classmethod
    def validate_ai_systems(cls, value: List[AISystemInput]) -> List[AISystemInput]:
        if len(value) < 2:
            raise ValueError("ai_systems must include at least two systems for comparison.")
        return value

    @field_validator("weights")
    @classmethod
    def validate_compare_weights(
        cls,
        value: Dict[str, Dict[str, float]],
        info: ValidationInfo,
    ) -> Dict[str, Dict[str, float]]:
        normalized: Dict[str, Dict[str, float]] = {}
        for stakeholder_id, weight_vector in value.items():
            normalized[stakeholder_id] = _normalize_dimension_scores(
                weight_vector,
                require_all_dimensions=True,
            )

        stakeholder_ids = info.data.get("stakeholder_ids")
        if isinstance(stakeholder_ids, list):
            missing = [stakeholder_id for stakeholder_id in stakeholder_ids if stakeholder_id not in normalized]
            if missing:
                raise ValueError(f"Missing weights for stakeholder ids: {', '.join(missing)}")

        return normalized


class StakeholderCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    role: StakeholderRole
    description: Optional[str] = None
    weights: Dict[str, float]
    is_default: bool = False

    @field_validator("weights")
    @classmethod
    def validate_stakeholder_create_weights(cls, value: Dict[str, float]) -> Dict[str, float]:
        return _normalize_dimension_scores(value, require_all_dimensions=True)


class FrameworkScore(BaseModel):
    framework_id: str
    score: float = Field(..., ge=SCORE_MIN, le=SCORE_MAX)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    risk_level: Optional[RiskLevel] = None

    @field_validator("dimension_scores")
    @classmethod
    def validate_dimension_scores(cls, value: Dict[str, float]) -> Dict[str, float]:
        return _normalize_dimension_scores(value, require_all_dimensions=False)


class EvaluationResult(BaseModel):
    ai_system_id: str
    scoring_method: ScoringMethod
    framework_scores: List[FrameworkScore] = Field(default_factory=list)
    overall_score: Optional[float] = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None


class StakeholderConflict(BaseModel):
    stakeholder_a_id: str
    stakeholder_b_id: str
    conflict_level: ConflictLevel
    spearman_rho: float = Field(..., ge=-1.0, le=1.0)
    conflicting_dimensions: List[str] = Field(default_factory=list)

    @field_validator("conflicting_dimensions")
    @classmethod
    def validate_conflicting_dimensions(cls, value: List[str]) -> List[str]:
        for dimension in value:
            if dimension not in UNIFIED_DIMENSIONS:
                raise ValueError(f"Unknown dimension '{dimension}' in conflicting_dimensions.")
        return value


class ParetoSolution(BaseModel):
    solution_id: str
    weights: Dict[str, Dict[str, float]]
    objective_scores: Dict[str, float] = Field(default_factory=dict)
    rank: int = Field(1, ge=1)

    @field_validator("weights")
    @classmethod
    def validate_pareto_weights(cls, value: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        normalized: Dict[str, Dict[str, float]] = {}
        for stakeholder_id, weight_vector in value.items():
            normalized[stakeholder_id] = _normalize_dimension_scores(
                weight_vector,
                require_all_dimensions=True,
            )
        return normalized


class ConflictReport(BaseModel):
    summary: str
    conflicts: List[StakeholderConflict] = Field(default_factory=list)
    pareto_solutions: List[ParetoSolution] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompareResult(BaseModel):
    method: ScoringMethod
    evaluations: List[EvaluationResult] = Field(default_factory=list)
    best_system_id: Optional[str] = None
    notes: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    frameworks_loaded: int
    stakeholder_profiles_loaded: int


class ErrorResponse(BaseModel):
    detail: Any
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
