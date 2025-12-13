"""Tests for core module."""

from decimal import Decimal

from portfolio_tracker.core import PortfolioTracker


class TestPortfolioTracker:
    """Test PortfolioTracker class."""

    def test_create_portfolio(self):
        """Test portfolio creation."""
        tracker = PortfolioTracker()
        portfolio = tracker.create_portfolio("Test Portfolio")

        assert portfolio.name == "Test Portfolio"
        assert len(tracker.portfolios) == 1

    def test_get_portfolio(self):
        """Test getting a portfolio by name."""
        tracker = PortfolioTracker()
        tracker.create_portfolio("Test Portfolio")

        portfolio = tracker.get_portfolio("Test Portfolio")
        assert portfolio is not None
        assert portfolio.name == "Test Portfolio"

    def test_get_nonexistent_portfolio(self):
        """Test getting a nonexistent portfolio."""
        tracker = PortfolioTracker()
        portfolio = tracker.get_portfolio("Nonexistent")

        assert portfolio is None

    def test_delete_portfolio(self):
        """Test deleting a portfolio."""
        tracker = PortfolioTracker()
        tracker.create_portfolio("Test Portfolio")

        result = tracker.delete_portfolio("Test Portfolio")
        assert result is True
        assert len(tracker.portfolios) == 0

    def test_delete_nonexistent_portfolio(self):
        """Test deleting a nonexistent portfolio."""
        tracker = PortfolioTracker()
        result = tracker.delete_portfolio("Nonexistent")

        assert result is False

    def test_get_all_portfolios(self):
        """Test getting all portfolios."""
        tracker = PortfolioTracker()
        tracker.create_portfolio("Portfolio 1")
        tracker.create_portfolio("Portfolio 2")

        portfolios = tracker.get_all_portfolios()
        assert len(portfolios) == 2

    def test_get_total_value(self):
        """Test calculating total value."""
        tracker = PortfolioTracker()
        portfolio = tracker.create_portfolio("Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0)
        portfolio.add_asset("GOOGL", "Google", 5, current_price=200.0)

        total_value = tracker.get_total_value()
        assert total_value == Decimal("2000")  # (10 * 100) + (5 * 200)
