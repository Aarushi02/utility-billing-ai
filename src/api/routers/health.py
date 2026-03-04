from fastapi import APIRouter

from src.api.schemas.common import HealthResponse


router = APIRouter()


@router.get("/health/live", response_model=HealthResponse)
def health_live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
def health_ready() -> HealthResponse:
    return HealthResponse(status="ok")
