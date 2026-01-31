"""Shared FastAPI dependencies (auth, user context)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from portfolio_tracker.auth import decode_access_token
from portfolio_tracker.database import get_db
from portfolio_tracker.models import UserModel

logger = logging.getLogger(__name__)


def get_access_token(request: Request, token: Optional[str] = Query(default=None)) -> str:
    """
    Get access token from either query param `token` or `Authorization: Bearer ...` header.
    """
    if token:
        logger.debug("Token extracted from query parameter")
        return token

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        logger.debug("Token extracted from Authorization header")
        return auth_header.split(" ", 1)[1].strip()

    logger.warning(f"No token found - Path: {request.url.path}, Headers: {dict(request.headers)}")
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
        logger.warning(f"User not found for email: {email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user

