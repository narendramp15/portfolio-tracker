"""Broker integration API endpoints."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.brokers.zerodha import ZerodhaBroker
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.models import AssetModel, TransactionModel
from portfolio_tracker.models import UserModel

router = APIRouter()


@router.post("/zerodha/setup")
def setup_zerodha_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup Zerodha broker with API credentials."""
    try:
        user_id = user.id
        
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
    config_id: Optional[int] = Query(default=None),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle Zerodha OAuth callback."""
    try:
        user_id = user.id
        
        # Get broker config
        if config_id is not None:
            config = crud.get_broker_config(db, config_id)
        else:
            config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")

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
            config.id,
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
def get_zerodha_login_url(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Zerodha login URL for authorization (legacy endpoint)."""
    try:
        user_id = user.id
        
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
def get_broker_configs(
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all broker configurations for current user."""
    try:
        configs = crud.get_broker_configs_by_user(db, user.id)
        return configs
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
        user_id = user.id
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
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync holdings from Zerodha to portfolio."""
    try:
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")
        if not config or not config.access_token:
            raise ValueError(
                "Zerodha not connected. Please (re)connect Zerodha from the Brokers page and ensure "
                "ZERODHA_REDIRECT_URL is set to http://localhost:8000/app/brokers."
            )
        
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


@router.post("/zerodha/sync-transactions", response_model=schemas.BrokerTransactionsSyncResponse)
def sync_zerodha_transactions(
    portfolio_id: int = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync recent trades from Zerodha into portfolio transactions."""
    try:
        user_id = user.id

        config = crud.get_broker_config_by_broker_name(db, user_id, "zerodha")
        if not config or not config.access_token:
            raise ValueError(
                "Zerodha not connected. Please (re)connect Zerodha from the Brokers page and ensure "
                "ZERODHA_REDIRECT_URL is set to http://localhost:8000/app/brokers."
            )

        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")

        access_token = EncryptionManager.decrypt(config.access_token)
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")

        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)
        trades = broker.get_trades()

        imported = 0
        for trade in trades:
            symbol = trade.get("tradingsymbol") or trade.get("symbol") or ""
            if not symbol:
                continue

            tx_type_raw = trade.get("transaction_type") or trade.get("trade_type") or ""
            tx_type = str(tx_type_raw).strip().lower()
            if tx_type in {"buy", "b"}:
                tx_type = "buy"
            elif tx_type in {"sell", "s"}:
                tx_type = "sell"
            elif str(tx_type_raw).upper() in {"BUY", "SELL"}:
                tx_type = str(tx_type_raw).lower()
            else:
                continue

            quantity = trade.get("quantity") or 0
            price = trade.get("average_price") or trade.get("price") or 0

            # Parse timestamp if available
            ts = trade.get("exchange_timestamp") or trade.get("order_timestamp") or trade.get("trade_timestamp")
            tx_dt = None
            if isinstance(ts, datetime):
                tx_dt = ts
            elif isinstance(ts, str) and ts:
                try:
                    tx_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    tx_dt = None
            if tx_dt is None:
                tx_dt = datetime.now(timezone.utc)
            if tx_dt.tzinfo is None:
                tx_dt = tx_dt.replace(tzinfo=timezone.utc)

            # Ensure asset exists in the portfolio.
            asset = (
                db.query(AssetModel)
                .filter(AssetModel.portfolio_id == portfolio_id, AssetModel.symbol == symbol)
                .first()
            )
            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    name=symbol,
                    quantity=0,
                    current_price=price or 0,
                    purchase_price=price or 0,
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)

            # Avoid duplicates by matching key fields.
            existing = (
                db.query(TransactionModel)
                .filter(
                    TransactionModel.portfolio_id == portfolio_id,
                    TransactionModel.asset_id == asset.id,
                    TransactionModel.type == tx_type,
                    TransactionModel.quantity == quantity,
                    TransactionModel.price == price,
                    TransactionModel.transaction_date == tx_dt,
                )
                .first()
            )
            if existing:
                continue

            note = trade.get("trade_id")
            notes = f"Imported from Zerodha trade {note}" if note else "Imported from Zerodha"

            tx = TransactionModel(
                portfolio_id=portfolio_id,
                asset_id=asset.id,
                type=tx_type,
                quantity=quantity,
                price=price,
                notes=notes,
                transaction_date=tx_dt,
            )
            db.add(tx)
            imported += 1

        if imported:
            db.commit()

        crud.update_broker_config(db, config.id, last_synced=datetime.now(timezone.utc))

        return schemas.BrokerTransactionsSyncResponse(
            success=True,
            message=f"Successfully synced {len(trades)} trades",
            transactions_count=len(trades),
            transactions_imported=imported,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Angel Broker Endpoints
@router.post("/angel/setup")
def setup_angel_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setup Angel broker with API credentials."""
    try:
        from portfolio_tracker.brokers.angel import AngelBroker
        
        user_id = user.id
        
        # Test the credentials
        broker = AngelBroker(api_key=api_key, api_secret=api_secret)
        profile = broker.get_profile()
        
        # Save broker config with encrypted credentials
        config = crud.get_broker_config_by_broker_name(db, user_id, "angel")
        
        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                broker_user_id=profile.get("user_id", "")
            )
        else:
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="angel",
                broker_user_id=profile.get("user_id", ""),
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret)
            )
        
        return {
            "success": True,
            "message": "Angel broker connected successfully"
        }
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
        
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, "angel")
        if not config:
            raise ValueError("Angel not connected")
        
        # Get portfolio
        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")
        
        # Decrypt credentials
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        broker = AngelBroker(api_key=api_key, api_secret=api_secret)
        holdings = broker.get_holdings()
        
        # Create or update assets
        assets_imported = 0
        for holding in holdings:
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == holding.symbol
            ).first()
            
            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=holding.symbol,
                    name=holding.symbol,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.quantity = holding.quantity
                asset.current_price = holding.current_price
                asset.purchase_price = holding.average_price
            
            db.commit()
        
        crud.update_broker_config(db, config.id)
        
        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# 5Paisa Broker Endpoints
@router.post("/fivepaisa/setup")
def setup_fivepaisa_broker(
    api_key: str = Query(...),
    api_secret: str = Query(...),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setup 5Paisa broker with API credentials."""
    try:
        from portfolio_tracker.brokers.fivepaisa import FivepaIsaBroker
        
        user_id = user.id
        
        # Test the credentials
        broker = FivepaIsaBroker(api_key=api_key, api_secret=api_secret)
        profile = broker.get_profile()
        
        # Save broker config with encrypted credentials
        config = crud.get_broker_config_by_broker_name(db, user_id, "fivepaisa")
        
        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                broker_user_id=profile.get("user_id", "")
            )
        else:
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="fivepaisa",
                broker_user_id=profile.get("user_id", ""),
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret)
            )
        
        return {
            "success": True,
            "message": "5Paisa broker connected successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to setup 5Paisa: {str(e)}"
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
        from portfolio_tracker.brokers.fivepaisa import FivepaIsaBroker
        
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, "fivepaisa")
        if not config:
            raise ValueError("5Paisa not connected")
        
        # Get portfolio
        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")
        
        # Decrypt credentials
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        broker = FivepaIsaBroker(api_key=api_key, api_secret=api_secret)
        holdings = broker.get_holdings()
        
        # Create or update assets
        assets_imported = 0
        for holding in holdings:
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == holding.symbol
            ).first()
            
            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=holding.symbol,
                    name=holding.symbol,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.quantity = holding.quantity
                asset.current_price = holding.current_price
                asset.purchase_price = holding.average_price
            
            db.commit()
        
        crud.update_broker_config(db, config.id)
        
        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
