from fastapi import APIRouter
from src.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics")
metrics_service = MetricsService()


@router.get("/aws-credits")
def aws_credits():
    return metrics_service.get_aws_metrics()


@router.get("/llm-credits")
def llm_credits():
    return metrics_service.get_openai_metrics()


@router.get("/summary")
def summary():
    return {
        "aws": metrics_service.get_aws_metrics(),
        "llm": metrics_service.get_openai_metrics(),
    }