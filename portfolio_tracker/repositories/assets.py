"""Asset (holding) persistence."""

from decimal import Decimal

from sqlalchemy.orm import Session

from portfolio_tracker.models import AssetModel


def get_asset_by_id(db: Session, asset_id: int):
    """Get an asset by ID."""
    return db.query(AssetModel).filter(AssetModel.id == asset_id).first()


def get_portfolio_assets(db: Session, portfolio_id: int):
    """Get all assets in a portfolio."""
    return db.query(AssetModel).filter(AssetModel.portfolio_id == portfolio_id).all()


def get_asset_by_symbol(db: Session, portfolio_id: int, symbol: str):
    """Get an asset in a portfolio by its (already normalized) symbol."""
    return (
        db.query(AssetModel)
        .filter(AssetModel.portfolio_id == portfolio_id, AssetModel.symbol == symbol)
        .first()
    )


def create_asset(db: Session, portfolio_id: int, symbol: str, name: str, quantity: Decimal, current_price: Decimal, purchase_price: Decimal):
    """Create a new asset."""
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
