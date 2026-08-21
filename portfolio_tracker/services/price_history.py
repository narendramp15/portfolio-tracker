"""
Price History Service - daily closes for holdings and the benchmark.

Strategy:
- Retain enough history in the DB to serve the dashboard's trailing-year
  charts without a live fetch (PRICE_HISTORY_DAYS, default 400)
- Fall back to yfinance only for windows older than retention
- Track the symbols users hold, plus the benchmark index
- Periodic cleanup trims anything past retention

Retention deliberately exceeds one year. The portfolio growth chart and the
TWR/drawdown figures walk twelve month-ends, so a 90-day window meant nine
of those twelve points hit yfinance on every page load - slow, and the
fastest way to get rate-limited off an unofficial API. Storage is not the
constraint it looks like: a 50-symbol portfolio over 400 days is roughly
14,000 rows, well under a megabyte.
"""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy import and_, delete
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from portfolio_tracker.constants import BENCHMARK_SYMBOL
from portfolio_tracker.models import AssetModel, PriceHistoryModel

# Configuration. 400 days covers a trailing-year chart plus slack for
# weekends, holidays and month-end alignment.
PRICE_HISTORY_DAYS = int(os.getenv("PRICE_HISTORY_DAYS", "400"))  # Days to store in DB


def _to_naive_utc(value: datetime) -> datetime:
    """Convert to naive UTC, matching the naive `price_history.date` column.

    Callers pass both kinds, and comparing the two raises TypeError, so every
    boundary is normalised here rather than at each comparison.
    """
    if value is None:
        return value
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


class PriceHistoryService:
    """Service for managing historical price data efficiently."""

    def __init__(self, db: Session):
        self.db = db
        self.retention_days = PRICE_HISTORY_DAYS

    def get_price_history(
        self,
        symbol: str,
        days: int = 90,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """
        Get price history for a symbol. Uses DB for recent data, yfinance for older.

        Returns list of {"date": datetime, "close": float}

        Bounds are normalised to naive UTC before any comparison. The stored
        column is naive, but callers legitimately pass either kind - the
        analytics layer works in naive datetimes while this class's own
        defaults were aware, and mixing the two raised TypeError on the very
        first comparison. That surfaced as "no price history" for every symbol
        rather than as an error, so a fully populated table still produced an
        empty chart.
        """
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=days)

        start_date = _to_naive_utc(start_date)
        end_date = _to_naive_utc(end_date)

        # Try to get from DB first (recent data)
        db_cutoff = _to_naive_utc(datetime.now(UTC)) - timedelta(
            days=self.retention_days
        )

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

        Delegates to :meth:`store_daily_closes` so there is one upsert
        implementation to keep dialect-correct. The previous version fell
        through to SQLite's ON CONFLICT syntax for any non-Postgres backend,
        which is invalid on MySQL/MariaDB - the dialect this deployment
        actually runs.
        """
        return self.store_daily_closes(symbol, [{"date": date, "close": close}]) == 1

    def store_daily_closes(self, symbol: str, points: list[dict]) -> int:
        """
        Store many daily closes for one symbol in a single transaction.

        ``store_daily_close`` commits per row, which is fine for a one-off
        update but turns a backfill into thousands of round trips against a
        remote database. This upserts the whole series at once.

        Args:
            symbol: Ticker to store under.
            points: ``[{"date": datetime, "close": float}, ...]``

        Returns:
            Number of rows written, or 0 if the batch failed.
        """
        if not points:
            return 0

        rows = []
        seen_dates = set()
        for item in points:
            close = item.get("close")
            when = item.get("date")
            if close is None or when is None:
                continue
            normalized = when.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            # One row per (symbol, date): a duplicate inside the batch would
            # trip the unique constraint before the upsert clause applies.
            if normalized in seen_dates:
                continue
            seen_dates.add(normalized)
            rows.append(
                {"symbol": symbol, "date": normalized, "close": Decimal(str(close))}
            )

        if not rows:
            return 0

        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        try:
            if dialect == "postgresql":
                stmt = pg_insert(PriceHistoryModel).values(rows)
                stmt = stmt.on_conflict_do_update(
                    constraint="uix_symbol_date",
                    set_={"close": stmt.excluded.close},
                )
            elif dialect == "sqlite":
                stmt = sqlite_insert(PriceHistoryModel).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "date"],
                    set_={"close": stmt.excluded.close},
                )
            else:
                # MySQL / MariaDB: ON DUPLICATE KEY UPDATE.
                stmt = mysql_insert(PriceHistoryModel).values(rows)
                stmt = stmt.on_duplicate_key_update(close=stmt.inserted.close)

            self.db.execute(stmt)
            self.db.commit()
            return len(rows)
        except Exception as e:
            print(f"[PriceHistory] Error storing {symbol} batch: {e}")
            self.db.rollback()
            return 0

    # Exchange suffixes tried for a bare Indian symbol, NSE first.
    _FALLBACK_SUFFIXES = (".NS", ".BO")

    def backfill_symbol(self, symbol: str, days: int = None) -> int:
        """
        Backfill price history for a symbol from yfinance.
        Fetches at most the retention window, since anything older would be
        deleted by the next cleanup anyway.
        Returns number of records added.

        A bare symbol ("RELIANCE") returns nothing from Yahoo, which needs an
        exchange suffix ("RELIANCE.NS"). Older rows in this database predate
        symbol normalisation and still carry bare tickers, and they hold real
        transaction history, so the price is fetched under the suffixed form
        and stored under the symbol as given - otherwise those holdings can
        never be valued and every chart quietly undercounts them.
        """
        if days is None:
            days = self.retention_days

        # Don't fetch more than retention period
        days = min(days, self.retention_days)

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        data = self._fetch_from_yfinance(symbol, start_date, end_date)

        if not data and "." not in symbol and not symbol.startswith("^"):
            for suffix in self._FALLBACK_SUFFIXES:
                data = self._fetch_from_yfinance(f"{symbol}{suffix}", start_date, end_date)
                if data:
                    print(
                        f"[PriceHistory] {symbol} resolved via {symbol}{suffix}; "
                        f"stored under {symbol}"
                    )
                    break

        return self.store_daily_closes(symbol, data)

    def backfill_all_holdings(
        self, user_id: int = None, include_benchmark: bool = True
    ) -> dict:
        """
        Backfill price history for all symbols in user portfolios.
        If user_id is None, backfills for all users.

        The benchmark index is included by default: without it the dashboard
        has holdings to plot but nothing to compare them against, so the
        comparison line silently never appears.
        """
        # Get unique symbols from assets
        query = self.db.query(AssetModel.symbol).distinct()

        if user_id:
            from portfolio_tracker.models import PortfolioModel
            query = query.join(PortfolioModel).filter(PortfolioModel.user_id == user_id)

        symbols = [r[0] for r in query.all()]

        if include_benchmark and BENCHMARK_SYMBOL not in symbols:
            symbols.append(BENCHMARK_SYMBOL)

        results = {"success": 0, "failed": 0, "symbols": {}, "failed_symbols": []}
        for symbol in symbols:
            count = self.backfill_symbol(symbol)
            if count > 0:
                results["success"] += 1
                results["symbols"][symbol] = count
            else:
                # Name what failed. A bare count hides which holdings are
                # missing from every chart that reads this table.
                results["failed"] += 1
                results["failed_symbols"].append(symbol)

        results["benchmark_symbol"] = BENCHMARK_SYMBOL
        results["benchmark_ok"] = results["symbols"].get(BENCHMARK_SYMBOL, 0) > 0
        return results

    def cleanup_old_data(self) -> int:
        """
        Remove price history older than retention period.
        Run this periodically (daily cron) to keep storage lean.
        """
        cutoff = datetime.now(UTC) - timedelta(days=self.retention_days)

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
