import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.router import router as api_router
from core.config import config
from core.db import engine
from core.exceptions.base import CustomException
from core.logging import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info(f"Starting {config.APP_NAME}...")
    yield
    # Shutdown
    logger.info(f"Shutting down {config.APP_NAME}...")
    await engine.dispose()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CSF Backend",
        description="CSF Youth Sports Registration Platform API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    cors_config = {
        "allow_origins": config.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }

    # Add regex pattern for wildcard subdomain support (e.g., *.yourdomain.com)
    if config.cors_origin_regex:
        cors_config["allow_origin_regex"] = config.cors_origin_regex

    app.add_middleware(CORSMiddleware, **cors_config)

    # Custom exception handler
    @app.exception_handler(CustomException)
    async def custom_exception_handler(
        request: Request, exc: CustomException
    ) -> JSONResponse:
        logger.warning(f"CustomException: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "data": exc.data,
            },
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "version": "0.1.0",
            "app_name": config.APP_NAME,
        }

    # Include API routers
    app.include_router(api_router, prefix="/api")

    # Mount static files for uploads (photos, attachments, etc.)
    app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

    return app


app = create_app()
