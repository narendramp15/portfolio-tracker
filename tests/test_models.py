"""Tests for models module."""

from decimal import Decimal

from portfolio_tracker.models import Asset, Portfolio


class TestAsset:
    """Test Asset class."""

    def test_asset_creation(self):
        """Test creating an asset."""
        asset = Asset(
            symbol="AAPL",
            name="Apple",
            quantity=10,
            current_price=100.0,
            purchase_price=80.0,
        )

        assert asset.symbol == "AAPL"
        assert asset.quantity == 10

    def test_get_current_value(self):
        """Test calculating current value."""
        asset = Asset(
            symbol="AAPL",
            name="Apple",
            quantity=10,
            current_price=100.0,
        )

        assert asset.get_current_value() == Decimal("1000")

    def test_get_cost_basis(self):
        """Test calculating cost basis."""
        asset = Asset(
            symbol="AAPL",
            name="Apple",
            quantity=10,
            purchase_price=80.0,
        )

        assert asset.get_cost_basis() == Decimal("800")

    def test_get_gain_loss(self):
        """Test calculating gain/loss."""
        asset = Asset(
            symbol="AAPL",
            name="Apple",
            quantity=10,
            current_price=100.0,
            purchase_price=80.0,
        )

        assert asset.get_gain_loss() == Decimal("200")

    def test_get_gain_loss_percent(self):
        """Test calculating gain/loss percentage."""
        asset = Asset(
            symbol="AAPL",
            name="Apple",
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            purchase_price=Decimal("80"),
        )

        assert asset.get_gain_loss_percent() == Decimal("25")


class TestPortfolio:
    """Test Portfolio class."""

    def test_portfolio_creation(self):
        """Test creating a portfolio."""
        portfolio = Portfolio(name="Test Portfolio")

        assert portfolio.name == "Test Portfolio"
        assert len(portfolio.assets) == 0

    def test_add_asset(self):
        """Test adding an asset to portfolio."""
        portfolio = Portfolio(name="Test Portfolio")
        asset = portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0)

        assert asset.symbol == "AAPL"
        assert "AAPL" in portfolio.assets

    def test_get_asset(self):
        """Test getting an asset from portfolio."""
        portfolio = Portfolio(name="Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0)

        asset = portfolio.get_asset("AAPL")
        assert asset is not None
        assert asset.symbol == "AAPL"

    def test_get_nonexistent_asset(self):
        """Test getting a nonexistent asset."""
        portfolio = Portfolio(name="Test Portfolio")
        asset = portfolio.get_asset("NONEXISTENT")

        assert asset is None

    def test_remove_asset(self):
        """Test removing an asset from portfolio."""
        portfolio = Portfolio(name="Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0)

        result = portfolio.remove_asset("AAPL")
        assert result is True
        assert "AAPL" not in portfolio.assets

    def test_remove_nonexistent_asset(self):
        """Test removing a nonexistent asset."""
        portfolio = Portfolio(name="Test Portfolio")
        result = portfolio.remove_asset("NONEXISTENT")

        assert result is False

    def test_get_total_value(self):
        """Test calculating total portfolio value."""
        portfolio = Portfolio(name="Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0)
        portfolio.add_asset("GOOGL", "Google", 5, current_price=200.0)

        assert portfolio.get_total_value() == Decimal("2000")

    def test_get_total_cost_basis(self):
        """Test calculating total cost basis."""
        portfolio = Portfolio(name="Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, purchase_price=80.0)
        portfolio.add_asset("GOOGL", "Google", 5, purchase_price=150.0)

        assert portfolio.get_total_cost_basis() == Decimal("1550")

    def test_get_total_gain_loss(self):
        """Test calculating total gain/loss."""
        portfolio = Portfolio(name="Test Portfolio")
        portfolio.add_asset("AAPL", "Apple", 10, current_price=100.0, purchase_price=80.0)

        assert portfolio.get_total_gain_loss() == Decimal("200")
