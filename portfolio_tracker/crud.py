"""CRUD operations for database models."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func


# User CRUD Operations
def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    from portfolio_tracker.models import UserModel
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Get a user by email."""
    from portfolio_tracker.models import UserModel
    return db.query(UserModel).filter(UserModel.email == email).first()


def create_user(
    db: Session,
    email: str,
    username: Optional[str] = None,
    hashed_password: Optional[str] = None,
    full_name: Optional[str] = None,
    is_active: bool = True,
    # Legacy parameters for backwards compatibility with tests
    password: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
):
    """
    Create a new user.
    
    Supports two calling conventions:
    1. New: (email, username, hashed_password, full_name)
    2. Legacy: (email, password, first_name, last_name) - auto-hashes password
    """
    from portfolio_tracker.auth import hash_password
    from portfolio_tracker.models import UserModel

    # Handle legacy parameters
    if password and not hashed_password:
        hashed_password = hash_password(password)
    
    if not username:
        # Generate username from email if not provided
        username = email.split("@")[0]
    
    if not full_name and (first_name or last_name):
        # Build full_name from first_name/last_name
        full_name = f"{first_name or ''} {last_name or ''}".strip()
    
    user = UserModel(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_portfolio_by_id(db: Session, portfolio_id: int):
    """Get a portfolio by ID."""
    from portfolio_tracker.models import PortfolioModel
    return db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()


def get_portfolios(db: Session, skip: int = 0, limit: int = 100, user_id: int | None = None):
    """Get all portfolios with pagination."""
    from portfolio_tracker.models import PortfolioModel
    query = db.query(PortfolioModel)
    if user_id is not None:
        query = query.filter(PortfolioModel.user_id == user_id)
    return query.offset(skip).limit(limit).all()


def create_portfolio(db: Session, user_id: int, name: str, description: str | None = None):
    """Create a new portfolio."""
    from portfolio_tracker.models import PortfolioModel
    portfolio = PortfolioModel(user_id=user_id, name=name, description=description)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def update_portfolio(db: Session, portfolio_id: int, name: str | None = None, description: str | None = None):
    """Update a portfolio."""
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return None
    if name:
        portfolio.name = name
    if description is not None:
        portfolio.description = description
    db.commit()
    db.refresh(portfolio)
    return portfolio


def delete_portfolio(db: Session, portfolio_id: int):
    """Delete a portfolio."""
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return False
    db.delete(portfolio)
    db.commit()
    return True


def get_asset_by_id(db: Session, asset_id: int):
    """Get an asset by ID."""
    from portfolio_tracker.models import AssetModel
    return db.query(AssetModel).filter(AssetModel.id == asset_id).first()


def get_portfolio_assets(db: Session, portfolio_id: int):
    """Get all assets in a portfolio."""
    from portfolio_tracker.models import AssetModel
    return db.query(AssetModel).filter(AssetModel.portfolio_id == portfolio_id).all()


def create_asset(db: Session, portfolio_id: int, symbol: str, name: str, quantity: Decimal, current_price: Decimal, purchase_price: Decimal):
    """Create a new asset."""
    from portfolio_tracker.models import AssetModel
    asset = AssetModel(
        portfolio_id=portfolio_id,
        symbol=symbol,
        name=name,
        quantity=quantity,
        current_price=current_price,
        purchase_price=purchase_price,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id: int, quantity: Decimal = None, current_price: Decimal = None, purchase_price: Decimal = None, name: str = None, symbol: str = None):
    """Update an asset."""
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return None
    if quantity is not None:
        asset.quantity = quantity
    if current_price is not None:
        asset.current_price = current_price
    if purchase_price is not None:
        asset.purchase_price = purchase_price
    if name is not None:
        asset.name = name
    if symbol is not None:
        asset.symbol = symbol
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int):
    """Delete an asset."""
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return False
    db.delete(asset)
    db.commit()
    return True


# Transaction CRUD Operations
def get_transaction_by_id(db: Session, transaction_id: int):
    """Get a transaction by ID."""
    from portfolio_tracker.models import TransactionModel
    return db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()


def get_portfolio_transactions(db: Session, portfolio_id: int, skip: int = 0, limit: int = 100):
    """Get all transactions for a portfolio."""
    from portfolio_tracker.models import TransactionModel
    return db.query(TransactionModel).filter(
        TransactionModel.portfolio_id == portfolio_id
    ).order_by(TransactionModel.transaction_date.desc()).offset(skip).limit(limit).all()


def create_transaction(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    type: Optional[str] = None,
    quantity: Decimal = Decimal("0"),
    price: Decimal = Decimal("0"),
    transaction_date: Optional[datetime] = None,
    notes: Optional[str] = None,
    # Legacy parameter alias
    transaction_type: Optional[str] = None,
):
    """
    Create a new transaction.
    
    Supports both 'type' and 'transaction_type' parameters for backwards compatibility.
    """
    from portfolio_tracker.models import TransactionModel

    # Handle legacy parameter
    if transaction_type and not type:
        type = transaction_type
    
    transaction = TransactionModel(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        type=type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date or datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, transaction_id: int):
    """Delete a transaction."""
    transaction = get_transaction_by_id(db, transaction_id)
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True


def get_portfolio_stats(db: Session, portfolio_id: int):
    """Get portfolio statistics."""
    from portfolio_tracker.models import AssetModel
    
    assets = db.query(AssetModel).filter(AssetModel.portfolio_id == portfolio_id).all()
    
    if not assets:
        return {
            "total_value": Decimal("0"),
            "total_invested": Decimal("0"),
            "total_gain_loss": Decimal("0"),
            "gain_loss_percentage": Decimal("0"),
        }
    
    total_value = sum(asset.quantity * asset.current_price for asset in assets)
    total_invested = sum(asset.quantity * asset.purchase_price for asset in assets)
    total_gain_loss = total_value - total_invested
    
    if total_invested == 0:
        gain_loss_percentage = Decimal("0")
    else:
        gain_loss_percentage = (total_gain_loss / total_invested) * Decimal("100")
    
    return {
        "total_value": total_value,
        "total_invested": total_invested,
        "total_gain_loss": total_gain_loss,
        "gain_loss_percentage": gain_loss_percentage,
    }

# Broker Configuration CRUD Operations
def get_broker_config(db: Session, config_id: int):
    """Get broker config by ID."""
    from portfolio_tracker.models import BrokerConfigModel
    return db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()


def get_broker_configs_by_user(db: Session, user_id: int):
    """Get all broker configs for a user."""
    from portfolio_tracker.models import BrokerConfigModel
    return db.query(BrokerConfigModel).filter(BrokerConfigModel.user_id == user_id).all()


def get_broker_config_by_broker_name(db: Session, user_id: int, broker_name: str):
    """Get broker config by broker name and user."""
    from portfolio_tracker.models import BrokerConfigModel
    return db.query(BrokerConfigModel).filter(
        BrokerConfigModel.user_id == user_id,
        BrokerConfigModel.broker_name == broker_name
    ).first()


def create_broker_config(
    db: Session,
    user_id: int,
    broker_name: str,
    broker_user_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    extra_config: str | None = None,
):
    """Create a new broker configuration."""
    from portfolio_tracker.models import BrokerConfigModel
    
    config = BrokerConfigModel(
        user_id=user_id,
        broker_name=broker_name,
        broker_user_id=broker_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        api_key=api_key,
        api_secret=api_secret,
        extra_config=extra_config,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_broker_config(
    db: Session,
    config_id: int,
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    broker_user_id: str | None = None,
    extra_config: str | None = None,
    last_synced = None,
):
    """Update broker configuration tokens."""
    from datetime import datetime, timezone

    from portfolio_tracker.models import BrokerConfigModel
    
    config = db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()
    if not config:
        return None
    
    if access_token:
        config.access_token = access_token
    if refresh_token:
        config.refresh_token = refresh_token
    if api_key:
        config.api_key = api_key
    if api_secret:
        config.api_secret = api_secret
    if broker_user_id:
        config.broker_user_id = broker_user_id
    if extra_config:
        config.extra_config = extra_config
    if last_synced:
        config.last_synced = last_synced
    else:
        config.last_synced = datetime.now(timezone.utc)
    
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def delete_broker_config(db: Session, config_id: int):
    """Delete broker configuration."""
    from portfolio_tracker.models import BrokerConfigModel
    
    config = db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()
    if config:
        db.delete(config)
        db.commit()
    return config
