"""Dashboard API endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel

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
    
    # Today's change (placeholder - would need historical data for real implementation)
    # For now, calculate a rough estimate based on recent price movements
    today_change = Decimal("0")
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
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get yearly portfolio growth data for chart visualization."""
    from datetime import datetime, timedelta

    from dateutil.relativedelta import relativedelta
    
    portfolios = crud.get_portfolios(db, user_id=user.id)
    
    # Get current date and calculate 12 months back
    now = datetime.now()
    growth_data = []
    
    # Simulate Nifty 50 starting value (based on approximate real Nifty levels)
    # In production, fetch actual Nifty historical data from NSE API or data provider
    nifty_current = 22500.0  # Approximate Nifty 50 level as of Jan 2026
    
    # Generate data points for the last 12 months
    for i in range(12, -1, -1):
        date = now - relativedelta(months=i)
        
        # Calculate portfolio value at that point
        # For simplicity, we'll simulate growth based on current values
        # In a real implementation, you'd query historical transaction data
        total_value = Decimal("0")
        total_invested = Decimal("0")
        
        for portfolio in portfolios:
            stats = crud.get_portfolio_stats(db, portfolio.id)
            current_value = Decimal(str(stats["total_value"]))
            invested = Decimal(str(stats["total_invested"]))
            
            total_value += current_value
            total_invested += invested
        
        # Simulate historical growth (decay factor based on months ago)
        # This is a placeholder - real implementation would use transaction history
        if i > 0:
            decay_factor = 1 - (i * 0.05)  # Assume ~5% monthly growth on average
            simulated_value = float(total_value) * decay_factor
        else:
            simulated_value = float(total_value)
        
        # Ensure value doesn't go below invested amount minus some loss tolerance
        min_value = float(total_invested) * 0.7  # Don't simulate more than 30% loss
        simulated_value = max(simulated_value, min_value)
        
        # Simulate Nifty growth (assume average 12-15% annual return)
        # Nifty typically grows 1-1.5% per month on average with volatility
        if i > 0:
            nifty_decay = 1 - (i * 0.012)  # ~1.2% monthly growth
            simulated_nifty = nifty_current * nifty_decay
        else:
            simulated_nifty = nifty_current
        
        # Normalize Nifty to portfolio scale for better visualization
        # Start both at same baseline for comparison
        if i == 12:
            nifty_baseline = simulated_nifty
            portfolio_baseline = simulated_value
        
        # Scale Nifty proportionally to portfolio starting value
        nifty_scaled = (simulated_nifty / nifty_baseline) * portfolio_baseline if portfolio_baseline > 0 else simulated_nifty
        
        growth_data.append({
            "year": date.year,
            "month": date.month,
            "value": round(simulated_value, 2),
            "nifty_value": round(nifty_scaled, 2),
            "label": date.strftime("%b %Y")
        })
    
    return growth_data
