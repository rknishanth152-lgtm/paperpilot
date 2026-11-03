from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    """Report that the API process is running.

    It does not check PostgreSQL or GROBID, so it never reports them as
    healthy without evidence.
    """
    return HealthResponse(status="ok")
