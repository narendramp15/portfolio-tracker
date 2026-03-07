"""Billing and subscription management endpoints (Razorpay)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from portfolio_tracker.database import get_db
from portfolio_tracker.deps import (PLAN_LIMITS, check_broker_limit,
                                    get_current_user,
                                    get_export_count_this_month)
from portfolio_tracker.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Razorpay configuration (set via environment variables)
# ---------------------------------------------------------------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
# Create a monthly plan in your Razorpay dashboard and paste the plan_id here:
RAZORPAY_PLAN_ID_PRO = os.getenv("RAZORPAY_PLAN_ID_PRO", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

PRO_PRICE_PAISE = 19900  # ₹199 × 100 paise


def _razorpay_client():
    """Return an authenticated Razorpay client, or raise 503 if not configured."""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Payment service is not configured. Contact the administrator.",
        )
    try:
        import razorpay  # optional dep — only needed when billing is active
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Payment library not installed. Run: pip install razorpay",
        )
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/subscription")
def get_subscription_status(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's subscription tier, limits, and monthly usage."""
    tier = (user.subscription_tier or "free").lower()
    limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["free"])
    export_count = get_export_count_this_month(user, db)

    return {
        "tier": tier,
        "status": user.subscription_status or "active",
        "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        "limits": limits,
        "usage": {
            "exports_this_month": export_count,
        },
        "razorpay_key_id": RAZORPAY_KEY_ID or None,
    }


@router.post("/create-order")
def create_razorpay_order(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Razorpay order for a one-month Pro upgrade (₹199).
    The frontend uses the returned order_id to open the Razorpay checkout.
    """
    client = _razorpay_client()
    receipt = f"pro_{user.id}_{int(datetime.now(timezone.utc).timestamp())}"
    try:
        order = client.order.create(
            {
                "amount": PRO_PRICE_PAISE,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "user_id": str(user.id),
                    "plan": "pro_monthly",
                },
            }
        )
    except Exception as exc:
        logger.error(f"Razorpay order creation failed: {exc}")
        raise HTTPException(status_code=400, detail=f"Failed to create payment order: {exc}")

    return {
        "order_id": order["id"],
        "amount": PRO_PRICE_PAISE,
        "currency": "INR",
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "user_email": user.email,
        "user_name": user.full_name or user.username,
    }


@router.post("/create-subscription")
def create_razorpay_subscription(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Razorpay recurring subscription for the Pro monthly plan.
    Requires RAZORPAY_PLAN_ID_PRO to be configured.
    """
    if not RAZORPAY_PLAN_ID_PRO:
        raise HTTPException(
            status_code=503,
            detail="Subscription plans not configured. Use one-time order checkout instead.",
        )
    client = _razorpay_client()
    try:
        subscription = client.subscription.create(
            {
                "plan_id": RAZORPAY_PLAN_ID_PRO,
                "total_count": 12,
                "customer_notify": 1,
                "notes": {
                    "user_id": str(user.id),
                    "email": user.email,
                },
            }
        )
    except Exception as exc:
        logger.error(f"Razorpay subscription creation failed: {exc}")
        raise HTTPException(status_code=400, detail=f"Failed to create subscription: {exc}")

    user.razorpay_subscription_id = subscription["id"]
    db.commit()

    return {
        "subscription_id": subscription["id"],
        "razorpay_key_id": RAZORPAY_KEY_ID,
    }


@router.post("/verify-payment")
def verify_razorpay_payment(
    payment_id: str = Query(...),
    order_id: str = Query(...),
    signature: str = Query(...),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify the Razorpay payment signature after checkout and upgrade the user to Pro.
    The frontend calls this with the values returned by the Razorpay checkout handler.
    """
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment service not configured.")

    # Verify HMAC-SHA256 signature
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature. Payment not verified.")

    # Upgrade user to Pro for 30 days
    user.subscription_tier = "pro"
    user.subscription_status = "active"
    user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()

    logger.info(f"User {user.id} upgraded to Pro via order {order_id}")
    return {"success": True, "tier": "pro", "message": "Upgraded to Pro successfully!"}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Razorpay webhook events for automatic subscription lifecycle management.
    Configure this URL in your Razorpay dashboard: POST /api/billing/webhook
    """
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # Verify webhook signature when secret is configured
    if RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event = event_data.get("event", "")
    logger.info(f"Razorpay webhook received: {event}")

    if event in ("subscription.activated", "subscription.charged"):
        _handle_subscription_activated(event_data, db)
    elif event == "payment.captured":
        _handle_payment_captured(event_data, db)
    elif event in ("subscription.cancelled", "subscription.halted", "subscription.completed"):
        _handle_subscription_cancelled(event_data, db)

    return {"status": "ok"}


def _handle_subscription_activated(event_data: dict, db: Session) -> None:
    payload = event_data.get("payload", {}).get("subscription", {}).get("entity", {})
    notes = payload.get("notes", {})
    user_id = notes.get("user_id")
    if user_id:
        user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
        if user:
            user.subscription_tier = "pro"
            user.subscription_status = "active"
            user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=31)
            db.commit()
            logger.info(f"User {user_id} activated Pro via webhook")


def _handle_payment_captured(event_data: dict, db: Session) -> None:
    """Handle one-time order payment captured (for non-subscription upgrades)."""
    payload = event_data.get("payload", {}).get("payment", {}).get("entity", {})
    notes = payload.get("notes", {})
    user_id = notes.get("user_id")
    plan = notes.get("plan", "")
    if user_id and "pro" in plan:
        user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
        if user:
            user.subscription_tier = "pro"
            user.subscription_status = "active"
            user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            db.commit()
            logger.info(f"User {user_id} upgraded to Pro via payment.captured webhook")


def _handle_subscription_cancelled(event_data: dict, db: Session) -> None:
    payload = event_data.get("payload", {}).get("subscription", {}).get("entity", {})
    notes = payload.get("notes", {})
    user_id = notes.get("user_id")
    if user_id:
        user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
        if user:
            user.subscription_status = "cancelled"
            db.commit()
            logger.info(f"User {user_id} subscription cancelled via webhook")


@router.post("/cancel")
def cancel_subscription(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel the user's active Razorpay subscription (at end of current billing cycle).
    Access continues until subscription_expires_at.
    """
    subscription_id = user.razorpay_subscription_id

    if subscription_id and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            client = _razorpay_client()
            client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 1})
        except Exception as exc:
            logger.warning(f"Razorpay cancel API call failed: {exc} — marking locally cancelled")

    user.subscription_status = "cancelled"
    db.commit()

    return {
        "success": True,
        "message": "Subscription cancelled. Pro access continues until the end of your billing period.",
    }
