"""FastAPI application factory for the ELEANOR Moral Ops Center."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from eje.api import endpoints
from eje.api.validation import validation_exception_handler, pydantic_exception_handler
from eje.config.settings import Settings, get_settings
from eje.db import escalation_log
from eje.learning.context_model import DissentAwareContextModel

logger = logging.getLogger(__name__)


security = HTTPBearer(auto_error=False)


def verify_bearer(settings: Settings):
    def dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if not settings.api_token and settings.require_api_token:
            raise HTTPException(status_code=500, detail="API token not configured")
        if not settings.api_token:
            return None
        if not credentials or credentials.credentials != settings.api_token:
            raise HTTPException(status_code=401, detail="Invalid or missing API token")
        return credentials

    return dependency


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build a FastAPI app with shared config, DB, and learning helpers."""

    settings = settings or get_settings()
    settings.validate_security()
    app = FastAPI(title="ELEANOR Moral Ops Center", version="1.0.0")
    app.state.settings = settings
    app.state.version = "1.0.0"
    app.logger = logger
    app.state.error_stats = {"errors": 0, "total": 0, "last_error_rate": 0.0}

    # Register custom validation exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.on_event("startup")
    async def _startup():
        app.state.config = endpoints.load_config(settings.config_path)
        app.state.context_model = DissentAwareContextModel()
        engine = escalation_log.get_engine(settings.db_path)
        escalation_log.init_db(engine)
        app.state.engine = engine
        logger.info("Ops Center initialized with config=%s db=%s", settings.config_path, settings.db_path)

    app.include_router(
        endpoints.router,
        dependencies=[Depends(verify_bearer(settings))],
    )
    return app
