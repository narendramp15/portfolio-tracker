"""Portfolio persistence and aggregate statistics."""

from decimal import Decimal

from sqlalchemy.orm import Session

from portfolio_tracker.models import AssetModel, PortfolioModel


def get_portfolio_by_id(db: Session, portfolio_id: int):
    """Get a portfolio by ID."""
    return db.query(PortfolioModel).filter(PortfolioModel.id == portfolio_id).first()


def get_portfolios(db: Session, skip: int = 0, limit: int = 100, user_id: int | None = None):
    """Get all portfolios with pagination."""
    query = db.query(PortfolioModel)
    if user_id is not None:
        query = query.filter(PortfolioModel.user_id == user_id)
    return query.offset(skip).limit(limit).all()


def create_portfolio(db: Session, user_id: int, name: str, description: str | None = None):
    """Create a new portfolio."""
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


def get_portfolio_stats(db: Session, portfolio_id: int):
    """Get portfolio statistics."""
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
