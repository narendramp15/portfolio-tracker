"""Trading Journal API endpoints."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from portfolio_tracker import models, schemas
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import TradingJournalModel, UserModel

router = APIRouter()


def verify_portfolio_ownership(db: Session, portfolio_id: int, user_id: int):
    """Verify that the user owns the portfolio."""
    import logging
    logger = logging.getLogger(__name__)
    
    portfolio = db.query(models.PortfolioModel).filter(
        models.PortfolioModel.id == portfolio_id,
        models.PortfolioModel.user_id == user_id
    ).first()
    if not portfolio:
        # Check if portfolio exists but belongs to another user
        exists = db.query(models.PortfolioModel).filter(
            models.PortfolioModel.id == portfolio_id
        ).first()
        if exists:
            logger.warning(f"User {user_id} attempted to access portfolio {portfolio_id} owned by user {exists.user_id}")
            raise HTTPException(
                status_code=403, 
                detail=f"Portfolio {portfolio_id} belongs to another user. Your user ID: {user_id}, Portfolio owner ID: {exists.user_id}"
            )
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
    return portfolio


def calculate_profit_loss(entry_price: Decimal, exit_price: Decimal, quantity: Decimal) -> Decimal:
    """Calculate profit/loss from a trade."""
    return (exit_price - entry_price) * quantity


def get_next_trade_id(db: Session, portfolio_id: int) -> int:
    """Get the next trade_id for a portfolio."""
    max_trade_id = db.query(func.max(TradingJournalModel.trade_id)).filter(
        TradingJournalModel.portfolio_id == portfolio_id
    ).scalar()
    return (max_trade_id or 0) + 1


def _get_journal_entry(db: Session, journal_id: int, portfolio_id: int) -> Optional[TradingJournalModel]:
    """Get a trading journal entry by ID."""
    return db.query(TradingJournalModel).filter(
        TradingJournalModel.id == journal_id,
        TradingJournalModel.portfolio_id == portfolio_id
    ).first()


@router.get("/{portfolio_id}/stats", response_model=schemas.TradingJournalSummary)
async def get_journal_stats(
    portfolio_id: int,
    start_date: Optional[datetime] = Query(None, description="Filter by entry date (start)"),
    end_date: Optional[datetime] = Query(None, description="Filter by entry date (end)"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trading journal statistics for a portfolio."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    base_query = db.query(TradingJournalModel).filter(TradingJournalModel.portfolio_id == portfolio_id)
    
    if start_date:
        base_query = base_query.filter(TradingJournalModel.entry_date >= start_date)
    if end_date:
        base_query = base_query.filter(TradingJournalModel.entry_date <= end_date)
    
    trades = base_query.all()
    
    if not trades:
        return schemas.TradingJournalSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit_loss=Decimal("0"),
            average_profit_loss=Decimal("0"),
            best_trade=None,
            worst_trade=None
        )
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.profit_loss and t.profit_loss > 0])
    losing_trades = len([t for t in trades if t.profit_loss and t.profit_loss < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    total_profit_loss = sum(t.profit_loss or Decimal("0") for t in trades)
    average_profit_loss = total_profit_loss / total_trades if total_trades > 0 else Decimal("0")
    
    profitable_trades = [t.profit_loss for t in trades if t.profit_loss and t.profit_loss > 0]
    losing_trade_values = [t.profit_loss for t in trades if t.profit_loss and t.profit_loss < 0]
    
    best_trade = max(profitable_trades) if profitable_trades else None
    worst_trade = min(losing_trade_values) if losing_trade_values else None
    
    return schemas.TradingJournalSummary(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        total_profit_loss=total_profit_loss,
        average_profit_loss=average_profit_loss,
        best_trade=best_trade,
        worst_trade=worst_trade
    )


@router.get("/{portfolio_id}/{journal_id}", response_model=schemas.TradingJournal)
async def get_journal_entry_endpoint(
    portfolio_id: int,
    journal_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trading journal entry."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    entry = _get_journal_entry(db, journal_id, portfolio_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    return entry


@router.patch("/{portfolio_id}/{journal_id}", response_model=schemas.TradingJournal)
async def update_journal_entry(
    portfolio_id: int,
    journal_id: int,
    update_data: schemas.TradingJournalUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trading journal entry."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    entry = _get_journal_entry(db, journal_id, portfolio_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if 'exit_price' in update_dict:
        entry.exit_price = update_dict['exit_price']
        if entry.exit_price and entry.quantity:
            entry.profit_loss = calculate_profit_loss(
                entry.entry_price,
                entry.exit_price,
                entry.quantity
            )
    
    for field, value in update_dict.items():
        if field != 'exit_price' or value is not None:
            setattr(entry, field, value)
    
    entry.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(entry)
    
    return entry


@router.delete("/{portfolio_id}/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    portfolio_id: int,
    journal_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trading journal entry."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    entry = _get_journal_entry(db, journal_id, portfolio_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    db.delete(entry)
    db.commit()


@router.post("/{portfolio_id}", response_model=schemas.TradingJournal, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    portfolio_id: int,
    journal_data: schemas.TradingJournalCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading journal entry."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    trade_id = get_next_trade_id(db, portfolio_id)
    
    profit_loss = None
    if journal_data.exit_price and journal_data.exit_date:
        profit_loss = calculate_profit_loss(
            journal_data.entry_price,
            journal_data.exit_price,
            journal_data.quantity
        )
    
    new_entry = TradingJournalModel(
        portfolio_id=portfolio_id,
        trade_id=trade_id,
        symbol=journal_data.symbol,
        entry_price=journal_data.entry_price,
        exit_price=journal_data.exit_price,
        quantity=journal_data.quantity,
        entry_date=journal_data.entry_date,
        exit_date=journal_data.exit_date,
        profit_loss=profit_loss,
        notes=journal_data.notes
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return new_entry


@router.get("/{portfolio_id}", response_model=List[schemas.TradingJournal])
async def get_portfolio_journal(
    portfolio_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[datetime] = Query(None, description="Filter by entry date (start)"),
    end_date: Optional[datetime] = Query(None, description="Filter by entry date (end)"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trading journal entries for a portfolio with optional filtering and pagination."""
    verify_portfolio_ownership(db, portfolio_id, user.id)
    
    query = db.query(TradingJournalModel).filter(TradingJournalModel.portfolio_id == portfolio_id)
    
    if symbol:
        query = query.filter(TradingJournalModel.symbol == symbol)
    if start_date:
        query = query.filter(TradingJournalModel.entry_date >= start_date)
    if end_date:
        query = query.filter(TradingJournalModel.entry_date <= end_date)
    
    entries = query.order_by(desc(TradingJournalModel.entry_date)).offset(skip).limit(limit).all()
    return entries
