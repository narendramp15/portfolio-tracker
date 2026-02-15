"""End-to-end tests for trading journal feature."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from portfolio_tracker import database, models
from portfolio_tracker.auth import create_access_token, hash_password


class TestTradingJournalE2E:
    """End-to-end tests for complete user trading workflow."""

    @pytest.fixture
    def setup_database(self):
        """Set up test database with sample data."""
        # Create in-memory SQLite database
        engine = database.create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=engine)
        Base = database.Base
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Create test user and portfolio
        session = TestingSessionLocal()
        user = models.UserModel(
            email="trader@example.com",
            username="trader",
            hashed_password=hash_password("password123"),
            is_active=True
        )
        session.add(user)
        session.commit()
        
        portfolio = models.PortfolioModel(
            user_id=user.id,
            name="Trading Portfolio",
            description="Main trading account"
        )
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)
        
        # Create token
        token = create_access_token(data={"sub": user.email})
        
        yield {
            "session": session,
            "user": user,
            "portfolio": portfolio,
            "token": token,
            "TestingSessionLocal": TestingSessionLocal,
            "engine": engine
        }
        
        # Cleanup
        session.close()
        engine.dispose()

    def test_user_complete_trading_journey(self, setup_database):
        """Test complete user journey from login to trade analysis."""
        client = TestClient(setup_database["engine"])
        headers = {"Authorization": f"Bearer {setup_database['token']}"}
        portfolio_id = setup_database["portfolio"].id
        
        # Step 1: User logs in (implicit via token) and navigates to trading journal
        # This is simulated by making an authenticated request
        
        # Step 2: User creates their first trade
        first_trade = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z",
            "notes": "Starting a position in Reliance"
        }
        
        response = client.post(f"/api/journal/{portfolio_id}", json=first_trade, headers=headers)
        assert response.status_code == 201
        first_trade_response = response.json()
        first_trade_id = first_trade_response["id"]
        
        # Verify trade was created with auto-generated trade_id
        assert first_trade_response["trade_id"] == 1
        assert first_trade_response["profit_loss"] is None  # No exit yet
        
        # Step 3: User adds more trades over time
        trades = [
            {"symbol": "TCS.NS", "entry_price": "3500.00", "quantity": "5", "entry_date": "2024-06-02T09:00:00Z"},
            {"symbol": "INFY.NS", "entry_price": "1500.00", "quantity": "20", "entry_date": "2024-06-03T11:00:00Z"},
        ]
        
        for trade in trades:
            response = client.post(f"/api/journal/{portfolio_id}", json=trade, headers=headers)
            assert response.status_code == 201
        
        # Step 4: User views their journal
        journal_response = client.get(f"/api/journal/{portfolio_id}", headers=headers)
        assert journal_response.status_code == 200
        journal = journal_response.json()
        assert len(journal) == 3
        
        # Step 5: User updates a trade with exit details
        update_response = client.patch(
            f"/api/journal/{portfolio_id}/{first_trade_id}",
            json={
                "exit_price": "2700.00",
                "exit_date": "2024-06-15T14:30:00Z",
                "notes": "Took profit at resistance"
            },
            headers=headers
        )
        assert update_response.status_code == 200
        updated_trade = update_response.json()
        assert updated_trade["profit_loss"] == "2000.00"  # (2700-2500)*10
        
        # Step 6: User checks their performance statistics
        stats_response = client.get(f"/api/journal/{portfolio_id}/stats", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert stats["total_trades"] == 3
        assert stats["winning_trades"] == 1
        assert stats["losing_trades"] == 0  # Only one trade closed
        assert stats["total_profit_loss"] == "2000.00"
        
        # Step 7: User filters to see only RELIANCE trades
        filtered_response = client.get(f"/api/journal/{portfolio_id}?symbol=RELIANCE.NS", headers=headers)
        assert filtered_response.status_code == 200
        filtered = filtered_response.json()
        assert len(filtered) == 1
        assert filtered[0]["symbol"] == "RELIANCE.NS"
        
        # Step 8: User closes another trade
        second_trade_id = journal[1]["id"]  # TCS trade
        close_response = client.patch(
            f"/api/journal/{portfolio_id}/{second_trade_id}",
            json={
                "exit_price": "3600.00",
                "exit_date": "2024-06-20T16:00:00Z"
            },
            headers=headers
        )
        assert close_response.status_code == 200
        
        # Step 9: User checks updated statistics
        updated_stats_response = client.get(f"/api/journal/{portfolio_id}/stats", headers=headers)
        updated_stats = updated_stats_response.json()
        
        assert updated_stats["total_trades"] == 3
        assert updated_stats["winning_trades"] == 2  # Now 2 winning trades
        assert updated_stats["win_rate"] == pytest.approx(66.67, rel=1.0)
        
        # Step 10: User deletes a trade (maybe a mistake)
        third_trade_id = journal[2]["id"]  # INFY trade
        delete_response = client.delete(f"/api/journal/{portfolio_id}/{third_trade_id}", headers=headers)
        assert delete_response.status_code == 204
        
        # Step 11: User verifies the deletion
        final_journal_response = client.get(f"/api/journal/{portfolio_id}", headers=headers)
        final_journal = final_journal_response.json()
        assert len(final_journal) == 2
        
        # Final stats should reflect the deleted trade
        final_stats_response = client.get(f"/api/journal/{portfolio_id}/stats", headers=headers)
        final_stats = final_stats_response.json()
        assert final_stats["total_trades"] == 2

    def test_broker_import_workflow_simulation(self, setup_database):
        """Simulate importing trades from a broker API."""
        client = TestClient(setup_database["engine"])
        headers = {"Authorization": f"Bearer {setup_database['token']}"}
        portfolio_id = setup_database["portfolio"].id
        
        # Simulate broker data import
        broker_trades = [
            {
                "symbol": "RELIANCE.NS",
                "entry_price": "2485.50",
                "exit_price": "2520.00",
                "quantity": "25",
                "entry_date": "2024-06-01T09:15:00Z",
                "exit_date": "2024-06-10T15:30:00Z"
            },
            {
                "symbol": "TCS.NS",
                "entry_price": "3490.00",
                "exit_price": "3550.00",
                "quantity": "10",
                "entry_date": "2024-06-05T10:00:00Z",
                "exit_date": "2024-06-12T14:00:00Z"
            },
            {
                "symbol": "HDFCBANK.NS",
                "entry_price": "1600.00",
                "exit_price": "1585.00",
                "quantity": "15",
                "entry_date": "2024-06-08T11:30:00Z",
                "exit_date": "2024-06-18T09:45:00Z"
            }
        ]
        
        # Import trades
        for trade in broker_trades:
            response = client.post(f"/api/journal/{portfolio_id}", json=trade, headers=headers)
            assert response.status_code == 201
        
        # Verify imports
        journal_response = client.get(f"/api/journal/{portfolio_id}", headers=headers)
        assert len(journal_response.json()) == 3
        
        # Check calculated statistics
        stats_response = client.get(f"/api/journal/{portfolio_id}/stats", headers=headers)
        stats = stats_response.json()
        
        # Calculations:
        # RELIANCE: (2520-2485.50)*25 = 34.50*25 = 862.50
        # TCS: (3550-3490)*10 = 60*10 = 600
        # HDFCBANK: (1585-1600)*15 = -15*15 = -225
        # Total: 862.50 + 600 - 225 = 1237.50
        assert Decimal(stats["total_profit_loss"]) == Decimal("1237.50")
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 1
        assert stats["win_rate"] == pytest.approx(66.67, rel=1.0)
        assert Decimal(stats["best_trade"]) == Decimal("862.50")
        assert Decimal(stats["worst_trade"]) == Decimal("-225.00")

    def test_manual_entry_workflow(self, setup_database):
        """Test manual trade entry workflow with validation."""
        client = TestClient(setup_database["engine"])
        headers = {"Authorization": f"Bearer {setup_database['token']}"}
        portfolio_id = setup_database["portfolio"].id
        
        # Step 1: Try to create trade with invalid data
        invalid_trade = {
            "symbol": "",  # Empty symbol
            "entry_price": "-100.00",  # Negative price
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z"
        }
        
        response = client.post(f"/api/journal/{portfolio_id}", json=invalid_trade, headers=headers)
        assert response.status_code == 422  # Validation error
        
        # Step 2: Create valid trade
        valid_trade = {
            "symbol": "RELIANCE.NS",
            "entry_price": "2500.00",
            "exit_price": "2750.00",
            "quantity": "10",
            "entry_date": "2024-06-01T10:00:00Z",
            "exit_date": "2024-06-15T14:30:00Z",
            "notes": "Manual entry - validated trade"
        }
        
        response = client.post(f"/api/journal/{portfolio_id}", json=valid_trade, headers=headers)
        assert response.status_code == 201
        created = response.json()
        
        # Step 3: Verify profit/loss was calculated correctly
        assert Decimal(created["profit_loss"]) == Decimal("2500.00")  # (2750-2500)*10
