"""Subscription-plan entitlements: limits per tier and quota enforcement.

This is business policy, deliberately separate from HTTP auth (``deps``).
Raises ``HTTPException(402)`` on quota breach because callers are FastAPI
handlers; if a non-HTTP caller ever needs these rules, lift the status-code
mapping into the router layer.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from portfolio_tracker.models import BrokerConfigModel, ExportLogModel, UserModel

logger = logging.getLogger(__name__)

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
