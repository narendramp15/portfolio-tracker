"""Tax reports router for capital gains calculations."""

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    
    # Validate method
    if method not in ["FIFO", "LIFO"]:
        raise HTTPException(status_code=400, detail="Method must be FIFO or LIFO")

    # Calculate capital gains over the full history; the FY only scopes which
    # sells are reported (pre-filtering would corrupt FIFO lot matching).
    report = TaxCalculator.calculate_capital_gains(
        transactions,
        method=method,
        include_unrealized=include_unrealized,
        financial_year=financial_year,
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
        report = TaxCalculator.calculate_capital_gains(
            transactions, method="FIFO", financial_year=fy
        )
        
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

    if method not in ["FIFO", "LIFO"]:
        raise HTTPException(status_code=400, detail="Method must be FIFO or LIFO")

    report = TaxCalculator.calculate_capital_gains(
        transactions, method=method, financial_year=financial_year
    )

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


# ---------------------------------------------------------------------------
# FY auto-detection
# ---------------------------------------------------------------------------

@router.get("/current-financial-year")
def get_current_financial_year():
    """Return the current Indian financial year string (e.g. '2025-26')."""
    today = datetime.now(timezone.utc)
    # Indian FY runs Apr 1 — Mar 31
    if today.month >= 4:
        start_year = today.year
    else:
        start_year = today.year - 1
    fy = f"{start_year}-{str(start_year + 1)[-2:]}"
    return {"financial_year": fy}


# ---------------------------------------------------------------------------
# PDF export (uses reportlab if available, else returns CSV fallback)
# ---------------------------------------------------------------------------

@router.get("/portfolios/{portfolio_id}/capital-gains/export-pdf")
def export_capital_gains_pdf(
    portfolio_id: int,
    financial_year: Optional[str] = None,
    method: str = "FIFO",
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export capital gains report as PDF (Pro feature)."""
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

    if method not in ["FIFO", "LIFO"]:
        raise HTTPException(status_code=400, detail="Method must be FIFO or LIFO")

    report = TaxCalculator.calculate_capital_gains(
        transactions, method=method, financial_year=financial_year
    )
    summary = report.get("summary", {})
    fy_label = financial_year or "all"

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                        Table, TableStyle)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation library not installed. Install reportlab: pip install reportlab",
        )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Capital Gains Tax Report — {portfolio.name}", styles["Title"]))
    elements.append(Paragraph(f"Financial Year: {fy_label} | Method: {method}", styles["Normal"]))
    elements.append(Spacer(1, 8 * mm))

    # Summary table
    summary_data = [
        ["Metric", "Amount (₹)"],
        ["Short-Term Capital Gains (STCG)", f"{summary.get('total_stcg', 0):,.2f}"],
        ["STCG Tax @ 20%", f"{summary.get('total_stcg_tax', 0):,.2f}"],
        ["Long-Term Capital Gains (LTCG)", f"{summary.get('total_ltcg', 0):,.2f}"],
        ["LTCG Exemption Used", f"{summary.get('ltcg_exemption_used', 0):,.2f}"],
        ["LTCG Tax @ 12.5%", f"{summary.get('total_ltcg_tax', 0):,.2f}"],
        ["Total Tax Liability", f"{summary.get('total_tax', 0):,.2f}"],
    ]
    t = Table(summary_data, colWidths=[280, 180])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))

    # Transactions table
    tx_header = ["Symbol", "Type", "Buy Date", "Sell Date", "Qty", "Buy ₹", "Sell ₹", "Gain ₹", "Days"]
    tx_rows = [tx_header]
    for symbol, data in report.get("by_symbol", {}).items():
        for tx in data.get("stcg_transactions", []):
            tx_rows.append([
                symbol, "STCG", tx.get("buy_date", ""), tx.get("sell_date", ""),
                str(tx.get("quantity", "")), str(tx.get("buy_price", "")),
                str(tx.get("sell_price", "")), str(tx.get("gain", "")),
                str(tx.get("holding_days", "")),
            ])
        for tx in data.get("ltcg_transactions", []):
            tx_rows.append([
                symbol, "LTCG", tx.get("buy_date", ""), tx.get("sell_date", ""),
                str(tx.get("quantity", "")), str(tx.get("buy_price", "")),
                str(tx.get("sell_price", "")), str(tx.get("gain", "")),
                str(tx.get("holding_days", "")),
            ])

    if len(tx_rows) > 1:
        elements.append(Paragraph("Transaction Details", styles["Heading2"]))
        col_w = [60, 36, 64, 64, 36, 56, 56, 56, 36]
        t2 = Table(tx_rows, colWidths=col_w, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(t2)

    # Disclaimer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "<i>Disclaimer: This report is for informational purposes only and does not constitute tax advice. "
        "Please consult a qualified Chartered Accountant for ITR filing. Generated by QuantLeap.</i>",
        styles["Normal"],
    ))

    doc.build(elements)
    buf.seek(0)
    log_export(user, "tax_report_pdf", db)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=tax-report-{portfolio.name}-{fy_label}.pdf"
        },
    )


# ---------------------------------------------------------------------------
# Share with CA (generates a pre-filled mailto link or returns share data)
# ---------------------------------------------------------------------------

@router.get("/portfolios/{portfolio_id}/capital-gains/share")
def get_share_data(
    portfolio_id: int,
    financial_year: Optional[str] = None,
    method: str = "FIFO",
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return share-friendly summary for emailing to a CA/tax advisor."""
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

    report = TaxCalculator.calculate_capital_gains(
        transactions, method=method, financial_year=financial_year
    )
    s = report.get("summary", {})
    fy_label = financial_year or "All Time"

    subject = f"Capital Gains Report — {portfolio.name} — FY {fy_label}"
    body_lines = [
        f"Hi,",
        f"",
        f"Please find my capital gains summary for FY {fy_label} (Portfolio: {portfolio.name}):",
        f"",
        f"Short-Term Capital Gains (STCG): ₹{s.get('total_stcg', 0):,.2f}",
        f"STCG Tax @ 20%: ₹{s.get('total_stcg_tax', 0):,.2f}",
        f"Long-Term Capital Gains (LTCG): ₹{s.get('total_ltcg', 0):,.2f}",
        f"LTCG Exemption Used: ₹{s.get('ltcg_exemption_used', 0):,.2f}",
        f"LTCG Tax @ 12.5%: ₹{s.get('total_ltcg_tax', 0):,.2f}",
        f"Total Estimated Tax: ₹{s.get('total_tax', 0):,.2f}",
        f"",
        f"Method: {method}",
        f"Symbols: {len(s.get('symbols', []))}",
        f"",
        f"I have attached the detailed CSV/PDF export for your reference.",
        f"",
        f"Thanks,",
        f"{user.full_name or user.username}",
        f"",
        f"— Generated by QuantLeap (https://quantleap.in)",
    ]

    return {
        "subject": subject,
        "body": "\n".join(body_lines),
        "summary": s,
    }
