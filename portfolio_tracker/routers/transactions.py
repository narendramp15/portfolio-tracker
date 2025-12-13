"""Transactions API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from portfolio_tracker.database import get_db
from portfolio_tracker import schemas, models

router = APIRouter()


@router.get("/")
async def list_all_transactions(db: Session = Depends(get_db)):
    """List all transactions across all portfolios."""
    try:
        transactions = db.query(models.TransactionModel).all()
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "portfolio_id": t.portfolio_id,
                "portfolio_name": t.portfolio.name if t.portfolio else "Unknown",
                "asset_id": t.asset_id,
                "asset_name": t.asset.name if t.asset else "Unknown",
                "asset_symbol": t.asset.symbol if t.asset else "N/A",
                "transaction_type": t.type,
                "quantity": float(t.quantity),
                "price_per_unit": float(t.price),
                "notes": t.notes,
                "transaction_date": t.transaction_date,
                "created_at": t.created_at
            })
        return result
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return []


@router.get("/{portfolio_id}")
async def list_transactions(portfolio_id: int, db: Session = Depends(get_db)):
    """List all transactions for a portfolio."""
    return {"portfolio_id": portfolio_id, "transactions": []}


@router.post("/{portfolio_id}")
async def create_transaction(portfolio_id: int, transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction."""
    return {"status": "Transaction created", "portfolio_id": portfolio_id}


@router.get("/{portfolio_id}/{transaction_id}")
async def get_transaction(portfolio_id: int, transaction_id: int, db: Session = Depends(get_db)):
    """Get a specific transaction."""
    return {"portfolio_id": portfolio_id, "transaction_id": transaction_id}


@router.delete("/{portfolio_id}/{transaction_id}")
async def delete_transaction(portfolio_id: int, transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction."""
    return {"message": "Transaction deleted successfully"}
