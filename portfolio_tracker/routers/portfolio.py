"""Portfolio API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from portfolio_tracker.database import get_db
from portfolio_tracker import schemas, crud
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
    """Add an asset to a portfolio."""
    portfolio = crud.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return crud.create_asset(
        db,
        portfolio_id=portfolio_id,
        symbol=asset.symbol,
        name=asset.name,
        quantity=asset.quantity,
        current_price=asset.current_price,
        purchase_price=asset.purchase_price,
    )
