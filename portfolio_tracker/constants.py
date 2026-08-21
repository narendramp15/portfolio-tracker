"""Shared constants with no heavy imports.

Lives apart from the service modules so both the analytics layer and the
price-history layer can agree on a value without importing each other (and
without pulling yfinance in as a side effect).
"""

# Yahoo Finance ticker for the Nifty 50 index, used as the portfolio benchmark.
# Stored in price_history alongside ordinary holdings so the comparison line
# is served from the database rather than fetched per request.
BENCHMARK_SYMBOL = "^NSEI"

BENCHMARK_LABEL = "Nifty 50"
