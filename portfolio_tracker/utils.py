"""Utility functions for portfolio tracking."""

import logging
from decimal import Decimal


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def format_currency(value: Decimal | float | int, currency: str = "USD") -> str:
    """
    Format a value as currency.

    Args:
        value: The numeric value to format
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    amount = Decimal(str(value))
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def format_percent(value: Decimal | float | int, decimal_places: int = 2) -> str:
    """
    Format a value as a percentage.

    Args:
        value: The numeric value to format
        decimal_places: Number of decimal places (default: 2)

    Returns:
        Formatted percentage string
    """
    amount = Decimal(str(value))
    return f"{amount:.{decimal_places}f}%"
