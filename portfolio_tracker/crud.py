"""Backwards-compatibility facade over ``portfolio_tracker.repositories``.

The flat CRUD module was split into one repository per aggregate. Existing
callers (routers, tests, migration scripts) importing ``portfolio_tracker.crud``
keep working; new code should import from ``portfolio_tracker.repositories``
directly. Remove this module once no callers remain.
"""

from portfolio_tracker.repositories.assets import (
                                                   create_asset,
                                                   delete_asset,
                                                   get_asset_by_id,
                                                   get_asset_by_symbol,
                                                   get_portfolio_assets,
                                                   update_asset,
)
from portfolio_tracker.repositories.broker_configs import (
                                                   create_broker_config,
                                                   delete_broker_config,
                                                   get_broker_config,
                                                   get_broker_config_by_broker_name,
                                                   get_broker_configs_by_user,
                                                   update_broker_config,
)
from portfolio_tracker.repositories.portfolios import (
                                                   create_portfolio,
                                                   delete_portfolio,
                                                   get_portfolio_by_id,
                                                   get_portfolio_stats,
                                                   get_portfolios,
                                                   update_portfolio,
)
from portfolio_tracker.repositories.transactions import (
                                                   create_transaction,
                                                   delete_transaction,
                                                   find_duplicate_transaction,
                                                   get_portfolio_transactions,
                                                   get_transaction_by_id,
)
from portfolio_tracker.repositories.users import create_user, get_user_by_email, get_user_by_id

__all__ = [
    # users
    "get_user_by_id", "get_user_by_email", "create_user",
    # portfolios
    "get_portfolio_by_id", "get_portfolios", "create_portfolio",
    "update_portfolio", "delete_portfolio", "get_portfolio_stats",
    # assets
    "get_asset_by_id", "get_portfolio_assets", "get_asset_by_symbol",
    "create_asset", "update_asset", "delete_asset",
    # transactions
    "get_transaction_by_id", "get_portfolio_transactions",
    "create_transaction", "delete_transaction", "find_duplicate_transaction",
    # broker configs
    "get_broker_config", "get_broker_configs_by_user",
    "get_broker_config_by_broker_name", "create_broker_config",
    "update_broker_config", "delete_broker_config",
]
