"""Broker integration API endpoints."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from kiteconnect import KiteConnect
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.brokers.zerodha import ZerodhaBroker
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import check_broker_limit, get_current_user
from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.models import (AssetModel, BrokerConfigModel,
                                      TransactionModel, UserModel)
from portfolio_tracker.services.symbol_mapper import symbol_mapper

router = APIRouter()


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
                api_secret=EncryptionManager.encrypt(api_secret),
                consent_given=consent_given,
            )
        else:
            # Enforce plan broker limit only on NEW connections
            check_broker_limit(user, db)
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="zerodha",
                broker_user_id="",
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                consent_given=consent_given,
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        configs = crud.get_broker_configs_by_user(db, user.id)
        # Add is_authorized field based on whether access_token exists
        result = []
        for config in configs:
            has_token = bool(config.access_token)
            logger.info(f"Broker {config.broker_name}: access_token exists={has_token}, broker_user_id={config.broker_user_id}")
            config_dict = {
                "id": config.id,
                "user_id": config.user_id,
                "broker_name": config.broker_name,
                "broker_user_id": config.broker_user_id or "",
                "is_active": config.is_active,
                "is_authorized": has_token,  # True if access token exists
                "last_synced": config.last_synced,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }
            result.append(schemas.BrokerConfigResponse(**config_dict))
        return result
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
    import logging
    logger = logging.getLogger(__name__)

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
        try:
            access_token = EncryptionManager.decrypt(config.access_token)
            api_key = EncryptionManager.decrypt(config.api_key or "")
            api_secret = EncryptionManager.decrypt(config.api_secret or "")
            logger.info(f"✓ Credentials decrypted successfully")
        except Exception as decrypt_error:
            logger.error(f"✗ Failed to decrypt credentials: {str(decrypt_error)}")
            raise ValueError(f"Failed to decrypt Zerodha credentials: {str(decrypt_error)}")

        # Log credential details for debugging (not the actual values)
        logger.info(f"📋 API key: length={len(api_key)}, non-empty={bool(api_key.strip())}")
        logger.info(f"📋 API secret: length={len(api_secret)}, non-empty={bool(api_secret.strip())}")
        logger.info(f"📋 Access token: length={len(access_token)}, non-empty={bool(access_token.strip())}")
        logger.info(f"📋 Broker config: api_key_stored={bool(config.api_key)}, access_token_stored={bool(config.access_token)}")

        # Validate decrypted credentials are not empty
        if not api_key.strip():
            logger.error("✗ API key is empty after decryption")
            raise ValueError("API key is empty - Zerodha not properly configured")
        if not access_token.strip():
            logger.error("✗ Access token is empty after decryption")
            raise ValueError("Access token is empty - Zerodha not properly configured")

        # Test credentials with profile API call
        logger.info(f"🔐 Creating KiteConnect instance with api_key")
        try:
            kite = KiteConnect(api_key=api_key)
            logger.info(f"✓ KiteConnect instance created")
        except Exception as kite_error:
            logger.error(f"✗ Failed to create KiteConnect instance: {str(kite_error)}")
            raise ValueError(f"Failed to initialize KiteConnect: {str(kite_error)}")

        logger.info(f"🔐 Setting access token on KiteConnect")
        try:
            kite.set_access_token(access_token)
            logger.info(f"✓ Access token set successfully")
        except Exception as token_error:
            logger.error(f"✗ Failed to set access token: {str(token_error)}")
            raise ValueError(f"Failed to set access token: {str(token_error)}")

        logger.info(f"🔐 Calling profile API to validate credentials")
        try:
            profile = kite.profile()
            logger.info(f"✓ Profile API call successful: user_name={profile.get('user_name', 'Unknown')}, user_id={profile.get('user_id', 'Unknown')}")
        except Exception as profile_error:
            error_details = f"{str(profile_error)}"
            if hasattr(profile_error, 'code'):
                error_details += f" (code: {profile_error.code})"
            if hasattr(profile_error, 'response'):
                error_details += f" (response: {profile_error.response})"
            logger.error(f"✗ Profile API call failed: {error_details}")
            logger.warning(f"⚠️  This usually means: 1) Access token expired, 2) API key invalid, or 3) Network issue")
            logger.warning(f"⚠️  Solution: Try reconnecting Zerodha from the Brokers page")
            raise ValueError(f"Invalid Zerodha credentials - profile API failed: {error_details}")

        # Test the credentials by making a simple API call first
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)

        # Test with profile call first (lighter than holdings)
        try:
            profile = broker.get_profile()
            logger.info(f"Profile test successful for user {user_id}: {profile.get('user_id', 'unknown')}")
        except Exception as profile_error:
            logger.error(f"Profile test failed for user {user_id}: {str(profile_error)}")
            raise ValueError(f"Authentication failed: {str(profile_error)}")

        holdings = broker.get_holdings()
        
        # Create or update assets in portfolio
        assets_imported = 0
        for holding in holdings:
            # Normalize symbol to Yahoo Finance format
            normalized_symbol = symbol_mapper.normalize_broker_symbol(
                symbol=holding.symbol,
                exchange='NSE',  # Zerodha primarily uses NSE
                isin=holding.isin
            )
            
            # Get company name from Yahoo Finance
            company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol
            
            # Check if asset exists
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == normalized_symbol
            ).first()
            
            if not asset:
                # Create new asset
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=normalized_symbol,
                    name=company_name,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                # Update existing asset
                asset.name = company_name  # Update name in case it changed
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
    historical: bool = Query(default=False, description="Fetch historical trades (all orders) instead of recent trades only"),
    token: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync trades from Zerodha into portfolio transactions."""
    import logging
    logger = logging.getLogger(__name__)

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

        # Decrypt access token and create broker instance
        try:
            access_token = EncryptionManager.decrypt(config.access_token)
            api_key = EncryptionManager.decrypt(config.api_key or "")
            api_secret = EncryptionManager.decrypt(config.api_secret or "")
            logger.info(f"✓ Credentials decrypted successfully for trades sync")
        except Exception as decrypt_error:
            logger.error(f"✗ Failed to decrypt credentials: {str(decrypt_error)}")
            raise ValueError(f"Failed to decrypt Zerodha credentials: {str(decrypt_error)}")

        # Log credential details for debugging (not the actual values)
        logger.debug(f"📋 API key: length={len(api_key)}, non-empty={bool(api_key.strip())}")
        logger.debug(f"📋 API secret: length={len(api_secret)}, non-empty={bool(api_secret.strip())}")
        logger.debug(f"📋 Access token: length={len(access_token)}, non-empty={bool(access_token.strip())}")

        logger.info(f"🔐 Creating ZerodhaBroker for trades sync")
        broker = ZerodhaBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)
        
        if historical:
            logger.info(f"🔐 Fetching HISTORICAL trades from Zerodha (using orders API)")
            trades = broker.get_historical_trades()
            logger.info(f"✓ Successfully fetched {len(trades)} historical trades from Zerodha")
        else:
            logger.info(f"🔐 Fetching recent trades from Zerodha")
            trades = broker.get_trades()
            logger.info(f"✓ Successfully fetched {len(trades)} recent trades from Zerodha")

        if not trades:
            logger.info(f"ℹ️  No trades found in Zerodha account")

        imported = 0
        for idx, trade in enumerate(trades):
            symbol = trade.get("tradingsymbol") or trade.get("symbol") or ""
            if not symbol:
                logger.debug(f"Trade {idx}: Skipping - no symbol found")
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
                logger.debug(f"Trade {idx} ({symbol}): Skipping - invalid transaction type: {tx_type_raw}")
                continue

            quantity = trade.get("quantity") or 0
            price = trade.get("average_price") or trade.get("price") or 0

            logger.debug(f"Trade {idx}: {symbol} {tx_type} {quantity} @ {price}")

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
                logger.debug(f"Trade {idx}: {symbol} - duplicate, skipping")
                continue

            note = trade.get("trade_id")
            notes = f"Imported from Zerodha trade {note}" if note else "Imported from Zerodha"

            logger.debug(f"Trade {idx}: Creating transaction for {symbol} {tx_type} {quantity} @ {price}")
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
            logger.info(f"✓ Successfully imported {imported}/{len(trades)} trades")
        else:
            logger.info(f"ℹ️  No new trades to import (0/{len(trades)})")

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
    consent_given: bool = Query(False),
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
                broker_user_id=profile.get("user_id", ""),
                consent_given=consent_given,
            )
        else:
            check_broker_limit(user, db)
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="angel",
                broker_user_id=profile.get("user_id", ""),
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                consent_given=consent_given,
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
            # Normalize symbol to Yahoo Finance format
            normalized_symbol = symbol_mapper.normalize_broker_symbol(
                symbol=holding.symbol,
                exchange='NSE',
                isin=holding.isin
            )
            
            # Get company name from Yahoo Finance
            company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol
            
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == normalized_symbol
            ).first()
            
            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=normalized_symbol,
                    name=company_name,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.name = company_name
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
    import json

    # Support legacy param names and provide sensible defaults for optional fields
    effective_user_key = user_key or api_key
    effective_encryption_key = encryption_key or api_secret
    app_name = app_name or ""
    app_source = app_source or ""
    user_id_5p = user_id_5p or ""
    password = password or ""

    try:
        from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker

        db_user_id = user.id

        # Store extra config as encrypted JSON
        extra_config = {
            "app_name": app_name,
            "app_source": app_source,
            "user_id": user_id_5p,
            "password": password,
        }
        encrypted_extra = EncryptionManager.encrypt(json.dumps(extra_config))

        # Test creating the broker (validates credentials format)
        broker = FivePaisaBroker(
            api_key=effective_user_key,
            api_secret=effective_encryption_key,
            app_name=app_name,
            app_source=app_source,
            user_id=user_id_5p,
            password=password,
        )
        profile = broker.get_profile()

        # Save broker config with encrypted credentials
        config = crud.get_broker_config_by_broker_name(db, db_user_id, "fivepaisa")

        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(effective_user_key or ""),
                api_secret=EncryptionManager.encrypt(effective_encryption_key or ""),
                extra_config=encrypted_extra,
                broker_user_id=profile.get("user_id", user_id_5p),
                consent_given=consent_given,
            )
        else:
            check_broker_limit(user, db)
            config = crud.create_broker_config(
                db,
                user_id=db_user_id,
                broker_name="fivepaisa",
                broker_user_id=profile.get("user_id", user_id_5p),
                api_key=EncryptionManager.encrypt(effective_user_key or ""),
                api_secret=EncryptionManager.encrypt(effective_encryption_key or ""),
                extra_config=encrypted_extra,
                consent_given=consent_given,
            )

        return {"success": True, "message": "5Paisa broker connected successfully"}
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
    import json
    try:
        from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker
        
        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "fivepaisa")
        if not config:
            raise ValueError("5Paisa not connected. Set up API credentials first.")
        
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        # Load extra config for 5Paisa
        extra = {}
        if config.extra_config:
            try:
                decrypted_extra = EncryptionManager.decrypt(config.extra_config)
                extra = json.loads(decrypted_extra)
            except Exception:
                pass
        
        broker = FivePaisaBroker(
            api_key=api_key,
            api_secret=api_secret,
            app_name=extra.get("app_name", ""),
            app_source=extra.get("app_source", ""),
            user_id=extra.get("user_id", ""),
            password=extra.get("password", ""),
        )
        login_url = broker.get_login_url()
        
        return {"login_url": login_url}
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
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker
        
        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "fivepaisa")
        if not config:
            raise ValueError("5Paisa not connected. Set up API credentials first.")
        
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        
        # Load extra config for 5Paisa (app_name, app_source, user_id, password)
        extra = {}
        if config.extra_config:
            try:
                decrypted_extra = EncryptionManager.decrypt(config.extra_config)
                extra = json.loads(decrypted_extra)
            except Exception as e:
                logger.warning(f"Failed to decrypt extra_config: {e}")
        
        logger.info(f"5Paisa callback: Creating broker with all 6 credentials")
        broker = FivePaisaBroker(
            api_key=api_key,
            api_secret=api_secret,
            app_name=extra.get("app_name", ""),
            app_source=extra.get("app_source", ""),
            user_id=extra.get("user_id", ""),
            password=extra.get("password", ""),
        )
        
        logger.info(f"5Paisa callback: Calling set_access_token with token length={len(request_token)}")
        access_token = broker.set_access_token(request_token)
        
        logger.info(f"5Paisa callback: Got access_token length={len(access_token) if access_token else 0}, client_code={broker.client_code}")
        
        if not access_token:
            # Even if SDK fails, use the request_token as fallback
            logger.warning("5Paisa callback: access_token empty, using request_token as fallback")
            access_token = request_token
        
        # Save access token and client code to config
        crud.update_broker_config(
            db,
            config.id,
            access_token=EncryptionManager.encrypt(access_token),
            broker_user_id=broker.client_code or config.broker_user_id
        )
        
        logger.info(f"5Paisa callback: Saved config successfully")
        
        return {
            "success": True,
            "message": "5Paisa authorization successful",
            "client_code": broker.client_code
        }
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
        import json

        from portfolio_tracker.brokers.fivepaisa import FivePaisaBroker
        
        user_id = user.id
        
        # Get broker config
        config = crud.get_broker_config_by_broker_name(db, user_id, "fivepaisa")
        if not config:
            raise ValueError("5Paisa not connected")
        
        # Check for access token
        if not config.access_token:
            raise ValueError("5Paisa not authorized. Please complete the login flow.")
        
        # Get portfolio
        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")
        
        # Decrypt credentials
        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        access_token = EncryptionManager.decrypt(config.access_token)
        
        # Load extra config for 5Paisa (app_name, app_source, user_id, password)
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
        )
        broker.set_token(access_token, config.broker_user_id)
        holdings = broker.get_holdings()
        
        # Create or update assets
        assets_imported = 0
        for holding in holdings:
            # Normalize symbol to Yahoo Finance format
            normalized_symbol = symbol_mapper.normalize_broker_symbol(
                symbol=holding.symbol,
                exchange='NSE',
                isin=holding.isin
            )
            
            # Get company name from Yahoo Finance
            company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol
            
            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == normalized_symbol
            ).first()
            
            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=normalized_symbol,
                    name=company_name,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.name = company_name
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


# ── Dhan Broker Endpoints ─────────────────────────────────────────────────────

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

        user_id = user.id
        broker = DhanBroker(client_id=client_id, access_token=access_token)
        profile = broker.get_profile()

        config = crud.get_broker_config_by_broker_name(db, user_id, "dhan")
        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(client_id),
                access_token=EncryptionManager.encrypt(access_token),
                broker_user_id=profile.get("user_id", client_id),
                consent_given=consent_given,
            )
        else:
            check_broker_limit(user, db)
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="dhan",
                broker_user_id=profile.get("user_id", client_id),
                api_key=EncryptionManager.encrypt(client_id),
                access_token=EncryptionManager.encrypt(access_token),
                consent_given=consent_given,
            )

        return {
            "success": True,
            "message": "Dhan broker connected successfully",
            "config_id": config.id,
        }
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

        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "dhan")
        if not config or not config.access_token:
            raise ValueError("Dhan not connected. Please connect Dhan from the Brokers page.")

        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")

        client_id = EncryptionManager.decrypt(config.api_key or "")
        access_token = EncryptionManager.decrypt(config.access_token)

        broker = DhanBroker(client_id=client_id, access_token=access_token)
        holdings = broker.get_holdings()

        assets_imported = 0
        for holding in holdings:
            normalized_symbol = symbol_mapper.normalize_broker_symbol(
                symbol=holding.symbol,
                exchange="NSE",
                isin=holding.isin,
            )
            company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol

            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == normalized_symbol,
            ).first()

            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=normalized_symbol,
                    name=company_name,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.name = company_name
                asset.quantity = holding.quantity
                asset.current_price = holding.current_price
                asset.purchase_price = holding.average_price

            db.commit()

        crud.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Groww Broker Endpoints ────────────────────────────────────────────────────

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

        user_id = user.id
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        login_url = broker.get_login_url()

        config = crud.get_broker_config_by_broker_name(db, user_id, "groww")
        if config:
            config = crud.update_broker_config(
                db,
                config.id,
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                consent_given=consent_given,
            )
        else:
            check_broker_limit(user, db)
            config = crud.create_broker_config(
                db,
                user_id=user_id,
                broker_name="groww",
                broker_user_id="",
                api_key=EncryptionManager.encrypt(api_key),
                api_secret=EncryptionManager.encrypt(api_secret),
                consent_given=consent_given,
            )

        return {
            "success": True,
            "login_url": login_url,
            "message": "Groww credentials saved. Please complete OAuth authorization.",
            "config_id": config.id,
        }
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

        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "groww")
        if not config or not config.api_key:
            raise ValueError("Groww not configured. Please save API credentials first.")

        api_key = EncryptionManager.decrypt(config.api_key)
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        return {"login_url": broker.get_login_url(), "broker": "groww"}
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

        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "groww")
        if not config:
            raise ValueError("Groww config not found. Please save API credentials first.")

        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        access_token = broker.set_access_token(request_token)
        profile = broker.get_profile()

        crud.update_broker_config(
            db,
            config.id,
            access_token=EncryptionManager.encrypt(access_token),
            broker_user_id=profile.get("user_id", ""),
        )

        return {"success": True, "message": "Groww broker connected successfully"}
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

        user_id = user.id
        config = crud.get_broker_config_by_broker_name(db, user_id, "groww")
        if not config or not config.access_token:
            raise ValueError("Groww not connected. Please authorize via the Brokers page.")

        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError("Portfolio not found")

        api_key = EncryptionManager.decrypt(config.api_key or "")
        api_secret = EncryptionManager.decrypt(config.api_secret or "")
        access_token = EncryptionManager.decrypt(config.access_token)

        broker = GrowwBroker(api_key=api_key, api_secret=api_secret)
        broker.set_token(access_token)
        holdings = broker.get_holdings()

        assets_imported = 0
        for holding in holdings:
            normalized_symbol = symbol_mapper.normalize_broker_symbol(
                symbol=holding.symbol,
                exchange="NSE",
                isin=holding.isin,
            )
            company_name = symbol_mapper.get_company_name(normalized_symbol) or holding.symbol

            asset = db.query(AssetModel).filter(
                AssetModel.portfolio_id == portfolio_id,
                AssetModel.symbol == normalized_symbol,
            ).first()

            if not asset:
                asset = AssetModel(
                    portfolio_id=portfolio_id,
                    symbol=normalized_symbol,
                    name=company_name,
                    quantity=holding.quantity,
                    current_price=holding.current_price,
                    purchase_price=holding.average_price,
                )
                db.add(asset)
                assets_imported += 1
            else:
                asset.name = company_name
                asset.quantity = holding.quantity
                asset.current_price = holding.current_price
                asset.purchase_price = holding.average_price

            db.commit()

        crud.update_broker_config(db, config.id)

        return schemas.BrokerSyncResponse(
            success=True,
            message=f"Successfully synced {len(holdings)} holdings",
            holdings_count=len(holdings),
            assets_imported=assets_imported,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
