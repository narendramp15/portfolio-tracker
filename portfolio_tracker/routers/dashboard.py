"""Dashboard API endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel
from portfolio_tracker.services import portfolio_analytics

router = APIRouter()


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get dashboard statistics with professional KPIs."""
    portfolios = crud.get_portfolios(db, user_id=user.id)
    
    total_portfolio_value = Decimal("0")
    total_invested = Decimal("0")
    all_assets = []
    
    for portfolio in portfolios:
        stats = crud.get_portfolio_stats(db, portfolio.id)
        total_portfolio_value += Decimal(str(stats["total_value"]))
        total_invested += Decimal(str(stats["total_invested"]))
        all_assets.extend(portfolio.assets)
    
    total_gain_loss = total_portfolio_value - total_invested
    
    if total_invested == 0:
        gain_loss_percentage = Decimal("0")
    else:
        gain_loss_percentage = (total_gain_loss / total_invested) * Decimal("100")
    
    # Calculate professional KPIs
    best_performer = None
    worst_performer = None
    returns_list = []
    winning_assets = 0
    losing_assets = 0
    
    if all_assets:
        performers = []
        for asset in all_assets:
            invested_value = Decimal(str(asset.purchase_price)) * Decimal(str(asset.quantity))
            current_value = Decimal(str(asset.current_price)) * Decimal(str(asset.quantity))
            gain_loss = current_value - invested_value
            
            if invested_value > 0:
                return_pct = (gain_loss / invested_value) * Decimal("100")
                returns_list.append(return_pct)
                performers.append({
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "return_pct": float(return_pct),
                    "gain_loss": float(gain_loss)
                })
                
                if gain_loss > 0:
                    winning_assets += 1
                elif gain_loss < 0:
                    losing_assets += 1
        
        if performers:
            best_performer = max(performers, key=lambda x: x["return_pct"])
            worst_performer = min(performers, key=lambda x: x["return_pct"])
    
    # Average return
    average_return = None
    if returns_list:
        average_return = sum(returns_list) / len(returns_list)
    
    # Diversification score (unique symbols)
    diversification_score = len(set(asset.symbol for asset in all_assets))
    
    # Today's change - calculated from previous_close if available
    today_change = Decimal("0")
    total_previous_value = Decimal("0")
    
    for asset in all_assets:
        quantity = Decimal(str(asset.quantity))
        current_price = Decimal(str(asset.current_price))
        
        if asset.previous_close:
            previous_close = Decimal(str(asset.previous_close))
            # Today's change = (current_price - previous_close) * quantity
            asset_change = (current_price - previous_close) * quantity
            today_change += asset_change
            total_previous_value += previous_close * quantity
    
    # Calculate percentage based on total previous value
    if total_previous_value > 0:
        today_change_percentage = (today_change / total_previous_value) * Decimal("100")
    else:
        today_change_percentage = Decimal("0")
    
    return {
        "total_portfolio_value": float(total_portfolio_value),
        "total_invested": float(total_invested),
        "total_gain_loss": float(total_gain_loss),
        "gain_loss_percentage": float(gain_loss_percentage),
        "number_of_portfolios": len(portfolios),
        "number_of_assets": len(all_assets),
        
        # Professional KPIs
        "today_change": float(today_change),
        "today_change_percentage": float(today_change_percentage),
        "best_performer": best_performer,
        "worst_performer": worst_performer,
        "average_return": float(average_return) if average_return else None,
        "total_return_percentage": float(gain_loss_percentage),
        "diversification_score": diversification_score,
        "winning_assets": winning_assets,
        "losing_assets": losing_assets,
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


@router.get("/growth", response_model=list[schemas.GrowthDataPoint])
async def get_portfolio_growth(
    months: int = 12,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Month-end portfolio value against Nifty 50, rebuilt from the ledger.

    Each point is the holdings the transaction ledger says were held on that
    date, valued at that date's actual closing prices, with the index rebased
    onto the portfolio's axis for comparison.

    Returns an empty list when there is no history to plot or when too little
    of the portfolio can be priced - the chart renders its empty state rather
    than a simulated line.
    """
    months = max(1, min(months, 60))
    return portfolio_analytics.build_valuation_series(db, user_id=user.id, months=months)


@router.get("/returns")
async def get_portfolio_returns(
    months: int = 12,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Headline performance metrics: XIRR, TWR, benchmark alpha, drawdown.

    XIRR is money-weighted and answers "how did my rupees do". TWR removes the
    effect of contribution timing and is the figure that can fairly be compared
    against the index. Any metric that cannot be computed from available data
    is returned as null rather than estimated.
    """
    months = max(1, min(months, 60))
    return portfolio_analytics.compute_returns(db, user_id=user.id, months=months)
