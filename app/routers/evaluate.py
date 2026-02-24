from fastapi import APIRouter

from app.framework_registry import list_frameworks
from app.models import EvaluationRequest, EvaluationResponse
from app.scoring_engine import compute_scores

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("", response_model=EvaluationResponse)
def evaluate(payload: EvaluationRequest) -> EvaluationResponse:
    available_frameworks = [framework.id for framework in list_frameworks()]
    scores = compute_scores(payload, framework_ids=available_frameworks)
    return EvaluationResponse(
        case_id=payload.case_id,
        scores=scores,
        notes="Deterministic placeholder scores.",
    )
