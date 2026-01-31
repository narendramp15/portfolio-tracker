"""Market data API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import AssetModel, PortfolioModel, UserModel
from portfolio_tracker.services.market_data import market_data_service

router = APIRouter()


@router.get("/search")
async def search_stocks(
    q: str,
    market: str = 'IN',
    user: UserModel = Depends(get_current_user)
):
    """
    Search for stocks by name or symbol.
    
    Query params:
    - q: Search query (stock name or symbol)
    - market: 'IN' for India (NSE/BSE), 'US' for USA
    """
    if not q or len(q) < 2:
        return {"results": []}
    
    results = market_data_service.search_stocks(q, market)
    return {"results": results}


@router.get("/price/{symbol}")
async def get_stock_price(
    symbol: str,
    user: UserModel = Depends(get_current_user)
):
    """Get current price and info for a stock symbol."""
    stock_info = market_data_service.get_stock_info(symbol)
    
    if not stock_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock symbol '{symbol}' not found or invalid"
        )
    
    return stock_info


@router.get("/info/{symbol}")
async def get_stock_info(
    symbol: str,
    user: UserModel = Depends(get_current_user)
):
    """Get comprehensive information for a stock symbol (alias for /price)."""
    return await get_stock_price(symbol, user)


@router.post("/validate")
async def validate_symbol(
    symbol: str,
    user: UserModel = Depends(get_current_user)
):
    """Check if a stock symbol is valid."""
    is_valid = market_data_service.validate_symbol(symbol)
    
    return {
        "symbol": symbol,
        "valid": is_valid,
        "message": "Symbol is valid" if is_valid else "Symbol not found or invalid"
    }


@router.post("/portfolios/{portfolio_id}/refresh-prices")
async def refresh_portfolio_prices(
    portfolio_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh current prices for all assets in a portfolio.
    Updates asset prices from live market data.
    """
    # Verify portfolio ownership
    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.user_id == user.id
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Get all assets in portfolio
    assets = db.query(AssetModel).filter(
        AssetModel.portfolio_id == portfolio_id
    ).all()
    
    if not assets:
        return {
            "message": "No assets to update",
            "updated": 0,
            "failed": 0,
            "details": []
        }
    
    updated_count = 0
    failed_count = 0
    details = []
    
    for asset in assets:
        try:
            # Get full stock info including previous_close from market
            stock_info = market_data_service.get_stock_info(asset.symbol)
            
            if stock_info and stock_info.get('current_price'):
                current_price = stock_info['current_price']
                previous_close = stock_info.get('previous_close')
                old_price = float(asset.current_price)
                
                asset.current_price = current_price
                if previous_close:
                    asset.previous_close = previous_close
                asset.last_price_update = datetime.now()
                
                # Calculate day change
                day_change = 0
                day_change_percent = 0
                if previous_close and previous_close > 0:
                    day_change = current_price - previous_close
                    day_change_percent = (day_change / previous_close) * 100
                
                details.append({
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "old_price": old_price,
                    "new_price": current_price,
                    "previous_close": previous_close,
                    "day_change": day_change,
                    "day_change_percent": round(day_change_percent, 2),
                    "change": current_price - old_price,
                    "change_percent": ((current_price - old_price) / old_price * 100) if old_price > 0 else 0,
                    "status": "updated"
                })
                updated_count += 1
            else:
                details.append({
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "status": "failed",
                    "error": "Could not fetch price"
                })
                failed_count += 1
                
        except Exception as e:
            details.append({
                "symbol": asset.symbol,
                "name": asset.name,
                "status": "error",
                "error": str(e)
            })
            failed_count += 1
    
    # Commit all updates
    db.commit()
    
    return {
        "message": f"Updated {updated_count} assets, {failed_count} failed",
        "updated": updated_count,
        "failed": failed_count,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/assets/{asset_id}/refresh-price")
async def refresh_asset_price(
    asset_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh price for a single asset."""
    # Get asset and verify ownership through portfolio
    asset = db.query(AssetModel).join(PortfolioModel).filter(
        AssetModel.id == asset_id,
        PortfolioModel.user_id == user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Get current price
    current_price = market_data_service.get_current_price(asset.symbol)
    
    if not current_price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not fetch price for {asset.symbol}"
        )
    
    old_price = float(asset.current_price)
    asset.current_price = current_price
    asset.last_price_update = datetime.now()
    
    db.commit()
    db.refresh(asset)
    
    return {
        "asset_id": asset.id,
        "symbol": asset.symbol,
        "name": asset.name,
        "old_price": old_price,
        "new_price": current_price,
        "change": current_price - old_price,
        "change_percent": ((current_price - old_price) / old_price * 100) if old_price > 0 else 0,
        "updated_at": asset.last_price_update.isoformat()
    }


# ===== Price History Endpoints (Storage-Efficient) =====

@router.get("/history/{symbol}")
async def get_price_history(
    symbol: str,
    days: int = 90,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get historical price data for a symbol.
    
    - Recent data (< 90 days): From database (fast)
    - Older data: Fetched on-demand from yfinance (free)
    
    This hybrid approach saves storage on free-tier deployments.
    """
    from portfolio_tracker.services.price_history import \
        get_price_history_service
    
    service = get_price_history_service(db)
    data = service.get_price_history(symbol, days=days)
    
    return {
        "symbol": symbol,
        "days_requested": days,
        "data_points": len(data),
        "prices": data
    }


@router.post("/history/backfill")
async def backfill_price_history(
    symbol: Optional[str] = None,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Backfill price history for symbols.
    
    - If symbol provided: Backfill just that symbol
    - If no symbol: Backfill all symbols in user's portfolios
    
    Only stores data within retention period (default 90 days) to save space.
    """
    from portfolio_tracker.services.price_history import \
        get_price_history_service
    
    service = get_price_history_service(db)
    
    if symbol:
        count = service.backfill_symbol(symbol)
        return {
            "status": "success",
            "symbol": symbol,
            "records_added": count
        }
    else:
        results = service.backfill_all_holdings(user_id=user.id)
        return {
            "status": "success",
            "symbols_processed": results["success"] + results["failed"],
            "symbols_success": results["success"],
            "symbols_failed": results["failed"],
            "details": results["symbols"]
        }


@router.post("/history/cleanup")
async def cleanup_price_history(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up price history older than retention period.
    
    This helps keep storage lean on free-tier deployments.
    Recommended to run daily via cron job.
    """
    from portfolio_tracker.services.price_history import \
        get_price_history_service
    
    service = get_price_history_service(db)
    deleted = service.cleanup_old_data()
    
    return {
        "status": "success",
        "records_deleted": deleted
    }


@router.get("/history/stats")
async def get_price_history_stats(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get storage statistics for price history.
    
    Useful for monitoring storage usage on free-tier deployments.
    """
    from portfolio_tracker.services.price_history import \
        get_price_history_service
    
    service = get_price_history_service(db)
    stats = service.get_storage_stats()
    
    return stats
