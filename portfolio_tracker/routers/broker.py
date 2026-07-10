"""Broker integration API endpoints.

Thin HTTP layer: request parsing, error→status mapping, response shaping.
Credential handling lives in ``services.broker_accounts``; portfolio
synchronization in ``services.broker_sync``; per-broker API adapters in
``portfolio_tracker.brokers``.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from kiteconnect import KiteConnect
from sqlalchemy.orm import Session

from portfolio_tracker import schemas
from portfolio_tracker.brokers.zerodha import ZerodhaBroker
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel
from portfolio_tracker.repositories import broker_configs
from portfolio_tracker.services import broker_accounts, broker_sync

logger = logging.getLogger(__name__)

router = APIRouter()

ZERODHA_NOT_CONNECTED_MSG = (
    "Zerodha not connected. Please (re)connect Zerodha from the Brokers page and ensure "
    "ZERODHA_REDIRECT_URL is set to http://localhost:8000/app/brokers."
)


# ── Generic config endpoints ──────────────────────────────────────────────────

@router.get("/configs", response_model=list[schemas.BrokerConfigResponse])
def get_broker_configs(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all broker configurations for current user."""
    try:
        configs = broker_configs.get_broker_configs_by_user(db, user.id)
        return [
            schemas.BrokerConfigResponse(
                id=config.id,
                user_id=config.user_id,
                broker_name=config.broker_name,
                broker_user_id=config.broker_user_id or "",
                is_active=config.is_active,
                # is_authorized: True if an access token exists
                is_authorized=bool(config.access_token),
                last_synced=config.last_synced,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in configs
        ]
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/configs/{config_id}")
def delete_broker_config(
    config_id: int,
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a broker configuration."""
    try:
        config = broker_configs.get_broker_config(db, config_id)
        if not config or config.user_id != user.id:
            raise HTTPException(status_code=404, detail="Broker config not found")

        broker_configs.delete_broker_config(db, config_id)
        return {"success": True, "message": "Broker config deleted"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ── Zerodha ───────────────────────────────────────────────────────────────────

@router.post("/zerodha/setup")
def setup_zerodha_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    consent_given: bool = Query(False),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup Zerodha broker with API credentials."""
    try:
        # Test the credentials by creating a broker instance
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        login_url = broker.get_login_url()

        config = broker_accounts.save_credentials(
            db, user, "zerodha",
            api_key=api_key,
            api_secret=api_secret,
            consent_given=consent_given,
        )

        return {
            "success": True,
            "login_url": login_url,
            "message": "Zerodha API credentials saved. Please login to authorize.",
            "config_id": config.id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup Zerodha: {str(e)}"
        )


@router.post("/zerodha/callback")
def zerodha_callback(
    request_token: str = Query(...),
    config_id: Optional[int] = Query(default=None),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle Zerodha OAuth callback."""
    try:
        if config_id is not None:
            config = broker_configs.get_broker_config(db, config_id)
        else:
            config = broker_configs.get_broker_config_by_broker_name(db, user.id, "zerodha")

        if not config or config.user_id != user.id:
            raise ValueError("Broker config not found")

        api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
        if not api_key or not api_secret:
            raise ValueError("API credentials not found")

        # Exchange request token for access token
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        access_token = broker.set_access_token(request_token, api_secret)

        # Get user profile
        broker.set_token(access_token)
        profile = broker.get_profile()
        broker_user_id = profile.get("user_id", "")

        broker_accounts.store_access_token(
            db, config, access_token,
            broker_user_id=broker_user_id,
            last_synced=datetime.now(timezone.utc),
        )

        return {
            "success": True,
            "message": "Zerodha broker connected successfully",
            "broker_user_id": broker_user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Zerodha: {str(e)}"
        )


@router.get("/zerodha/login-url")
def get_zerodha_login_url(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Zerodha login URL for authorization (legacy endpoint)."""
    try:
        broker: Optional[ZerodhaBroker] = None
        config = broker_configs.get_broker_config_by_broker_name(db, user.id, "zerodha")

        if config and config.api_key:
            api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
            if not api_key:
                raise ValueError("Stored Zerodha API key is invalid or missing")
            broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret or None)
        else:
            broker = ZerodhaBroker()

        login_url = broker.get_login_url()
        return {"login_url": login_url, "broker": "zerodha"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Failed to get login URL: "
                "Zerodha API credentials are not configured. "
                "Please provide them via /api/broker/zerodha/setup or set "
                "ZERODHA_API_KEY/ZERODHA_API_SECRET in the environment."
                if "ZERODHA_API_KEY not configured" in str(e)
                else f"Failed to get login URL: {str(e)}"
            )
        )


def _authorized_zerodha_client(config) -> ZerodhaBroker:
    """Decrypt, validate and return a ready-to-use Zerodha client.

    Validation is deliberately step-by-step so each failure mode surfaces a
    specific, actionable error message (token expiry is the common case).
    """
    try:
        api_key, api_secret, access_token = broker_accounts.decrypt_credentials(config)
    except Exception as decrypt_error:
        logger.error(f"Failed to decrypt credentials: {decrypt_error}")
        raise ValueError(f"Failed to decrypt Zerodha credentials: {str(decrypt_error)}")

    if not api_key.strip():
        raise ValueError("API key is empty - Zerodha not properly configured")
    if not access_token.strip():
        raise ValueError("Access token is empty - Zerodha not properly configured")

    # Validate the session with a lightweight profile call before syncing
    try:
        kite = KiteConnect(api_key=api_key)
    except Exception as kite_error:
        raise ValueError(f"Failed to initialize KiteConnect: {str(kite_error)}")
    try:
        kite.set_access_token(access_token)
    except Exception as token_error:
        raise ValueError(f"Failed to set access token: {str(token_error)}")
    try:
        kite.profile()
    except Exception as profile_error:
        error_details = f"{str(profile_error)}"
        if hasattr(profile_error, 'code'):
            error_details += f" (code: {profile_error.code})"
        if hasattr(profile_error, 'response'):
            error_details += f" (response: {profile_error.response})"
        logger.warning(
            "Zerodha profile API failed - access token likely expired; "
            "reconnect Zerodha from the Brokers page."
        )
        raise ValueError(f"Invalid Zerodha credentials - profile API failed: {error_details}")

    broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
    broker.set_token(access_token)
    try:
        broker.get_profile()
    except Exception as profile_error:
        raise ValueError(f"Authentication failed: {str(profile_error)}")

    return broker


@router.post("/zerodha/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_zerodha_holdings(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync holdings from Zerodha to portfolio."""
    try:
        config = broker_accounts.get_config_or_error(
            db, user.id, "zerodha",
            missing_msg=ZERODHA_NOT_CONNECTED_MSG,
            require_token=True,
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        broker = _authorized_zerodha_client(config)
        holdings = broker.get_holdings()

        assets_imported = broker_sync.upsert_holdings(db, portfolio_id, holdings)

        broker_configs.update_broker_config(
            db, config.id, last_synced=datetime.now(timezone.utc)
        )

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported
        )
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/zerodha/sync-transactions", response_model=schemas.BrokerTransactionsSyncResponse)
def sync_zerodha_transactions(
    portfolio_id: int = Query(...),
    historical: bool = Query(default=False, description="Fetch historical trades (all orders) instead of recent trades only"),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync trades from Zerodha into portfolio transactions."""
    try:
        config = broker_accounts.get_config_or_error(
            db, user.id, "zerodha",
            missing_msg=ZERODHA_NOT_CONNECTED_MSG,
            require_token=True,
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        try:
            api_key, api_secret, access_token = broker_accounts.decrypt_credentials(config)
        except Exception as decrypt_error:
            raise ValueError(f"Failed to decrypt Zerodha credentials: {str(decrypt_error)}")

        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)

        if historical:
            trades = broker.get_historical_trades()
        else:
            trades = broker.get_trades()
        logger.info(f"Fetched {len(trades)} {'historical ' if historical else ''}trades from Zerodha")

        imported = broker_sync.import_trades(db, portfolio_id, trades, source_label="Zerodha")

        broker_configs.update_broker_config(db, config.id, last_synced=datetime.now(timezone.utc))

        return schemas.BrokerTransactionsSyncResponse(
            success=True,
            message=f"Successfully synced {len(trades)} trades",
            transactions_count=len(trades),
            transactions_imported=imported,
        )
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Angel ─────────────────────────────────────────────────────────────────────

@router.post("/angel/setup")
def setup_angel_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    consent_given: bool = Query(False),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setup Angel broker with API credentials."""
    try:
        from portfolio_tracker.brokers.angel import AngelBroker

        # Test the credentials
        broker = AngelBroker(api_key=api_key, api_secret=api_secret)
        profile = broker.get_profile()

        broker_accounts.save_credentials(
            db, user, "angel",
            broker_user_id=profile.get("user_id", ""),
            api_key=api_key,
            api_secret=api_secret,
            consent_given=consent_given,
        )

        return {
            "success": True,
            "message": "Angel broker connected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup Angel: {str(e)}"
        )


@router.post("/angel/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_angel_holdings(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync holdings from Angel to portfolio."""
    try:
        from portfolio_tracker.brokers.angel import AngelBroker

        config = broker_accounts.get_config_or_error(
            db, user.id, "angel", missing_msg="Angel not connected"
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
        broker = AngelBroker(api_key=api_key, api_secret=api_secret)
        holdings = broker.get_holdings()

        assets_imported = broker_sync.upsert_holdings(db, portfolio_id, holdings)
        broker_configs.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ── 5Paisa ────────────────────────────────────────────────────────────────────

def _fivepaisa_client(config):
    """Build a FivePaisaBroker from a stored (encrypted) config."""
    from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker

    api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
    extra = broker_accounts.load_extra_config(config)
    return FivePaisaBroker(
        api_key=api_key,
        api_secret=api_secret,
        app_name=extra.get("app_name", ""),
        app_source=extra.get("app_source", ""),
        user_id=extra.get("user_id", ""),
        password=extra.get("password", ""),
    )


@router.post("/fivepaisa/setup")
def setup_fivepaisa_broker(
    user_key: Optional[str] = Query(None, description="5Paisa User Key (VendorKey)"),
    encryption_key: Optional[str] = Query(None, description="5Paisa Encryption Key"),
    api_key: Optional[str] = Query(None, description="Legacy alias for user_key"),
    api_secret: Optional[str] = Query(None, description="Legacy alias for encryption_key"),
    app_name: Optional[str] = Query(None, description="5Paisa App Name"),
    app_source: Optional[str] = Query(None, description="5Paisa App Source"),
    user_id_5p: Optional[str] = Query(None, description="5Paisa User ID"),
    password: Optional[str] = Query(None, description="5Paisa Password"),
    consent_given: bool = Query(False),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setup 5Paisa broker with all required credentials.

    Backwards-compatible: accepts legacy `api_key`/`api_secret` (aliases for
    `user_key` / `encryption_key`) and makes the extra fields optional so tests
    that only supply `api_key`/`api_secret` continue to work.
    """
    # Support legacy param names and provide sensible defaults for optional fields
    effective_user_key = user_key or api_key
    effective_encryption_key = encryption_key or api_secret
    extra_config = {
        "app_name": app_name or "",
        "app_source": app_source or "",
        "user_id": user_id_5p or "",
        "password": password or "",
    }

    try:
        from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker

        # Test creating the broker (validates credentials format)
        broker = FivePaisaBroker(
            api_key=effective_user_key,
            api_secret=effective_encryption_key,
            app_name=extra_config["app_name"],
            app_source=extra_config["app_source"],
            user_id=extra_config["user_id"],
            password=extra_config["password"],
        )
        profile = broker.get_profile()

        broker_accounts.save_credentials(
            db, user, "fivepaisa",
            broker_user_id=profile.get("user_id", extra_config["user_id"]),
            api_key=effective_user_key or "",
            api_secret=effective_encryption_key or "",
            extra_config=extra_config,
            consent_given=consent_given,
        )

        return {"success": True, "message": "5Paisa broker connected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup 5Paisa: {str(e)}",
        )


@router.get("/fivepaisa/login-url")
def get_fivepaisa_login_url(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get 5Paisa OAuth login URL."""
    try:
        config = broker_accounts.get_config_or_error(
            db, user.id, "fivepaisa",
            missing_msg="5Paisa not connected. Set up API credentials first.",
        )
        broker = _fivepaisa_client(config)
        return {"login_url": broker.get_login_url()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/fivepaisa/callback")
def fivepaisa_oauth_callback(
    request_token: str = Query(..., description="OAuth request token from 5Paisa redirect"),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete 5Paisa OAuth flow with request token."""
    try:
        config = broker_accounts.get_config_or_error(
            db, user.id, "fivepaisa",
            missing_msg="5Paisa not connected. Set up API credentials first.",
        )
        broker = _fivepaisa_client(config)

        access_token = broker.set_access_token(request_token)
        if not access_token:
            # Token exchange failed. Do NOT persist the one-time request_token as
            # the access token — that would mark the broker "authorized" with an
            # unusable credential and every later sync would fail opaquely.
            logger.error("5Paisa callback: token exchange returned no access token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="5Paisa authorization failed: could not obtain an access token. Please try logging in again.",
            )

        broker_accounts.store_access_token(
            db, config, access_token,
            broker_user_id=broker.client_code or config.broker_user_id,
        )

        return {
            "success": True,
            "message": "5Paisa authorization successful",
            "client_code": broker.client_code
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"5Paisa callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"5Paisa OAuth failed: {str(e)}"
        )


@router.post("/fivepaisa/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_fivepaisa_holdings(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync holdings from 5Paisa to portfolio."""
    try:
        config = broker_accounts.get_config_or_error(
            db, user.id, "fivepaisa",
            missing_msg="5Paisa not connected",
            require_token=True,
            unauthorized_msg="5Paisa not authorized. Please complete the login flow.",
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        _, _, access_token = broker_accounts.decrypt_credentials(config)
        broker = _fivepaisa_client(config)
        broker.set_token(access_token, config.broker_user_id)
        holdings = broker.get_holdings()

        assets_imported = broker_sync.upsert_holdings(db, portfolio_id, holdings)
        broker_configs.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ── Dhan ──────────────────────────────────────────────────────────────────────

@router.post("/dhan/setup")
def setup_dhan_broker(
    client_id: str = Query(..., description="Dhan Client ID from developer portal"),
    access_token: str = Query(..., description="Dhan Access Token from developer portal"),
    consent_given: bool = Query(False),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setup Dhan broker with Client ID and Access Token (no OAuth redirect needed)."""
    try:
        from portfolio_tracker.brokers.dhan import DhanBroker

        broker = DhanBroker(client_id=client_id, access_token=access_token)
        profile = broker.get_profile()

        config = broker_accounts.save_credentials(
            db, user, "dhan",
            broker_user_id=profile.get("user_id", client_id),
            api_key=client_id,
            access_token=access_token,
            consent_given=consent_given,
        )

        return {
            "success": True,
            "message": "Dhan broker connected successfully",
            "config_id": config.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup Dhan: {str(e)}",
        )


@router.post("/dhan/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_dhan_holdings(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync holdings from Dhan to portfolio."""
    try:
        from portfolio_tracker.brokers.dhan import DhanBroker

        config = broker_accounts.get_config_or_error(
            db, user.id, "dhan",
            missing_msg="Dhan not connected. Please connect Dhan from the Brokers page.",
            require_token=True,
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        client_id, _, access_token = broker_accounts.decrypt_credentials(config)
        broker = DhanBroker(client_id=client_id, access_token=access_token)
        holdings = broker.get_holdings()

        assets_imported = broker_sync.upsert_holdings(db, portfolio_id, holdings)
        broker_configs.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported,
        )
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Groww ─────────────────────────────────────────────────────────────────────

@router.post("/groww/setup")
def setup_groww_broker(
    api_key: str = Query(..., description="Groww Client ID / API Key"),
    api_secret: str = Query(..., description="Groww Client Secret / API Secret"),
    consent_given: bool = Query(False),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save Groww API credentials and return OAuth login URL."""
    try:
        from portfolio_tracker.brokers.groww import GrowwBroker

        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        login_url = broker.get_login_url()

        config = broker_accounts.save_credentials(
            db, user, "groww",
            api_key=api_key,
            api_secret=api_secret,
            consent_given=consent_given,
        )

        return {
            "success": True,
            "login_url": login_url,
            "message": "Groww credentials saved. Please complete OAuth authorization.",
            "config_id": config.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup Groww: {str(e)}",
        )


@router.get("/groww/login-url")
def get_groww_login_url(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Groww OAuth login URL from stored credentials."""
    try:
        from portfolio_tracker.brokers.groww import GrowwBroker

        config = broker_configs.get_broker_config_by_broker_name(db, user.id, "groww")
        if not config or not config.api_key:
            raise ValueError("Groww not configured. Please save API credentials first.")

        api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        return {"login_url": broker.get_login_url(), "broker": "groww"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/groww/callback")
def groww_callback(
    request_token: str = Query(..., description="Authorization code from Groww OAuth redirect"),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete Groww OAuth flow with the authorization code."""
    try:
        from portfolio_tracker.brokers.groww import GrowwBroker

        config = broker_accounts.get_config_or_error(
            db, user.id, "groww",
            missing_msg="Groww config not found. Please save API credentials first.",
        )

        api_key, api_secret, _ = broker_accounts.decrypt_credentials(config)
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        access_token = broker.set_access_token(request_token)
        profile = broker.get_profile()

        broker_accounts.store_access_token(
            db, config, access_token,
            broker_user_id=profile.get("user_id", ""),
        )

        return {"success": True, "message": "Groww broker connected successfully"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Groww OAuth failed: {str(e)}",
        )


@router.post("/groww/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_groww_holdings(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync holdings from Groww to portfolio."""
    try:
        from portfolio_tracker.brokers.groww import GrowwBroker

        config = broker_accounts.get_config_or_error(
            db, user.id, "groww",
            missing_msg="Groww not connected. Please authorize via the Brokers page.",
            require_token=True,
        )
        broker_sync.require_portfolio(db, user.id, portfolio_id)

        api_key, api_secret, access_token = broker_accounts.decrypt_credentials(config)
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)
        holdings = broker.get_holdings()

        assets_imported = broker_sync.upsert_holdings(db, portfolio_id, holdings)
        broker_configs.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported,
        )
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
