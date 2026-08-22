"""Shared FastAPI dependencies (auth, user context).

Plan-limit / quota logic lives in ``portfolio_tracker.services.entitlements``;
the names are re-exported here for backwards compatibility with existing
routers and tests. New code should import them from the service directly.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from portfolio_tracker.auth import decode_access_token
from portfolio_tracker.database import get_db
from portfolio_tracker.models import UserModel

# Backwards-compatible re-exports (previously defined in this module)
from portfolio_tracker.services.entitlements import (  # noqa: F401
    PLAN_LIMITS,
    check_broker_limit,
    check_export_limit,
    get_export_count_this_month,
    get_plan_limits,
    log_export,
)

logger = logging.getLogger(__name__)


def get_access_token(request: Request) -> str:
    """Extract the bearer token from the ``Authorization`` header.

    The header is the only accepted location. A previous ``?token=`` query
    parameter was removed: query strings are recorded in web-server and
    reverse-proxy access logs, browser history and outbound ``Referer``
    headers, so accepting a 30-day bearer token there leaked long-lived
    full-account credentials into places we neither control nor can purge.
    """
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()

    logger.warning("No bearer token on request - Path: %s", request.url.path)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_user(
    access_token: str = Depends(get_access_token), db: Session = Depends(get_db)
) -> UserModel:
    """Resolve current user from JWT token."""
    email = decode_access_token(access_token)
    if not email:
        logger.warning("Token decode failed - invalid token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        logger.warning("Token decoded but no matching user exists")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
