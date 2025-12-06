"""FastAPI application factory for the ELEANOR Moral Ops Center."""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from eje.api import endpoints
from eje.api.auth import create_auth_dependency, security
from eje.api.validation import validation_exception_handler, pydantic_exception_handler
from eje.config.settings import Settings, get_settings
from eje.db import escalation_log
from eje.learning.context_model import DissentAwareContextModel

logger = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build a production-ready FastAPI app with full validation and monitoring.
    
    Features:
    - OAuth2 Bearer token authentication with audit trail (Task 10.4)
    - Strict Pydantic validation (Task 10.2)
    - Custom error handlers with clear messages
    - CORS middleware
    - Database initialization
    - Learning model integration
    - Uptime tracking
    
    Args:
        settings: Optional settings object (uses defaults if not provided)
        
    Returns:
        Configured FastAPI application
    """

    settings = settings or get_settings()
    settings.validate_security()
    
    app = FastAPI(
        title="ELEANOR Moral Ops Center",
        version="1.0.0",
        description="Ethical AI governance and decision-making API with OAuth2 Bearer authentication",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Application state
    app.state.settings = settings
    app.state.version = "1.0.0"
    app.state.start_time = time.time()
    app.logger = logger
    app.state.error_stats = {"errors": 0, "total": 0, "last_error_rate": 0.0}

    # Register custom validation exception handlers (Task 10.2)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_exception_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.on_event("startup")
    async def _startup():
        """Initialize application components on startup."""
        logger.info("Starting ELEANOR Moral Ops Center...")
        
        # Load configuration
        app.state.config = endpoints.load_config(settings.config_path)
        logger.info(f"Loaded configuration from {settings.config_path}")
        
        # Initialize learning model
        app.state.context_model = DissentAwareContextModel()
        logger.info("Initialized context learning model")
        
        # Initialize database
        engine = escalation_log.get_engine(settings.db_path)
        escalation_log.init_db(engine)
        app.state.engine = engine
        logger.info(f"Database initialized at {settings.db_path}")
        
        # Log authentication status
        if settings.require_api_token:
            logger.info("API authentication ENABLED - Bearer token required")
        else:
            logger.warning("API authentication DISABLED - All requests allowed")
        
        logger.info("Ops Center startup complete")

    @app.on_event("shutdown")
    async def _shutdown():
        """Clean up resources on shutdown."""
        logger.info("Shutting down ELEANOR Moral Ops Center...")

    # Create authentication dependency (Task 10.4)
    auth_dependency = create_auth_dependency(settings)
    
    # Include API router with authentication
    # The security parameter makes FastAPI display the auth in OpenAPI docs
    app.include_router(
        endpoints.router,
        dependencies=[Depends(security), Depends(auth_dependency)],
    )
    
    return app
