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


# ─── Options Analyzer tier upgrade ───────────────────────────────────────────

_OPTIONS_TIERS = ("starter", "pro", "elite")
_OPTIONS_TIER_LABELS = {"starter": "Starter", "pro": "Pro", "elite": "Elite"}

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# Starter plan payment link (static Razorpay payment link shared with users)
STARTER_PAYMENT_LINK = os.getenv("RAZORPAY_STARTER_PAYMENT_LINK", "https://rzp.io/rzp/y3LwB3p")
# The Razorpay Payment Link ID (plink_XXXXXXXX) for the Starter plan.
# Set this to enforce that the payment came from YOUR specific payment link,
# not just any ₹99 payment in your account.
# Find it: Razorpay Dashboard → Payment Links → copy the ID from the link URL/details.
STARTER_LINK_ID = os.getenv("RAZORPAY_STARTER_LINK_ID", "")  # e.g. plink_XXXXXXXXXXXXXXXX
STARTER_PRICE_PAISE = 9900  # ₹99 × 100

# Credit pack definitions: id → (credits, price_paise)
_CREDIT_PACKS: dict[str, tuple[int, int]] = {
    "starter_pack": (10, 9900),
    "growth_pack": (40, 29900),
    "power_pack": (120, 74900),
}


@router.post("/options-upgrade")
def options_upgrade(
    payload: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Immediately upgrades the user's options_tier (no payment — billing handled
    via Razorpay recurring outside this flow, or as a simple admin override).
    For production, integrate a real payment check before applying.
    """
    target_tier: str = payload.get("tier", "")
    if target_tier not in _OPTIONS_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{target_tier}'. Must be one of {_OPTIONS_TIERS}.")

    current_idx = _OPTIONS_TIERS.index(getattr(user, "options_tier", "starter"))
    target_idx = _OPTIONS_TIERS.index(target_tier)
    if target_idx <= current_idx:
        raise HTTPException(status_code=400, detail="Cannot downgrade tier via this endpoint.")

    user.options_tier = target_tier  # type: ignore[assignment]
    db.commit()
    db.refresh(user)
    logger.info("User %d upgraded options tier to %s", user.id, target_tier)
    return {"success": True, "tier": target_tier, "tier_label": _OPTIONS_TIER_LABELS[target_tier]}


@router.get("/options-starter-link")
def get_starter_payment_link(
    user: UserModel = Depends(get_current_user),
) -> dict:
    """Return the Starter plan payment link so the frontend can open it."""
    return {"payment_link": STARTER_PAYMENT_LINK, "price_inr": 99}


@router.post("/options-starter-activate")
def options_starter_activate(
    payload: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verifies a Razorpay payment for the Starter plan and upgrades the user.

    Flow:
      1. User opens the shared Razorpay payment link (STARTER_PAYMENT_LINK) in their browser.
      2. After paying, the user copies their Payment ID (starts with 'pay_') from the
         Razorpay confirmation screen or email.
      3. Frontend POSTs that payment_id here for server-side verification via the
         Razorpay fetch-payment API.
      4. If the payment is captured and the amount is ≥ ₹99, the user's options_tier
         is set to 'starter'.
    """
    payment_id: str = payload.get("payment_id", "").strip()
    if not payment_id or not payment_id.startswith("pay_"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Payment ID. It must start with 'pay_' — find it in your Razorpay confirmation email.",
        )

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Payment verification is not configured on the server. Contact support.",
        )

    # ── Security check 1: Prevent reuse of the same payment ID across accounts ──
    # DB-level UNIQUE constraint is the backstop, but we check here first for a
    # cleaner error message.
    existing = db.query(UserModel).filter(UserModel.options_starter_payment_id == payment_id).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This Payment ID has already been used to activate an account. Each payment can only activate one account.",
        )

    try:
        import razorpay  # type: ignore[import]
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        payment = client.payment.fetch(payment_id)
    except Exception as exc:
        logger.error("Razorpay payment fetch failed for %s: %s", payment_id, exc)
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment with payment gateway. Please try again.",
        ) from exc

    if payment.get("status") != "captured":
        raise HTTPException(
            status_code=400,
            detail="Payment is not yet captured. Please wait a few seconds and try again.",
        )
    if payment.get("amount", 0) < STARTER_PRICE_PAISE:
        raise HTTPException(
            status_code=400,
            detail="Payment amount does not match the Starter plan price (₹99).",
        )
    if payment.get("currency", "INR") != "INR":
        raise HTTPException(status_code=400, detail="Payment currency must be INR.")

    # ── Security check 2: Verify payment came from our specific payment link ──
    # Razorpay sets 'payment_link_id' on payments made via a Payment Link.
    # If RAZORPAY_STARTER_LINK_ID is configured, reject payments from other sources.
    if STARTER_LINK_ID:
        payment_link_id = payment.get("payment_link_id") or ""
        if payment_link_id != STARTER_LINK_ID:
            logger.warning(
                "Payment %s has payment_link_id=%r, expected %r — rejecting",
                payment_id, payment_link_id, STARTER_LINK_ID,
            )
            raise HTTPException(
                status_code=400,
                detail="Payment was not made via the official Starter plan link. Please use the link on the billing page.",
            )

    # ── Activate starter tier and record the payment ID ──
    user.options_tier = "starter"  # type: ignore[assignment]
    user.options_starter_payment_id = payment_id  # type: ignore[assignment]  — prevents reuse
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Most likely a race-condition duplicate (UNIQUE violation on options_starter_payment_id)
        raise HTTPException(
            status_code=409,
            detail="This Payment ID has already been used to activate another account.",
        )
    db.refresh(user)
    logger.info("User %d activated Starter tier via payment %s", user.id, payment_id)
    return {"success": True, "tier": "starter", "tier_label": "Starter"}


@router.post("/options-credits")
def buy_options_credits(
    payload: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Creates a Razorpay order for a credit pack purchase.
    If Razorpay is not configured, credits are added directly (dev/test mode).
    """
    pack_id: str = payload.get("pack_id", "")
    if pack_id not in _CREDIT_PACKS:
        raise HTTPException(status_code=400, detail=f"Unknown pack '{pack_id}'.")

    credits_to_add, price_paise = _CREDIT_PACKS[pack_id]

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        # Dev mode — add credits directly without payment
        user.options_credits = (getattr(user, "options_credits", 0) or 0) + credits_to_add  # type: ignore[assignment]
        db.commit()
        logger.info("Dev mode: added %d credits to user %d", credits_to_add, user.id)
        return {"credits_added": credits_to_add, "dev_mode": True}

    try:
        import razorpay  # type: ignore[import]
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": price_paise,
            "currency": "INR",
            "receipt": f"opt_credits_{user.id}_{pack_id}",
            "notes": {"user_id": str(user.id), "pack_id": pack_id, "credits": str(credits_to_add)},
        })
        return {
            "razorpay_order_id": order["id"],
            "razorpay_key": RAZORPAY_KEY_ID,
            "amount": price_paise,
            "pack_id": pack_id,
            "credits": credits_to_add,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Razorpay order creation failed: %s", exc)
        raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.") from exc


@router.post("/options-credits/verify")
def verify_options_credits_payment(
    payload: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verifies Razorpay payment signature and adds credits to the user's account.
    Called by the frontend after a successful Razorpay checkout.
    """
    order_id: str = payload.get("razorpay_order_id", "")
    payment_id: str = payload.get("razorpay_payment_id", "")
    signature: str = payload.get("razorpay_signature", "")
    pack_id: str = payload.get("pack_id", "")

    if not all([order_id, payment_id, signature, pack_id]):
        raise HTTPException(status_code=400, detail="Missing payment verification fields.")
    if pack_id not in _CREDIT_PACKS:
        raise HTTPException(status_code=400, detail=f"Unknown pack '{pack_id}'.")

    # Verify HMAC-SHA256 signature
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    credits_to_add, _ = _CREDIT_PACKS[pack_id]
    user.options_credits = (getattr(user, "options_credits", 0) or 0) + credits_to_add  # type: ignore[assignment]
    db.commit()
    logger.info("Verified payment — added %d credits to user %d", credits_to_add, user.id)
    return {"success": True, "credits_added": credits_to_add}
