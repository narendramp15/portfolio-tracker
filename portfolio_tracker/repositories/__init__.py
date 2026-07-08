"""Persistence layer: one module per aggregate root.

Every function takes an explicit ``Session`` so callers (services, routers)
own the unit of work. No business rules belong here — only queries and
straightforward writes.
"""

from portfolio_tracker.repositories import assets, broker_configs, portfolios, transactions, users

__all__ = ["assets", "broker_configs", "portfolios", "transactions", "users"]
