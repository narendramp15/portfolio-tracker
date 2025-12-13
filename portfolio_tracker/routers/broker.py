"""Broker integration API endpoints."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.auth import decode_access_token
from portfolio_tracker.brokers.zerodha import ZerodhaBroker
from portfolio_tracker.database import get_db
from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.models import AssetModel

router = APIRouter()


def get_current_user_id(token: str = Query(...)) -> int:
    """Get current user ID from JWT token."""
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user from database
    from portfolio_tracker.database import SessionLocal
    from portfolio_tracker.models import UserModel
    
    db = SessionLocal()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    db.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user.id


@router.post("/zerodha/setup")
def setup_zerodha_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Setup Zerodha broker with API credentials."""
    try:
        user_id = get_current_user_id(token)
        
        # Test the credentials by creating a broker instance
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        
        # Get login URL
        login_url = broker.get_login_url()
        
        # Save broker config with encrypted credentials
        config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")
        
        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret)
            )
        else:
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="zerodha",
                broker_user_id="",
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret)
            )
        
        return {
            "success": True,
            "login_url": login_url,
            "message": "Zerodha API credentials saved. Please login to authorize.",
            "config_id": config.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup Zerodha: {str(e)}"
        )


@router.post("/zerodha/callback")
def zerodha_callback(
    request_token: str = Query(...),
    config_id: int = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle Zerodha OAuth callback."""
    try:
        user_id = get_current_user_id(token)
        
        # Get broker config
        config = crud.get_broker_config(db, config_id)
        if not config or config.user_id != user_id:
            raise ValueError("Broker config not found")
        
        # Decrypt API credentials
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        if not api_key or not api_secret:
            raise ValueError("API credentials not found")
        
        # Exchange request token for access token
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        access_token = broker.set_access_token(request_token, api_secret)
        
        # Get user profile
        broker.set_token(access_token)
        profile = broker.get_profile()
        broker_user_id = profile.get("user_id", "")
        
        # Update broker config with access token and user ID
        config = crud.update_broker_config(
            db,
            config_id,
            access_token=EncryptionManager.encrypt(access_token),
            broker_user_id=broker_user_id,
            last_synced=datetime.now(timezone.utc)
        )
        
        return {
            "success": True,
            "message": "Zerodha broker connected successfully",
            "broker_user_id": broker_user_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Zerodha: {str(e)}"
        )


@router.get("/zerodha/login-url")
def get_zerodha_login_url(token: str = Query(...), db: Session = Depends(get_db)):
    """Get Zerodha login URL for authorization (legacy endpoint)."""
    try:
        user_id = get_current_user_id(token)
        
        broker: Optional[ZerodhaBroker] = None
        config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")
        
        if config and config.api_key:
            api_key = EncryptionManager.decrypt(config.api_key)
            api_secret = EncryptionManager.decrypt(config.api_secret or "")
            
            if not api_key:
                raise ValueError("Stored Zerodha API key is invalid or missing")
            
            broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret or None)
        else:
            broker = ZerodhaBroker()
        
        login_url = broker.get_login_url()
        return {"login_url": login_url, "broker": "zerodha"}
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


@router.get("/configs", response_model=list[schemas.BrokerConfigResponse])
def get_broker_configs(token: str = Query(...), db: Session = Depends(get_db)):
    """Get all broker configurations for current user."""
    try:
        user_id = get_current_user_id(token)
        configs = crud.get_broker_configs_by_user(db, user_id)
        return configs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/configs/{config_id}")
def delete_broker_config(config_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    """Delete a broker configuration."""
    try:
        user_id = get_current_user_id(token)
        config = crud.get_broker_config(db, config_id)
        
        if not config or config.user_id != user_id:
            raise HTTPException(status_code=404, detail="Broker config not found")
        
        crud.delete_broker_config(db, config_id)
        return {"success": True, "message": "Broker config deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/zerodha/sync-holdings", response_model=schemas.BrokerSyncResponse)
def sync_zerodha_holdings(
    portfolio_id: int = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Sync holdings from Zerodha to portfolio."""
    try:
        user_id = get_current_user_id(token)
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")
        if not config or not config.access_token:
            raise ValueError("Zerodha not connected")
        
        # Get portfolio
        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")
        
        # Decrypt access token and create broker instance
        access_token = EncryptionManager.decrypt(config.access_token)
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)
        holdings = broker.get_holdings()
        
        # Create or update assets in portfolio
        assets_imported = 0
        for holding in holdings:
            # Check if asset exists
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == holding.symbol
            ).first()
            
            if not asset:
                # Create new asset
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=holding.symbol,
                    name=holding.symbol,  # Use symbol as name, can be updated later
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                # Update existing asset
                asset.quantity = holding.quantity
                asset.current_price = holding.current_price
                asset.purchase_price = holding.average_price
            
            db.commit()
        
        # Update last synced time
        crud.update_broker_config(db, config.id, last_synced=datetime.now(timezone.utc))
        
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
