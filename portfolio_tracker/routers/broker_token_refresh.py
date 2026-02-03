"""Broker token refresh and status endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from portfolio_tracker import crud
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.models import UserModel

router = APIRouter()


@router.post("/{broker_name}/refresh-token")
def refresh_broker_token(
    broker_name: str,
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh broker access token.
    
    For Zerodha: Access tokens don't expire unless revoked. This endpoint validates the token.
    For 5Paisa: Uses refresh token to get new access token.
    
    Returns:
        success: True if token is valid/refreshed
        message: Status message
        needs_reauth: True if user needs to manually re-authenticate
    """
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    broker_name = broker_name.lower()
    
    if broker_name not in ["zerodha", "fivepaisa"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported broker: {broker_name}"
        )
    
    try:
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, broker_name)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{broker_name.capitalize()} not connected"
            )
        
        # Decrypt credentials
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        access_token = EncryptionManager.decrypt(config.access_token or "")
        refresh_token = EncryptionManager.decrypt(config.refresh_token or "") if config.refresh_token else None
        
        if broker_name == "zerodha":
            from portfolio_tracker.brokers.zerodha import ZerodhaBroker
            
            broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
            
            if access_token:
                broker.set_token(access_token)
            
            # Check if token is valid
            if broker.is_token_valid():
                return {
                    "success": True,
                    "message": "Zerodha token is valid",
                    "needs_reauth": False,
                    "token_valid": True
                }
            else:
                # Token expired - Zerodha doesn't have refresh, need re-auth
                return {
                    "success": False,
                    "message": "Zerodha access token has expired. Please reconnect from the Brokers page.",
                    "needs_reauth": True,
                    "token_valid": False
                }
        
        elif broker_name == "fivepaisa":
            from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker

            # Load extra config
            extra = {}
            if config.extra_config:
                try:
                    decrypted_extra = EncryptionManager.decrypt(config.extra_config)
                    extra = json.loads(decrypted_extra)
                except Exception as e:
                    logger.warning(f"Failed to decrypt extra_config: {e}")
            
            broker = FivePaisaBroker(
                api_key=api_key,
                api_secret=api_secret,
                app_name=extra.get("app_name", ""),
                app_source=extra.get("app_source", ""),
                user_id=extra.get("user_id", ""),
                password=extra.get("password", ""),
                access_token=access_token,
                refresh_token=refresh_token,
            )
            
            # Check if token is valid
            if broker.is_token_valid():
                return {
                    "success": True,
                    "message": "5Paisa token is valid",
                    "needs_reauth": False,
                    "token_valid": True
                }
            
            # Try to refresh token
            if refresh_token:
                try:
                    new_access_token, new_refresh_token = broker.refresh_access_token()
                    
                    # Save new tokens
                    crud.update_broker_config(
                        db,
                        config.id,
                        access_token=EncryptionManager.encrypt(new_access_token),
                        refresh_token=EncryptionManager.encrypt(new_refresh_token) if new_refresh_token else None,
                    )
                    
                    return {
                        "success": True,
                        "message": "5Paisa token refreshed successfully",
                        "needs_reauth": False,
                        "token_valid": True
                    }
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh 5Paisa token: {refresh_error}")
                    return {
                        "success": False,
                        "message": f"Failed to refresh token: {str(refresh_error)}",
                        "needs_reauth": True,
                        "token_valid": False
                    }
            else:
                # No refresh token available
                return {
                    "success": False,
                    "message": "5Paisa session expired and no refresh token available. Please reconnect.",
                    "needs_reauth": True,
                    "token_valid": False
                }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error for {broker_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{broker_name}/status")
def get_broker_status(
    broker_name: str,
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get broker connection status including token validity.
    
    Returns:
        is_connected: Whether broker is connected
        token_valid: Whether current token is valid
        last_synced: Last successful sync timestamp
        needs_attention: True if user action may be required
    """
    import logging
    logger = logging.getLogger(__name__)
    
    broker_name = broker_name.lower()
    
    try:
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, broker_name)
        if not config:
            return {
                "is_connected": False,
                "token_valid": False,
                "last_synced": None,
                "needs_attention": False
            }
        
        # Check if token is valid
        token_valid = False
        if config.access_token:
            try:
                decrypted_token = EncryptionManager.decrypt(config.access_token)
                if decrypted_token:
                    token_valid = True
            except Exception as e:
                logger.warning(f"Failed to decrypt token for status check: {e}")
        
        return {
            "is_connected": True,
            "is_authorized": token_valid,
            "token_valid": token_valid,
            "last_synced": config.last_synced.isoformat() if config.last_synced else None,
            "needs_attention": not token_valid,
            "broker_user_id": config.broker_user_id or None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
