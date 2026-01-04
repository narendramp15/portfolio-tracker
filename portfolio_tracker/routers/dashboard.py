"""Dashboard API endpoints."""

from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from portfolio_tracker.database import get_db
from portfolio_tracker import schemas, crud

router = APIRouter()


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get comprehensive dashboard statistics."""
    portfolios = crud.get_portfolios(db)

    total_portfolio_value = Decimal("0")
    total_invested = Decimal("0")
    assets_data = []

    for portfolio in portfolios:
        stats = crud.get_portfolio_stats(db, portfolio.id)
        total_portfolio_value += Decimal(str(stats["total_value"]))
        total_invested += Decimal(str(stats["total_invested"]))

        for asset in portfolio.assets:
            current_value = Decimal(str(asset.current_value or 0))
            cost_basis = Decimal(str(asset.cost_basis or 0))
            gain_loss = current_value - cost_basis

            if cost_basis > 0:
                return_percent = (gain_loss / cost_basis) * Decimal("100")
            else:
                return_percent = Decimal("0")

            assets_data.append({
                "name": asset.name,
                "quantity": float(asset.quantity),
                "current_value": float(current_value),
                "cost_basis": float(cost_basis),
                "gain_loss": float(gain_loss),
                "return_percent": float(return_percent),
                "portfolio_id": portfolio.id,
            })

    total_gain_loss = total_portfolio_value - total_invested

    if total_invested == 0:
        gain_loss_percentage = Decimal("0")
    else:
        gain_loss_percentage = (total_gain_loss / total_invested) * Decimal("100")

    assets_data.sort(key=lambda x: x["current_value"], reverse=True)
    top_assets = assets_data[:5]

    gainers = sorted(
        [a for a in assets_data if a["return_percent"] >= 0],
        key=lambda x: x["return_percent"],
        reverse=True
    )[:3]

    losers = sorted(
        [a for a in assets_data if a["return_percent"] < 0],
        key=lambda x: x["return_percent"]
    )[:3]

    asset_allocation = [
        {
            "name": asset["name"],
            "value": asset["current_value"],
            "percentage": (
                (asset["current_value"] / float(total_portfolio_value) * 100)
                if float(total_portfolio_value) > 0
                else 0
            )
        }
        for asset in assets_data[:8]
    ]

    return {
        "total_portfolio_value": float(total_portfolio_value),
        "total_invested": float(total_invested),
        "total_gain_loss": float(total_gain_loss),
        "gain_loss_percentage": float(gain_loss_percentage),
        "number_of_portfolios": len(portfolios),
        "number_of_assets": sum(len(p.assets) for p in portfolios),
        "top_assets": top_assets,
        "gainers": gainers,
        "losers": losers,
        "asset_allocation": asset_allocation,
    }


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_dashboard(portfolio_id: int, db: Session = Depends(get_db)):
    """Get dashboard data for a specific portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return {"error": "Portfolio not found"}
    
    stats = crud.get_portfolio_stats(db, portfolio_id)
    return {
        "portfolio": portfolio,
        "stats": stats,
    }
