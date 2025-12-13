"""
Core functionality for portfolio tracking.

This module provides the main PortfolioTracker class and related functions.
"""

import logging
from decimal import Decimal

from .models import Portfolio

logger = logging.getLogger(__name__)


class PortfolioTracker:
    """Main class for tracking investment portfolios."""

    def __init__(self) -> None:
        """Initialize the portfolio tracker."""
        self.portfolios: list[Portfolio] = []
        logger.info("PortfolioTracker initialized")

    def create_portfolio(self, name: str) -> Portfolio:
        """
        Create a new portfolio.

        Args:
            name: The name of the portfolio

        Returns:
            The newly created Portfolio object
        """
        portfolio = Portfolio(name=name)
        self.portfolios.append(portfolio)
        logger.info(f"Created portfolio: {name}")
        return portfolio

    def get_portfolio(self, name: str) -> Portfolio | None:
        """
        Get a portfolio by name.

        Args:
            name: The name of the portfolio

        Returns:
            The Portfolio object or None if not found
        """
        for portfolio in self.portfolios:
            if portfolio.name == name:
                return portfolio
        return None

    def delete_portfolio(self, name: str) -> bool:
        """
        Delete a portfolio by name.

        Args:
            name: The name of the portfolio

        Returns:
            True if deleted, False if not found
        """
        for i, portfolio in enumerate(self.portfolios):
            if portfolio.name == name:
                del self.portfolios[i]
                logger.info(f"Deleted portfolio: {name}")
                return True
        return False

    def get_all_portfolios(self) -> list[Portfolio]:
        """
        Get all portfolios.

        Returns:
            List of all Portfolio objects
        """
        return self.portfolios

    def get_total_value(self) -> Decimal:
        """
        Calculate the total value across all portfolios.

        Returns:
            Total value of all portfolios
        """
        return sum((portfolio.get_total_value() for portfolio in self.portfolios), Decimal("0"))
