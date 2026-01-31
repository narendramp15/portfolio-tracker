"""Portfolio API endpoints."""

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from portfolio_tracker import crud, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel

router = APIRouter()


@router.get("/", response_model=list[schemas.Portfolio])
async def list_portfolios(
    skip: int = 0,
    limit: int = 100,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all portfolios."""
    portfolios = crud.get_portfolios(db, skip=skip, limit=limit, user_id=user.id)
    return portfolios


@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
async def get_portfolio(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get a specific portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post("/", response_model=schemas.Portfolio)
async def create_portfolio(
    portfolio: schemas.PortfolioCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new portfolio."""
    return crud.create_portfolio(
        db, user_id=user.id, name=portfolio.name, description=portfolio.description
    )


@router.put("/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(
    portfolio_id: int,
    portfolio: schemas.PortfolioUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a portfolio."""
    existing = crud.get_portfolio_by_id(db, portfolio_id)
    if not existing or existing.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    updated = crud.update_portfolio(db, portfolio_id, portfolio.name, portfolio.description)
    if not updated:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return updated


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a portfolio."""
    existing = crud.get_portfolio_by_id(db, portfolio_id)
    if not existing or existing.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if not crud.delete_portfolio(db, portfolio_id):
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"message": "Portfolio deleted successfully"}


@router.get("/{portfolio_id}/assets", response_model=list[schemas.Asset])
async def get_portfolio_assets(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all assets in a portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return crud.get_portfolio_assets(db, portfolio_id)


@router.post("/{portfolio_id}/assets", response_model=schemas.Asset)
async def add_asset_to_portfolio(
    portfolio_id: int,
    asset: schemas.AssetCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an asset to a portfolio with automatic symbol validation and price fetching.
    
    - Validates the symbol exists in the market
    - Auto-fetches current price if not provided
    - Auto-fills company name if not provided
    """
    from portfolio_tracker.services.market_data import market_data_service
    
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Validate and enrich symbol data
    symbol = asset.symbol.strip().upper()
    
    # Fetch live stock info for validation and enrichment
    stock_info = market_data_service.get_stock_info(symbol)
    
    if not stock_info:
        # Try adding .NS suffix if it's a simple symbol (Indian stocks)
        if '.' not in symbol:
            symbol_ns = f"{symbol}.NS"
            stock_info = market_data_service.get_stock_info(symbol_ns)
            if stock_info:
                symbol = symbol_ns
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid stock symbol '{symbol}'. Symbol not found in market data."
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stock symbol '{symbol}'. Symbol not found in market data."
            )
    
    # Auto-fill name if not provided
    name = asset.name.strip() if asset.name else stock_info.get('name', symbol)
    
    # Use live price as current_price if not provided
    current_price = asset.current_price if asset.current_price else stock_info.get('current_price', asset.purchase_price)
    
    return crud.create_asset(
        db,
        portfolio_id=portfolio_id,
        symbol=symbol,
        name=name,
        quantity=asset.quantity,
        current_price=current_price,
        purchase_price=asset.purchase_price,
    )


@router.put("/{portfolio_id}/assets/{asset_id}", response_model=schemas.Asset)
async def update_asset_in_portfolio(
    portfolio_id: int,
    asset_id: int,
    asset_update: schemas.AssetUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an asset in a portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    asset = crud.get_asset_by_id(db, asset_id)
    if not asset or asset.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    updated = crud.update_asset(
        db,
        asset_id,
        quantity=asset_update.quantity,
        current_price=asset_update.current_price,
        purchase_price=asset_update.purchase_price,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
    return updated


@router.delete("/{portfolio_id}/assets/{asset_id}")
async def delete_asset_from_portfolio(
    portfolio_id: int,
    asset_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an asset from a portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    asset = crud.get_asset_by_id(db, asset_id)
    if not asset or asset.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if not crud.delete_asset(db, asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


@router.get("/{portfolio_id}/export")
async def export_portfolio_csv(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Export portfolio holdings to CSV."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    assets = crud.get_portfolio_assets(db, portfolio_id)
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Symbol',
        'Name',
        'Quantity',
        'Purchase Price (₹)',
        'Current Price (₹)',
        'Invested Value (₹)',
        'Current Value (₹)',
        'Gain/Loss (₹)',
        'Gain/Loss (%)',
        'Purchase Date'
    ])
    
    # Write data rows
    for asset in assets:
        quantity = float(asset.quantity)
        purchase_price = float(asset.purchase_price)
        current_price = float(asset.current_price)
        invested_value = quantity * purchase_price
        current_value = quantity * current_price
        gain_loss = current_value - invested_value
        gain_loss_pct = (gain_loss / invested_value * 100) if invested_value > 0 else 0
        
        writer.writerow([
            asset.symbol,
            asset.name,
            quantity,
            purchase_price,
            current_price,
            round(invested_value, 2),
            round(current_value, 2),
            round(gain_loss, 2),
            round(gain_loss_pct, 2),
            asset.created_at.strftime('%Y-%m-%d') if asset.created_at else ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={portfolio.name.replace(' ', '_')}_holdings.csv"
        }
    )
