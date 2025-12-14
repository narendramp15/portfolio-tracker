"""CRUD operations for database models."""

from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.sql import func


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


def delete_asset(db: Session, asset_id: int):
    """Delete an asset."""
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return False
    db.delete(asset)
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
