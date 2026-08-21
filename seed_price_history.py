"""Seed and refresh daily closes for held symbols and the benchmark index.

The dashboard's growth chart, TWR, drawdown and volatility figures all read
`price_history`. If that table is empty they correctly render an empty state
rather than a line - so this needs to run once to seed, then daily to stay
current.

The equivalent HTTP endpoint (POST /api/market/history/backfill) needs a
bearer token and only covers the calling user's holdings. This covers every
holding in the database and needs no token, which is what a cron job wants.

Usage:
    uv run python seed_price_history.py                  # all holdings + benchmark
    uv run python seed_price_history.py --days 400       # override window
    uv run python seed_price_history.py --symbol RELIANCE.NS
    uv run python seed_price_history.py --benchmark-only
    uv run python seed_price_history.py --stats           # report, change nothing

Suggested cron (after market close, IST):
    30 16 * * 1-5  cd /path/to/app && uv run python seed_price_history.py

Fetches come from yfinance, which is unofficial and rate-limits aggressively.
Symbols are fetched one at a time with a short pause; a failure is reported
per symbol rather than aborting the run.
"""

from __future__ import annotations

import argparse
import sys
import time

from portfolio_tracker.constants import BENCHMARK_SYMBOL

# Courtesy delay between symbol fetches. yfinance has no official rate limit
# to respect, so this is deliberately conservative.
PAUSE_SECONDS = 0.4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=None, help="Days of history to fetch")
    parser.add_argument("--symbol", help="Seed one symbol only")
    parser.add_argument(
        "--benchmark-only",
        action="store_true",
        help=f"Seed only {BENCHMARK_SYMBOL}, the comparison index",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print storage stats and exit"
    )
    args = parser.parse_args()

    from portfolio_tracker.database import SessionLocal, engine
    from portfolio_tracker.models import AssetModel
    from portfolio_tracker.services.price_history import get_price_history_service

    db = SessionLocal()
    try:
        service = get_price_history_service(db)
        url = engine.url
        print(f"Database: {url.database} on {url.host or 'local'} ({engine.dialect.name})")
        print(f"Retention: {service.retention_days} days\n")

        if args.stats:
            for key, value in service.get_storage_stats().items():
                print(f"  {key}: {value}")
            return 0

        if args.symbol:
            symbols = [args.symbol]
        elif args.benchmark_only:
            symbols = [BENCHMARK_SYMBOL]
        else:
            # Everything held now OR ever traded. A position sold six months
            # ago still needs prices for the earlier part of the chart window.
            from portfolio_tracker.models import TransactionModel

            held = {
                row[0] for row in db.query(AssetModel.symbol).distinct().all() if row[0]
            }
            traded = {
                row[0]
                for row in db.query(AssetModel.symbol)
                .join(TransactionModel, TransactionModel.asset_id == AssetModel.id)
                .distinct()
                .all()
                if row[0]
            }
            symbols = sorted(held | traded)
            if BENCHMARK_SYMBOL not in symbols:
                symbols.append(BENCHMARK_SYMBOL)

        if not symbols:
            print("No symbols to seed - no assets in the database.")
            return 0

        print(f"Seeding {len(symbols)} symbol(s)...\n")
        total = 0
        failed = []
        for i, symbol in enumerate(symbols, 1):
            label = f"{symbol} (benchmark)" if symbol == BENCHMARK_SYMBOL else symbol
            try:
                count = service.backfill_symbol(symbol, days=args.days)
            except Exception as exc:  # a bad ticker must not kill the run
                count = 0
                print(f"  [{i}/{len(symbols)}] {label}: error - {type(exc).__name__}")
            if count:
                total += count
                print(f"  [{i}/{len(symbols)}] {label}: {count} rows")
            else:
                failed.append(symbol)
                print(f"  [{i}/{len(symbols)}] {label}: no data")
            if i < len(symbols):
                time.sleep(PAUSE_SECONDS)

        print(f"\n{total} rows written across {len(symbols) - len(failed)} symbol(s).")

        if failed:
            print(f"\nNo data for {len(failed)}: {', '.join(failed)}")
            print(
                "These are missing from every chart that reads price_history. "
                "Usually a wrong exchange suffix (RELIANCE.NS vs RELIANCE.BO) "
                "or a delisted ticker."
            )

        if BENCHMARK_SYMBOL in failed:
            print(
                f"\nWarning: {BENCHMARK_SYMBOL} failed, so the benchmark "
                "comparison line will not render."
            )
            return 1

        stats = service.get_storage_stats()
        print(
            f"\nStored: {stats['total_records']} rows across "
            f"{stats['unique_symbols']} symbols "
            f"(~{stats['estimated_storage_kb']} KB)"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
