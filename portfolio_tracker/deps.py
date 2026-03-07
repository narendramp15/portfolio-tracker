"""Shared FastAPI dependencies (auth, user context)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from portfolio_tracker.auth import decode_access_token
from portfolio_tracker.database import get_db
from portfolio_tracker.models import (BrokerConfigModel, ExportLogModel,
                                      UserModel)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Plan limits
# ---------------------------------------------------------------------------

PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "max_brokers": 2,
        "exports_per_month": 3,
        "auto_sync": "daily",
    },
    "pro": {
        "max_brokers": 5,
        "exports_per_month": None,  # unlimited
        "auto_sync": "hourly",
    },
    "teams": {
        "max_brokers": None,  # unlimited
        "exports_per_month": None,
        "auto_sync": "hourly",
    },
}


def get_plan_limits(user: UserModel) -> dict:
    """Return the plan-specific limits dict for a user."""
    tier = (user.subscription_tier or "free").lower()
    return PLAN_LIMITS.get(tier, PLAN_LIMITS["free"])


def get_export_count_this_month(user: UserModel, db: Session) -> int:
    """Return how many exports the user has performed in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(ExportLogModel)
        .filter(
            ExportLogModel.user_id == user.id,
            ExportLogModel.created_at >= month_start,
        )
        .count()
    )


def check_export_limit(user: UserModel, db: Session) -> None:
    """Raise HTTP 402 if the user has exhausted their monthly export quota."""
    limits = get_plan_limits(user)
    max_exports = limits["exports_per_month"]
    if max_exports is None:
        return  # unlimited on paid plans
    count = get_export_count_this_month(user, db)
    if count >= max_exports:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Export limit reached ({count}/{max_exports} this month on the Free plan). "
                "Upgrade to Pro for unlimited exports."
            ),
        )


def log_export(user: UserModel, export_type: str, db: Session) -> None:
    """Record a CSV export event for rate-limiting purposes."""
    db.add(ExportLogModel(user_id=user.id, export_type=export_type))
    db.commit()


def check_broker_limit(user: UserModel, db: Session) -> None:
    """Raise HTTP 402 if the user has reached their broker connection limit."""
    limits = get_plan_limits(user)
    max_brokers = limits["max_brokers"]
    if max_brokers is None:
        return  # unlimited
    count = (
        db.query(BrokerConfigModel)
        .filter(
            BrokerConfigModel.user_id == user.id,
            BrokerConfigModel.is_active == True,  # noqa: E712
        )
        .count()
    )
    if count >= max_brokers:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Broker limit reached ({count}/{max_brokers} on the Free plan). "
                "Upgrade to Pro to connect up to 5 brokers."
            ),
        )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


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

