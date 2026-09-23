"""
SIF Sentinel — Health check route.

GET /health
Returns server status, version, and environment.
Used for deployment readiness probes and demo verification.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verify that the SIF Sentinel API is running correctly.",
)
def health_check() -> HealthResponse:
    """
    Returns the current operational status of the API.

    - **status**: 'ok' when the service is healthy
    - **version**: current API version
    - **environment**: 'development' / 'production'
    """
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        message="SIF Sentinel API is running. No AI pipeline yet — Phase 1 foundation.",
    )
