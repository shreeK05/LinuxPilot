"""
Health check endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from linuxpilot.config import settings
    
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
    )
