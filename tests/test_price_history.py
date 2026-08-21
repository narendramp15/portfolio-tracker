"""Tests for price history storage.

The dashboard's growth chart, TWR, drawdown and volatility all read this
table, so the cases here cover the two ways it silently produced no data:
an upsert that only spoke Postgres and SQLite, and a backfill that never
fetched the benchmark index the chart compares against.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from portfolio_tracker.constants import BENCHMARK_SYMBOL
from portfolio_tracker.models import PriceHistoryModel
from portfolio_tracker.services.price_history import (
    PRICE_HISTORY_DAYS,
    PriceHistoryService,
)


@pytest.fixture
def service(db_session):
    return PriceHistoryService(db_session)


def _points(count: int, start: datetime = None, close: float = 100.0) -> list[dict]:
    start = start or datetime(2026, 1, 1)
    return [
        {"date": start + timedelta(days=i), "close": close + i}
        for i in range(count)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Retention
# ─────────────────────────────────────────────────────────────────────────────

def test_retention_covers_a_trailing_year():
    """The charts walk twelve month-ends; a 90-day window left nine of them
    hitting yfinance on every request."""
    assert PRICE_HISTORY_DAYS >= 366


# ─────────────────────────────────────────────────────────────────────────────
# Batch upsert
# ─────────────────────────────────────────────────────────────────────────────

def test_store_daily_closes_writes_every_point(service, db_session):
    written = service.store_daily_closes("TEST.NS", _points(5))

    assert written == 5
    rows = db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").all()
    assert len(rows) == 5


def test_store_daily_closes_is_idempotent(service, db_session):
    """Re-seeding must update in place, not duplicate or raise."""
    points = _points(4)
    service.store_daily_closes("TEST.NS", points)
    service.store_daily_closes("TEST.NS", points)

    rows = db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").all()
    assert len(rows) == 4


def test_store_daily_closes_updates_a_revised_close(service, db_session):
    when = datetime(2026, 1, 1)
    service.store_daily_closes("TEST.NS", [{"date": when, "close": 100.0}])
    service.store_daily_closes("TEST.NS", [{"date": when, "close": 123.5}])

    row = db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").one()
    assert Decimal(str(row.close)) == Decimal("123.50")


def test_store_daily_closes_collapses_duplicates_within_one_batch(service, db_session):
    """A repeated date inside the batch would trip the unique constraint
    before the upsert clause could apply."""
    when = datetime(2026, 1, 1)
    written = service.store_daily_closes(
        "TEST.NS",
        [{"date": when, "close": 100.0}, {"date": when, "close": 101.0}],
    )

    assert written == 1
    assert db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").count() == 1


def test_store_daily_closes_normalises_timestamps_to_midnight(service, db_session):
    """Intraday timestamps for the same session must not become two rows."""
    service.store_daily_closes(
        "TEST.NS",
        [
            {"date": datetime(2026, 1, 1, 9, 15), "close": 100.0},
            {"date": datetime(2026, 1, 1, 15, 30), "close": 105.0},
        ],
    )

    rows = db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").all()
    assert len(rows) == 1
    assert rows[0].date.hour == 0


def test_store_daily_closes_skips_incomplete_points(service):
    written = service.store_daily_closes(
        "TEST.NS",
        [
            {"date": datetime(2026, 1, 1), "close": None},
            {"date": None, "close": 100.0},
            {"date": datetime(2026, 1, 2), "close": 100.0},
        ],
    )

    assert written == 1


def test_store_daily_closes_handles_an_empty_batch(service):
    assert service.store_daily_closes("TEST.NS", []) == 0


def test_store_daily_close_singular_still_works(service, db_session):
    """The single-row helper now delegates, so it must keep its contract."""
    ok = service.store_daily_close("TEST.NS", datetime(2026, 1, 1), 100.0)

    assert ok is True
    assert db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").count() == 1


def test_store_daily_close_accepts_a_timezone_aware_date(service, db_session):
    """Broker and yfinance timestamps arrive aware; the column is naive."""
    ok = service.store_daily_close(
        "TEST.NS", datetime(2026, 1, 1, tzinfo=UTC), 100.0
    )

    assert ok is True
    assert db_session.query(PriceHistoryModel).filter_by(symbol="TEST.NS").count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark inclusion
# ─────────────────────────────────────────────────────────────────────────────

def test_backfill_includes_the_benchmark(service, monkeypatch):
    """Without the index there is nothing to compare holdings against, and
    the comparison line silently never appears."""
    requested = []

    def fake_backfill(symbol, days=None):
        requested.append(symbol)
        return 10

    monkeypatch.setattr(service, "backfill_symbol", fake_backfill)

    result = service.backfill_all_holdings()

    assert BENCHMARK_SYMBOL in requested
    assert result["benchmark_ok"] is True
    assert result["benchmark_symbol"] == BENCHMARK_SYMBOL


def test_backfill_can_skip_the_benchmark(service, monkeypatch):
    requested = []
    monkeypatch.setattr(
        service, "backfill_symbol", lambda symbol, days=None: requested.append(symbol) or 1
    )

    service.backfill_all_holdings(include_benchmark=False)

    assert BENCHMARK_SYMBOL not in requested


def test_backfill_reports_which_symbols_failed(service, monkeypatch):
    """A bare failure count hides which holdings are missing from charts."""
    monkeypatch.setattr(service, "backfill_symbol", lambda symbol, days=None: 0)

    result = service.backfill_all_holdings()

    assert result["failed_symbols"] == [BENCHMARK_SYMBOL]
    assert result["benchmark_ok"] is False


def test_backfill_does_not_request_the_benchmark_twice(service, monkeypatch):
    """A user genuinely holding an index tracker must not be double-fetched."""
    from portfolio_tracker.models import AssetModel, PortfolioModel

    portfolio = PortfolioModel(user_id=1, name="P")
    service.db.add(portfolio)
    service.db.flush()
    service.db.add(
        AssetModel(
            portfolio_id=portfolio.id,
            symbol=BENCHMARK_SYMBOL,
            name="Nifty",
            quantity=Decimal("1"),
            current_price=Decimal("100"),
            purchase_price=Decimal("100"),
        )
    )
    service.db.commit()

    requested = []
    monkeypatch.setattr(
        service, "backfill_symbol", lambda symbol, days=None: requested.append(symbol) or 1
    )

    service.backfill_all_holdings()

    assert requested.count(BENCHMARK_SYMBOL) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Reads
# ─────────────────────────────────────────────────────────────────────────────

def test_stored_history_reads_back_in_date_order(service):
    service.store_daily_closes("TEST.NS", _points(5, start=datetime(2026, 1, 1)))

    rows = service._get_from_db(
        "TEST.NS", datetime(2026, 1, 1), datetime(2026, 1, 10)
    )

    assert [r["close"] for r in rows] == sorted(r["close"] for r in rows)
    assert len(rows) == 5


def test_storage_stats_counts_symbols_and_rows(service):
    service.store_daily_closes("A.NS", _points(3))
    service.store_daily_closes("B.NS", _points(2))

    stats = service.get_storage_stats()

    assert stats["total_records"] == 5
    assert stats["unique_symbols"] == 2
    assert stats["retention_days"] == PRICE_HISTORY_DAYS


# ─────────────────────────────────────────────────────────────────────────────
# Bare-symbol resolution
# ─────────────────────────────────────────────────────────────────────────────

def test_a_bare_indian_symbol_is_resolved_via_its_nse_suffix(service, monkeypatch):
    """Rows predating symbol normalisation carry bare tickers and real trade
    history. Yahoo needs the suffix, so without this they can never be valued."""
    asked = []

    def fake_fetch(symbol, start, end):
        asked.append(symbol)
        return _points(3) if symbol == "RELIANCE.NS" else []

    monkeypatch.setattr(service, "_fetch_from_yfinance", fake_fetch)

    written = service.backfill_symbol("RELIANCE")

    assert asked == ["RELIANCE", "RELIANCE.NS"]
    assert written == 3


def test_resolved_prices_are_stored_under_the_symbol_as_given(service, db_session, monkeypatch):
    """The ledger looks up by its own symbol, so that is the storage key."""
    monkeypatch.setattr(
        service,
        "_fetch_from_yfinance",
        lambda symbol, start, end: _points(2) if symbol == "RELIANCE.NS" else [],
    )

    service.backfill_symbol("RELIANCE")

    assert db_session.query(PriceHistoryModel).filter_by(symbol="RELIANCE").count() == 2
    assert db_session.query(PriceHistoryModel).filter_by(symbol="RELIANCE.NS").count() == 0


def test_bse_is_tried_when_nse_has_nothing(service, monkeypatch):
    asked = []

    def fake_fetch(symbol, start, end):
        asked.append(symbol)
        return _points(1) if symbol.endswith(".BO") else []

    monkeypatch.setattr(service, "_fetch_from_yfinance", fake_fetch)

    assert service.backfill_symbol("MISHTANN") == 1
    assert asked == ["MISHTANN", "MISHTANN.NS", "MISHTANN.BO"]


def test_an_already_suffixed_symbol_is_not_retried(service, monkeypatch):
    """No point appending .NS to something that already has an exchange."""
    asked = []
    monkeypatch.setattr(
        service,
        "_fetch_from_yfinance",
        lambda symbol, start, end: asked.append(symbol) or [],
    )

    service.backfill_symbol("TCS.NS")

    assert asked == ["TCS.NS"]


def test_the_index_symbol_is_not_suffixed(service, monkeypatch):
    """^NSEI is already a Yahoo index ticker; ^NSEI.NS does not exist."""
    asked = []
    monkeypatch.setattr(
        service,
        "_fetch_from_yfinance",
        lambda symbol, start, end: asked.append(symbol) or [],
    )

    service.backfill_symbol(BENCHMARK_SYMBOL)

    assert asked == [BENCHMARK_SYMBOL]
