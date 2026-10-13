from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.errors import (
    AppError,
    app_error_handler,
    unhandled_exception_handler,
)
from backend.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up in %s mode", settings.ENVIRONMENT)
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Recruiter decision-support tool for resume extraction, "
        "matching, and explainable ranking."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Suitable for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized error handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
