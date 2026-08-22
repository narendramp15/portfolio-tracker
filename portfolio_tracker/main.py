"""Application composition root.

This module only *assembles* the application: logging, middleware, routers,
static mounts. All HTTP plumbing lives in ``portfolio_tracker.api``; business
logic lives in ``portfolio_tracker.services``; persistence in
``portfolio_tracker.repositories``.

Exported names (stable — referenced by deployment entry points):
    ``app``          — outermost ASGI callable (passenger_wsgi.py, render.yaml)
    ``fastapi_app``  — inner FastAPI instance (tests need dependency_overrides)
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from portfolio_tracker.api.middleware import (CORSPreflightMiddleware,
                                              RequestLoggingMiddleware,
                                              SecurityHeadersMiddleware)
from portfolio_tracker.api.pages import mount_static
from portfolio_tracker.api.pages import router as pages_router
from portfolio_tracker.api.routes import register_routes
from portfolio_tracker.config import settings, validate_or_die
from portfolio_tracker.database import create_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and fully wire the FastAPI application (inner app, unwrapped)."""
    app = FastAPI(
        title="Portfolio Tracker",
        description="A modern Python portfolio tracking application",
        version="1.0.0",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"422 Validation error on {request.method} {request.url}: {exc.errors()}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # MIDDLEWARE ORDER MATTERS!
    # Middleware added first runs LAST in the request chain
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["Content-Disposition", "X-Total-Count"],
        max_age=3600,
    )
    # Added last => outermost of the FastAPI stack, so the headers land on every
    # response including those short-circuited by CORSMiddleware.
    app.add_middleware(SecurityHeadersMiddleware)

    mount_static(app)
    register_routes(app)
    app.include_router(pages_router)

    return app


# Refuse to boot a real deployment that is missing critical secrets. This runs
# before anything touches the database or serves a request, because both of the
# secrets it checks have silent, unsafe fallbacks.
validate_or_die()

# Create tables on startup
create_tables()

# Log configuration on startup (helps debug production issues)
logger.info(f"✓ CORS Origins configured: {settings.CORS_ORIGINS}")
logger.info(f"✓ Frontend URL: {settings.FRONTEND_URL}")
logger.info(f"✓ Google OAuth: {'Configured' if settings.GOOGLE_CLIENT_ID else 'Not configured'}")

# Expose the FastAPI app for testing (tests need dependency_overrides)
fastapi_app = create_app()

# Wrap with raw ASGI CORS preflight handler (outermost layer, catches OPTIONS
# before SessionMiddleware can reject them)
app = CORSPreflightMiddleware(fastapi_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
