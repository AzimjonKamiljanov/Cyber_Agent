"""REST routes and static file mounting for Cyber Agent."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/healthz")
async def health_check() -> JSONResponse:
    """Read-only health check endpoint."""
    return JSONResponse(content={"status": "ok", "stage": "s1", "mode": "live"})
