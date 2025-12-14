"""Dashboard API endpoints."""

from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from portfolio_tracker.database import get_db
from portfolio_tracker import schemas, crud
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel

router = APIRouter()


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    portfolios = crud.get_portfolios(db, user_id=user.id)
    
    total_portfolio_value = Decimal("0")
    total_invested = Decimal("0")
    
    for portfolio in portfolios:
        stats = crud.get_portfolio_stats(db, portfolio.id)
        total_portfolio_value += Decimal(str(stats["total_value"]))
        total_invested += Decimal(str(stats["total_invested"]))
    
    total_gain_loss = total_portfolio_value - total_invested
    
    if total_invested == 0:
        gain_loss_percentage = Decimal("0")
    else:
        gain_loss_percentage = (total_gain_loss / total_invested) * Decimal("100")
    
    return {
        "total_portfolio_value": float(total_portfolio_value),
        "total_invested": float(total_invested),
        "total_gain_loss": float(total_gain_loss),
        "gain_loss_percentage": float(gain_loss_percentage),
        "number_of_portfolios": len(portfolios),
        "number_of_assets": sum(len(p.assets) for p in portfolios),
    }


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_dashboard(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get dashboard data for a specific portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return {"error": "Portfolio not found"}
    if portfolio.user_id != user.id:
        return {"error": "Portfolio not found"}
    
    stats = crud.get_portfolio_stats(db, portfolio_id)
    return {
        "portfolio": portfolio,
        "stats": stats,
    }
