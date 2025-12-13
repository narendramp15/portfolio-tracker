"""
Portfolio Tracker - A modern Python portfolio tracking application.

This package provides tools for managing and analyzing investment portfolios.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core import PortfolioTracker
from .models import Portfolio, Asset

__all__ = [
    "PortfolioTracker",
    "Portfolio",
    "Asset",
]
