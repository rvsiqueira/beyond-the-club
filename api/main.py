"""
FastAPI application entry point.

Configures the API with all routes, middleware, and error handling.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .v1.router import router as v1_router
from .deps import get_services, close_services

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    logger.info("Starting Beyond The Club API...")

    # Initialize services on startup
    get_services()
    logger.info("Services initialized")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
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
