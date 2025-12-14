"""Transactions API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from portfolio_tracker.database import get_db
from portfolio_tracker import schemas, models
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.models import UserModel

router = APIRouter()


@router.get("/")
async def list_all_transactions(
    user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all transactions across all portfolios."""
    try:
        transactions = (
            db.query(models.TransactionModel)
            .join(models.PortfolioModel, models.TransactionModel.portfolio_id == models.PortfolioModel.id)
            .filter(models.PortfolioModel.user_id == user.id)
            .all()
        )
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
                "transaction_date": t.transaction_date.isoformat(),
                "created_at": t.created_at
            })
        return result
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return []


@router.get("/{portfolio_id}")
async def list_transactions(
    portfolio_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all transactions for a portfolio."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    txs = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.portfolio_id == portfolio_id)
        .order_by(models.TransactionModel.transaction_date.desc())
        .all()
    )
    return [
        {
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
            "transaction_date": t.transaction_date.isoformat(),
            "created_at": t.created_at,
        }
        for t in txs
    ]


@router.post("/{portfolio_id}")
async def create_transaction(
    portfolio_id: int,
    transaction: schemas.TransactionCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    asset = (
        db.query(models.AssetModel)
        .filter(models.AssetModel.id == transaction.asset_id, models.AssetModel.portfolio_id == portfolio_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    tx = models.TransactionModel(
        portfolio_id=portfolio_id,
        asset_id=transaction.asset_id,
        type=transaction.type.lower(),
        quantity=transaction.quantity,
        price=transaction.price,
        notes=transaction.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "id": tx.id,
        "portfolio_id": tx.portfolio_id,
        "portfolio_name": portfolio.name,
        "asset_id": tx.asset_id,
        "asset_name": asset.name,
        "asset_symbol": asset.symbol,
        "transaction_type": tx.type,
        "quantity": float(tx.quantity),
        "price_per_unit": float(tx.price),
        "notes": tx.notes,
        "transaction_date": tx.transaction_date.isoformat(),
        "created_at": tx.created_at,
    }


@router.get("/{portfolio_id}/{transaction_id}")
async def get_transaction(
    portfolio_id: int,
    transaction_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    tx = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.id == transaction_id, models.TransactionModel.portfolio_id == portfolio_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "id": tx.id,
        "portfolio_id": tx.portfolio_id,
        "portfolio_name": portfolio.name,
        "asset_id": tx.asset_id,
        "asset_name": tx.asset.name if tx.asset else "Unknown",
        "asset_symbol": tx.asset.symbol if tx.asset else "N/A",
        "transaction_type": tx.type,
        "quantity": float(tx.quantity),
        "price_per_unit": float(tx.price),
        "notes": tx.notes,
        "transaction_date": tx.transaction_date.isoformat(),
        "created_at": tx.created_at,
    }


@router.delete("/{portfolio_id}/{transaction_id}")
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    portfolio = db.query(models.PortfolioModel).filter(models.PortfolioModel.id == portfolio_id).first()
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    tx = (
        db.query(models.TransactionModel)
        .filter(models.TransactionModel.id == transaction_id, models.TransactionModel.portfolio_id == portfolio_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(tx)
    db.commit()

    return {"message": "Transaction deleted successfully"}
