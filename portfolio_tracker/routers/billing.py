"""Billing and subscription management endpoints (Razorpay)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from portfolio_tracker.config import settings
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import (PLAN_LIMITS, check_broker_limit,
                                    get_current_user,
                                    get_export_count_this_month)
from portfolio_tracker.models import ProcessedPaymentModel, UserModel

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


class VerifyPaymentRequest(BaseModel):
    """Razorpay checkout handler output.

    Sent as a JSON body, never as query parameters: these identifiers are
    bearer-equivalent for the duration of the order and query strings are
    written to access logs, proxy logs and browser history.
    """

    payment_id: str = Field(min_length=1, max_length=100)
    order_id: str = Field(min_length=1, max_length=100)
    signature: str = Field(min_length=1, max_length=256)


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
    body: VerifyPaymentRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify the Razorpay payment for a Pro upgrade and grant the tier.

    A valid signature proves only that *some* real Razorpay order was paid. It
    says nothing about who paid, how much, or whether this payment has already
    been redeemed. All four checks are required before granting anything:

      1. signature   — the order/payment pair came from Razorpay
      2. ownership   — the order was created for *this* user
      3. amount      — the order was for the Pro price, not a cheaper one
      4. uniqueness  — this payment has not already been redeemed

    Mirrors ``verify_options_credits_payment`` below, which already did this.
    """
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment service not configured.")

    order_id = body.order_id
    payment_id = body.payment_id

    # (1) Verify HMAC-SHA256 signature.
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, body.signature):
        logger.warning("Rejected verify-payment for user %s: bad signature", user.id)
        raise HTTPException(status_code=400, detail="Invalid payment signature. Payment not verified.")

    # (2) + (3) Fetch the order server-side. Neither the payer's identity nor
    # the amount is part of the signed payload, so both must come from Razorpay.
    client = _razorpay_client()
    try:
        order = client.order.fetch(order_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Razorpay order fetch failed for %s: %s", order_id, exc)
        raise HTTPException(
            status_code=502, detail="Could not verify order with payment gateway."
        ) from exc

    order_user_id = str((order.get("notes") or {}).get("user_id", ""))
    if order_user_id != str(user.id):
        logger.warning(
            "Rejected verify-payment: order %s belongs to user %r, caller is %s",
            order_id, order_user_id, user.id,
        )
        raise HTTPException(status_code=403, detail="This payment belongs to a different account.")

    if int(order.get("amount", 0)) != PRO_PRICE_PAISE:
        logger.warning(
            "Rejected verify-payment: order %s amount %s != Pro price %d",
            order_id, order.get("amount"), PRO_PRICE_PAISE,
        )
        raise HTTPException(status_code=400, detail="Payment amount does not match the Pro plan price.")

    if order.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order is not marked paid yet. Please retry shortly.")

    # (4) Replay guard. Recorded *before* the grant, so a concurrent duplicate
    # loses the race on the UNIQUE payment_id and is rejected having granted
    # nothing. Also gives finance a row per fulfilment to reconcile against.
    db.add(ProcessedPaymentModel(
        user_id=user.id,
        payment_id=payment_id,
        order_id=order_id,
        purpose="pro_subscription",
        pack_id="pro_monthly",
        amount_paise=PRO_PRICE_PAISE,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment has already been processed.")

    # Extend rather than overwrite, so a renewal paid before expiry is not
    # silently truncated to 30 days from today.
    now = datetime.now(timezone.utc)
    current_expiry = user.subscription_expires_at
    if current_expiry is not None and current_expiry.tzinfo is None:
        current_expiry = current_expiry.replace(tzinfo=timezone.utc)
    base = current_expiry if (current_expiry and current_expiry > now) else now

    user.subscription_tier = "pro"
    user.subscription_status = "active"
    user.subscription_expires_at = base + timedelta(days=30)
    db.commit()

    logger.info(
        "User %s upgraded to Pro via order %s (payment %s), expires %s",
        user.id, order_id, payment_id, user.subscription_expires_at,
    )
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

    # Fail CLOSED. This endpoint is unauthenticated and grants paid tiers, so an
    # unset secret must disable it rather than skip verification — previously a
    # missing RAZORPAY_WEBHOOK_SECRET turned it into an open "make me Pro" API.
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is not configured — rejecting")
        raise HTTPException(status_code=503, detail="Webhook processing is not configured.")

    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Rejected Razorpay webhook: invalid signature")
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


# Admin/dev override for options_tier WITHOUT payment. Disabled by default so it
# can never hand out paid tiers in production; the real paid path is
# /options-starter-activate (verified) and Razorpay recurring for pro/elite.
ALLOW_TIER_OVERRIDE = os.getenv("ALLOW_OPTIONS_TIER_OVERRIDE", "").lower() in ("1", "true", "yes")


@router.post("/options-upgrade")
def options_upgrade(
    payload: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Admin/dev-only tier override. No payment is taken, so it is gated behind
    ALLOW_OPTIONS_TIER_OVERRIDE and returns 403 unless explicitly enabled.
    Paid upgrades must go through the verified Razorpay flows.
    """
    if not ALLOW_TIER_OVERRIDE:
        raise HTTPException(
            status_code=403,
            detail="Tier upgrades must be completed through the payment flow.",
        )

    target_tier: str = payload.get("tier", "")
    if target_tier not in _OPTIONS_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{target_tier}'. Must be one of {_OPTIONS_TIERS}.")

    # Users start at 'free' (not in _OPTIONS_TIERS), so treat any unknown/unset
    # current tier as below the lowest paid tier instead of crashing on .index().
    current_tier = getattr(user, "options_tier", None) or "free"
    current_idx = _OPTIONS_TIERS.index(current_tier) if current_tier in _OPTIONS_TIERS else -1
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
        # Absence of a Razorpay key is a misconfiguration, not a licence to give
        # paid credits away: on a real deployment a dropped env var used to turn
        # this endpoint into free credits for anyone who asked.
        if settings.IS_PRODUCTION:
            logger.error("options-credits called but Razorpay keys are not configured")
            raise HTTPException(
                status_code=503,
                detail="Payment service is not configured. Contact the administrator.",
            )
        # Local development only — grant directly so checkout can be exercised.
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

    credits_to_add, price_paise = _CREDIT_PACKS[pack_id]

    # Verify HMAC-SHA256 signature (proves order_id/payment_id came from Razorpay).
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    # Guard against pack escalation: pack_id is NOT part of the signed payload, so
    # confirm the order was actually created for this pack's price server-side.
    try:
        import razorpay  # type: ignore[import]
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.fetch(order_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Razorpay order fetch failed for %s: %s", order_id, exc)
        raise HTTPException(status_code=502, detail="Could not verify order with payment gateway.") from exc

    if int(order.get("amount", 0)) != price_paise:
        logger.warning(
            "Order %s amount %s does not match pack %s price %d — rejecting",
            order_id, order.get("amount"), pack_id, price_paise,
        )
        raise HTTPException(status_code=400, detail="Payment amount does not match the selected pack.")
    if order.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order is not marked paid yet. Please retry shortly.")

    # Idempotency / replay guard: record the payment first, keyed on a UNIQUE
    # payment_id. A repeated verify for the same payment loses the race here and
    # is rejected before any credits are granted.
    db.add(ProcessedPaymentModel(
        user_id=user.id,
        payment_id=payment_id,
        order_id=order_id,
        purpose="options_credits",
        pack_id=pack_id,
        amount_paise=price_paise,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This payment has already been processed.")

    user.options_credits = (getattr(user, "options_credits", 0) or 0) + credits_to_add  # type: ignore[assignment]
    db.commit()
    logger.info("Verified payment %s — added %d credits to user %d", payment_id, credits_to_add, user.id)
    return {"success": True, "credits_added": credits_to_add}
