"""
Price History Service - Efficient storage for free tier deployments.

Strategy:
- Store only last 90 days in DB (configurable via PRICE_HISTORY_DAYS)
- Fetch older data on-demand from yfinance (free API)
- Only track symbols users actually hold
- Automatic cleanup of old data to save space
"""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import and_, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from portfolio_tracker.models import AssetModel, PriceHistoryModel

# Configuration
PRICE_HISTORY_DAYS = int(os.getenv("PRICE_HISTORY_DAYS", "90"))  # Days to store in DB


class PriceHistoryService:
    """Service for managing historical price data efficiently."""

    def __init__(self, db: Session):
        self.db = db
        self.retention_days = PRICE_HISTORY_DAYS

    def get_price_history(
        self,
        symbol: str,
        days: int = 90,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Get price history for a symbol. Uses DB for recent data, yfinance for older.
        
        Returns list of {"date": datetime, "close": float}
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=days)

        # Try to get from DB first (recent data)
        db_cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        
        if start_date >= db_cutoff:
            # All requested data is within DB retention period
            return self._get_from_db(symbol, start_date, end_date)
        elif end_date <= db_cutoff:
            # All requested data is older than retention - fetch from yfinance
            return self._fetch_from_yfinance(symbol, start_date, end_date)
        else:
            # Mixed: some from DB, some from yfinance
            yf_data = self._fetch_from_yfinance(symbol, start_date, db_cutoff)
            db_data = self._get_from_db(symbol, db_cutoff, end_date)
            return yf_data + db_data

    def _get_from_db(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Get price history from database."""
        records = (
            self.db.query(PriceHistoryModel)
            .filter(
                and_(
                    PriceHistoryModel.symbol == symbol,
                    PriceHistoryModel.date >= start_date,
                    PriceHistoryModel.date <= end_date,
                )
            )
            .order_by(PriceHistoryModel.date)
            .all()
        )
        return [{"date": r.date, "close": float(r.close)} for r in records]

    def _fetch_from_yfinance(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Fetch historical data from yfinance (free API)."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return []

            return [
                {"date": idx.to_pydatetime(), "close": float(row["Close"])}
                for idx, row in hist.iterrows()
            ]
        except Exception as e:
            print(f"[PriceHistory] Error fetching {symbol} from yfinance: {e}")
            return []

    def store_daily_close(self, symbol: str, date: datetime, close: float) -> bool:
        """
        Store a single daily close price. Uses upsert to handle duplicates.
        """
        try:
            # Normalize date to midnight UTC
            date_normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if using PostgreSQL or SQLite
            dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
            
            if dialect == "postgresql":
                stmt = pg_insert(PriceHistoryModel).values(
                    symbol=symbol,
                    date=date_normalized,
                    close=Decimal(str(close)),
                ).on_conflict_do_update(
                    constraint="uix_symbol_date",
                    set_={"close": Decimal(str(close))},
                )
            else:
                # SQLite - use INSERT OR REPLACE
                stmt = sqlite_insert(PriceHistoryModel).values(
                    symbol=symbol,
                    date=date_normalized,
                    close=Decimal(str(close)),
                ).on_conflict_do_update(
                    index_elements=["symbol", "date"],
                    set_={"close": Decimal(str(close))},
                )
            
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as e:
            print(f"[PriceHistory] Error storing {symbol} price: {e}")
            self.db.rollback()
            return False

    def backfill_symbol(self, symbol: str, days: int = None) -> int:
        """
        Backfill price history for a symbol from yfinance.
        Only fetches data within retention period to save space.
        Returns number of records added.
        """
        if days is None:
            days = self.retention_days
        
        # Don't fetch more than retention period
        days = min(days, self.retention_days)
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        data = self._fetch_from_yfinance(symbol, start_date, end_date)
        
        count = 0
        for item in data:
            if self.store_daily_close(symbol, item["date"], item["close"]):
                count += 1
        
        return count

    def backfill_all_holdings(self, user_id: int = None) -> dict:
        """
        Backfill price history for all symbols in user portfolios.
        If user_id is None, backfills for all users.
        """
        # Get unique symbols from assets
        query = self.db.query(AssetModel.symbol).distinct()
        
        if user_id:
            from portfolio_tracker.models import PortfolioModel
            query = query.join(PortfolioModel).filter(PortfolioModel.user_id == user_id)
        
        symbols = [r[0] for r in query.all()]
        
        results = {"success": 0, "failed": 0, "symbols": {}}
        for symbol in symbols:
            count = self.backfill_symbol(symbol)
            if count > 0:
                results["success"] += 1
                results["symbols"][symbol] = count
            else:
                results["failed"] += 1
        
        return results

    def cleanup_old_data(self) -> int:
        """
        Remove price history older than retention period.
        Run this periodically (daily cron) to keep storage lean.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        
        result = self.db.execute(
            delete(PriceHistoryModel).where(PriceHistoryModel.date < cutoff)
        )
        self.db.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            print(f"[PriceHistory] Cleaned up {deleted_count} old records")
        
        return deleted_count

    def get_storage_stats(self) -> dict:
        """Get storage statistics for monitoring."""
        from sqlalchemy import func
        
        total_records = self.db.query(func.count(PriceHistoryModel.id)).scalar()
        unique_symbols = self.db.query(func.count(func.distinct(PriceHistoryModel.symbol))).scalar()
        
        # Estimate storage (roughly 40 bytes per row)
        estimated_bytes = total_records * 40
        
        return {
            "total_records": total_records,
            "unique_symbols": unique_symbols,
            "estimated_storage_bytes": estimated_bytes,
            "estimated_storage_kb": round(estimated_bytes / 1024, 2),
            "retention_days": self.retention_days,
        }


# Singleton-ish helper for use in routes
def get_price_history_service(db: Session) -> PriceHistoryService:
    return PriceHistoryService(db)
