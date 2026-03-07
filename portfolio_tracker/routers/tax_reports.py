"""Tax reports router for capital gains calculations."""

import csv
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from portfolio_tracker.deps import (check_export_limit, get_current_user,
                                    get_db, log_export)
from portfolio_tracker.models import (PortfolioModel, TransactionModel,
                                      UserModel)
from portfolio_tracker.services.tax_calculator import TaxCalculator

router = APIRouter(prefix="/tax-reports", tags=["tax-reports"])


@router.get("/portfolios/{portfolio_id}/capital-gains")
def get_capital_gains_report(
    portfolio_id: int,
    financial_year: Optional[str] = None,
    method: str = "FIFO",
    include_unrealized: bool = False,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate STCG/LTCG capital gains report for a portfolio.
    
    Args:
        portfolio_id: ID of the portfolio
        financial_year: Optional FY filter (e.g., "2024-25"). If not provided, includes all transactions.
        method: Cost basis method - "FIFO" or "LIFO" (default: FIFO)
        include_unrealized: Whether to include unrealized gains from current holdings
        
    Returns:
        Comprehensive tax report with STCG/LTCG breakdown
    """
    # Verify portfolio ownership
    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.user_id == user.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Fetch all transactions with asset relationship
    transactions = db.query(TransactionModel).options(
        joinedload(TransactionModel.asset)
    ).filter(
        TransactionModel.portfolio_id == portfolio_id
    ).order_by(TransactionModel.transaction_date).all()
    
    if not transactions:
        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "financial_year": financial_year or "All Time",
            "method": method,
            "summary": {
                "total_stcg": 0,
                "total_ltcg": 0,
                "total_stcg_tax": 0,
                "total_ltcg_tax": 0,
                "total_tax": 0,
                "ltcg_exemption_used": 0,
                "symbols": []
            },
            "by_symbol": {},
            "available_financial_years": []
        }
    
    # Get available financial years
    available_fys = TaxCalculator.get_available_financial_years(transactions)
    
    # Filter by financial year if specified
    if financial_year:
        transactions = TaxCalculator.filter_by_financial_year(transactions, financial_year)
    
    # Validate method
    if method not in ["FIFO", "LIFO"]:
        raise HTTPException(status_code=400, detail="Method must be FIFO or LIFO")
    
    # Calculate capital gains
    report = TaxCalculator.calculate_capital_gains(
        transactions,
        method=method,
        include_unrealized=include_unrealized
    )
    
    # Add metadata
    report["portfolio_id"] = portfolio_id
    report["portfolio_name"] = portfolio.name
    report["financial_year"] = financial_year or "All Time"
    report["available_financial_years"] = available_fys
    
    return report


@router.get("/portfolios/{portfolio_id}/available-years")
def get_available_financial_years(
    portfolio_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of financial years that have transactions for a portfolio.
    
    Args:
        portfolio_id: ID of the portfolio
        
    Returns:
        List of financial year strings
    """
    # Verify portfolio ownership
    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.user_id == user.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Fetch transactions
    transactions = db.query(TransactionModel).filter(
        TransactionModel.portfolio_id == portfolio_id
    ).all()
    
    available_fys = TaxCalculator.get_available_financial_years(transactions)
    
    return {
        "portfolio_id": portfolio_id,
        "financial_years": available_fys
    }


@router.get("/portfolios/{portfolio_id}/tax-summary")
def get_tax_summary(
    portfolio_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a quick tax summary across all financial years.
    
    Args:
        portfolio_id: ID of the portfolio
        
    Returns:
        Summary of taxes by financial year
    """
    # Verify portfolio ownership
    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.user_id == user.id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Fetch all transactions with asset relationship
    transactions = db.query(TransactionModel).options(
        joinedload(TransactionModel.asset)
    ).filter(
        TransactionModel.portfolio_id == portfolio_id
    ).order_by(TransactionModel.transaction_date).all()
    
    if not transactions:
        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "years": []
        }
    
    # Get available financial years
    available_fys = TaxCalculator.get_available_financial_years(transactions)
    
    # Calculate for each year
    years_summary = []
    for fy in available_fys:
        filtered_txns = TaxCalculator.filter_by_financial_year(transactions, fy)
        report = TaxCalculator.calculate_capital_gains(filtered_txns, method="FIFO")
        
        years_summary.append({
            "financial_year": fy,
            "total_stcg": report["summary"]["total_stcg"],
            "total_ltcg": report["summary"]["total_ltcg"],
            "total_tax": report["summary"]["total_tax"],
            "symbols_count": len(report["summary"]["symbols"])
        })
    
    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "years": years_summary
    }


@router.get("/portfolios/{portfolio_id}/capital-gains/export")
def export_capital_gains_csv(
    portfolio_id: int,
    financial_year: Optional[str] = None,
    method: str = "FIFO",
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export capital gains report as CSV (gated — Free plan: 3 exports/month).
    """
    check_export_limit(user, db)

    portfolio = db.query(PortfolioModel).filter(
        PortfolioModel.id == portfolio_id,
        PortfolioModel.user_id == user.id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    transactions = (
        db.query(TransactionModel)
        .options(joinedload(TransactionModel.asset))
        .filter(TransactionModel.portfolio_id == portfolio_id)
        .order_by(TransactionModel.transaction_date)
        .all()
    )

    if financial_year:
        transactions = TaxCalculator.filter_by_financial_year(transactions, financial_year)

    if method not in ["FIFO", "LIFO"]:
        raise HTTPException(status_code=400, detail="Method must be FIFO or LIFO")

    report = TaxCalculator.calculate_capital_gains(transactions, method=method)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Symbol", "Type", "Buy Date", "Sell Date",
        "Quantity", "Buy Price (₹)", "Sell Price (₹)",
        "Gain/Loss (₹)", "Holding Days",
    ])

    for symbol, data in report.get("by_symbol", {}).items():
        for t in data.get("stcg_transactions", []):
            writer.writerow([
                symbol, "STCG",
                t.get("buy_date", ""), t.get("sell_date", ""),
                t.get("quantity", ""), t.get("buy_price", ""), t.get("sell_price", ""),
                t.get("gain", ""), t.get("holding_days", ""),
            ])
        for t in data.get("ltcg_transactions", []):
            writer.writerow([
                symbol, "LTCG",
                t.get("buy_date", ""), t.get("sell_date", ""),
                t.get("quantity", ""), t.get("buy_price", ""), t.get("sell_price", ""),
                t.get("gain", ""), t.get("holding_days", ""),
            ])

    output.seek(0)
    fy_label = financial_year or "all"
    log_export(user, "tax_report", db)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=tax-report-{portfolio.name}-{fy_label}.csv"
        },
    )
