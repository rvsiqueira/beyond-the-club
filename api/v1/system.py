"""
System endpoints.

Health checks and system status.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_status():
    """
    Health check endpoint.

    Returns system status for Docker healthcheck.
    """
    return {
        "status": "healthy",
        "service": "btc-api"
    }
