"""
FastAPI application entry point.

Configures the API with all routes, middleware, and error handling.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .v1.router import router as v1_router
from .deps import get_services, close_services

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Admin phone for scheduled tasks (will use this user's Beyond tokens)
ADMIN_PHONE = "+5511972741849"


async def refresh_availability_cache():
    """Background job to refresh availability cache every hour."""
    from src.firebase_auth import FirebaseTokens

    try:
        logger.info("Running scheduled availability cache refresh...")
        services = get_services()

        # Get admin user's Beyond token (with auto-refresh)
        valid_token = services.beyond_tokens.get_valid_id_token(ADMIN_PHONE)

        if not valid_token:
            logger.warning(f"Skipping scheduled refresh - no valid Beyond token for {ADMIN_PHONE}")
            return

        # Get full token info to initialize API
        user_token = services.beyond_tokens.get_token(ADMIN_PHONE)
        if not user_token:
            logger.warning("Skipping scheduled refresh - token info not found")
            return

        # Initialize Beyond API with admin tokens
        tokens = FirebaseTokens(
            id_token=user_token.id_token,
            refresh_token=user_token.refresh_token,
            expires_at=user_token.expires_at
        )
        services.auth.initialize_with_tokens(tokens)

        # Scan availability
        services.availability.scan_availability()
        logger.info("Scheduled availability cache refresh completed")

    except Exception as e:
        logger.error(f"Scheduled availability refresh failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global scheduler

    logger.info("Starting Beyond The Club API...")

    # Initialize services on startup
    get_services()
    logger.info("Services initialized")

    # Start scheduler for background jobs
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_availability_cache,
        trigger=CronTrigger(minute=0),  # Run at minute 0 of every hour (00:00, 01:00, etc.)
        id="availability_refresh",
        name="Refresh availability cache every hour at :00",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Background scheduler started - availability refresh at every hour :00 using {ADMIN_PHONE}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    close_services()


app = FastAPI(
    title="Beyond The Club API",
    description="API for managing sport session bookings at Beyond The Club",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "beyond-the-club-api"}


# Include API v1 routes
app.include_router(v1_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """API root endpoint."""
    return {
        "name": "Beyond The Club API",
        "version": "1.0.0",
        "docs": "/docs"
    }
