"""Tests for trading journal API endpoints."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from portfolio_tracker import models


class TestTradingJournalAPI:
    """Test trading journal API endpoints."""

    def test_create_journal_entry(self, client, auth_headers, test_portfolio):
        """Test creating a new trading journal entry."""
        entry_data = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "exit_price": "2700.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z",
            "exit_date": "2024-06-15T14:30:00Z",
            "notes": "Test trade entry"
        }
        
        response = client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=entry_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "RELIANCE.NS"
        assert data["trade_id"] == 1
        assert Decimal(data["entry_price"]) == Decimal("2500.00")
        assert Decimal(data["exit_price"]) == Decimal("2700.00")
        assert Decimal(data["quantity"]) == Decimal("10")
        assert Decimal(data["profit_loss"]) == Decimal("2000.00")  # (2700-2500) * 10

    def test_create_journal_entry_without_exit(self, client, auth_headers, test_portfolio):
        """Test creating a journal entry without exit price/date."""
        entry_data = {
            "symbol": "TCS.NS",
            "entry_price": "3500.00",
            "quantity": "5",
            "entry_date": "2024-06-01T10:00:00Z",
            "notes": "Open position"
        }
        
        response = client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=entry_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "TCS.NS"
        assert data["exit_price"] is None
        assert data["exit_date"] is None
        assert data["profit_loss"] is None

    def test_create_journal_entry_invalid_portfolio(self, client, auth_headers):
        """Test creating entry for non-existent portfolio."""
        entry_data = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        
        response = client.post(
            "/api/journal/99999",
            json=entry_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Portfolio not found" in response.json()["detail"]

    def test_create_journal_entry_unauthorized(self, client, test_portfolio):
        """Test creating entry without authentication."""
        entry_data = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        
        response = client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=entry_data
        )
        
        assert response.status_code == 401

    def test_get_portfolio_journal(self, client, auth_headers, test_portfolio, db_session):
        """Test getting all journal entries for a portfolio."""
        # Create some entries first
        entry1 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            exit_price=Decimal("2700.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("2000.00"),
            notes="First trade"
        )
        entry2 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=2,
            symbol="TCS.NS",
            entry_price=Decimal("3500.00"),
            exit_price=Decimal("3400.00"),
            quantity=Decimal("5"),
            entry_date=datetime(2024, 6, 5, 9, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("-500.00"),
            notes="Second trade"
        )
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()
        
        response = client.get(
            f"/api/journal/{test_portfolio['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "TCS.NS"  # Most recent first

    def test_get_journal_stats(self, client, auth_headers, test_portfolio, db_session):
        """Test getting journal statistics."""
        # Create winning and losing trades
        entry1 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            exit_price=Decimal("2700.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("2000.00")
        )
        entry2 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=2,
            symbol="TCS.NS",
            entry_price=Decimal("3500.00"),
            exit_price=Decimal("3400.00"),
            quantity=Decimal("5"),
            entry_date=datetime(2024, 6, 5, 9, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("-500.00")
        )
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()
        
        response = client.get(
            f"/api/journal/{test_portfolio['id']}/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 2
        assert data["winning_trades"] == 1
        assert data["losing_trades"] == 1
        assert data["win_rate"] == 50.0
        assert Decimal(data["total_profit_loss"]) == Decimal("1500.00")
        assert Decimal(data["best_trade"]) == Decimal("2000.00")
        assert Decimal(data["worst_trade"]) == Decimal("-500.00")

    def test_get_journal_entry(self, client, auth_headers, test_portfolio, db_session):
        """Test getting a specific journal entry."""
        entry = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            exit_price=Decimal("2700.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("2000.00"),
            notes="Test trade"
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        response = client.get(
            f"/api/journal/{test_portfolio['id']}/{entry.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "RELIANCE.NS"
        assert data["profit_loss"] == "2000.00"

    def test_get_nonexistent_entry(self, client, auth_headers, test_portfolio):
        """Test getting a non-existent journal entry."""
        response = client.get(
            f"/api/journal/{test_portfolio['id']}/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Journal entry not found" in response.json()["detail"]

    def test_update_journal_entry(self, client, auth_headers, test_portfolio, db_session):
        """Test updating a journal entry."""
        entry = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            exit_price=Decimal("2700.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
            profit_loss=Decimal("2000.00")
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        update_data = {
            "exit_price": "2750.00",
            "exit_date": "2024-06-20T16:00:00Z",
            "notes": "Updated exit"
        }
        
        response = client.patch(
            f"/api/journal/{test_portfolio['id']}/{entry.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["exit_price"]) == Decimal("2750.00")
        assert data["notes"] == "Updated exit"
        # Profit/loss should be recalculated
        assert Decimal(data["profit_loss"]) == Decimal("2500.00")  # (2750-2500) * 10

    def test_delete_journal_entry(self, client, auth_headers, test_portfolio, db_session):
        """Test deleting a journal entry."""
        entry = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        response = client.delete(
            f"/api/journal/{test_portfolio['id']}/{entry.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify entry is deleted
        get_response = client.get(
            f"/api/journal/{test_portfolio['id']}/{entry.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_get_journal_with_symbol_filter(self, client, auth_headers, test_portfolio, db_session):
        """Test filtering journal entries by symbol."""
        entry1 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        entry2 = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=2,
            symbol="TCS.NS",
            entry_price=Decimal("3500.00"),
            quantity=Decimal("5"),
            entry_date=datetime(2024, 6, 5, 9, 0, 0, tzinfo=timezone.utc)
        )
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()
        
        response = client.get(
            f"/api/journal/{test_portfolio['id']}?symbol=RELIANCE.NS",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "RELIANCE.NS"

    def test_get_empty_journal_stats(self, client, auth_headers, test_portfolio):
        """Test getting stats when no trades exist."""
        response = client.get(
            f"/api/journal/{test_portfolio['id']}/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["winning_trades"] == 0
        assert data["losing_trades"] == 0
        assert data["win_rate"] == 0.0
        assert Decimal(data["total_profit_loss"]) == Decimal("0")

    def test_auto_increment_trade_id(self, client, auth_headers, test_portfolio):
        """Test that trade_id auto-increments within a portfolio."""
        entry1 = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        entry2 = {
            "symbol": "TCS.NS",
            "entry_price": "3500.00",
            "quantity": "5",
            "entry_date": "2024-06-02T10:00:00Z"
        }
        
        response1 = client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=entry1,
            headers=auth_headers
        )
        assert response1.json()["trade_id"] == 1
        
        response2 = client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=entry2,
            headers=auth_headers
        )
        assert response2.json()["trade_id"] == 2


class TestTradingJournalSchemas:
    """Test trading journal Pydantic schemas."""

    def test_trading_journal_create_valid(self):
        """Test valid trading journal creation schema."""
        from portfolio_tracker.schemas import TradingJournalCreate
        
        data = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        
        schema = TradingJournalCreate(**data)
        assert schema.symbol == "RELIANCE.NS"
        assert schema.entry_price == Decimal("2500.00")

    def test_trading_journal_create_invalid_price(self):
        """Test invalid entry price in schema."""
        from pydantic import ValidationError

        from portfolio_tracker.schemas import TradingJournalCreate
        
        data = {
            "symbol": "RELIANCE.NS",
            "entry_price": "-100.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        
        with pytest.raises(ValidationError):
            TradingJournalCreate(**data)

    def test_trading_journal_update(self):
        """Test trading journal update schema."""
        from portfolio_tracker.schemas import TradingJournalUpdate
        
        data = {
            "exit_price": "2700.00",
            "exit_date": "2024-06-15T14:30:00Z",
            "notes": "Updated trade"
        }
        
        schema = TradingJournalUpdate(**data)
        assert schema.exit_price == Decimal("2700.00")
        assert schema.notes == "Updated trade"

    def test_trading_journal_summary(self):
        """Test trading journal summary schema."""
        from portfolio_tracker.schemas import TradingJournalSummary
        
        data = {
            "total_trades": 10,
            "winning_trades": 6,
            "losing_trades": 4,
            "win_rate": 60.0,
            "total_profit_loss": "15000.00",
            "average_profit_loss": "1500.00",
            "best_trade": "5000.00",
            "worst_trade": "-1000.00"
        }
        
        schema = TradingJournalSummary(**data)
        assert schema.total_trades == 10
        assert schema.win_rate == 60.0
