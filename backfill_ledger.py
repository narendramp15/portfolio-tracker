"""Populate the event ledger from the existing transactions and holdings.

The ledger is append-only and ingestion is idempotent on (source, source_ref),
so this is safe to run repeatedly - re-running after ISINs have been resolved
picks up the improvement without duplicating anything.

Usage:
    uv run python backfill_ledger.py --dry-run          # report, write nothing
    uv run python backfill_ledger.py --user 3           # one user
    uv run python backfill_ledger.py                    # every user
    uv run python backfill_ledger.py --verify           # fold and compare

``--verify`` is the one to care about: it folds the resulting ledger and checks
the quantities against the assets table. A mismatch means the ledger disagrees
with what the user sees in the app, which has to be resolved before anything
starts reading from it.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal

from sqlalchemy import select


def _print_report(user_id: int, report) -> None:
    print(f"  user {user_id}:")
    print(f"    from transactions : {report.transaction_events}")
    print(f"    opening balances  : {report.opening_events}")
    print(f"    written           : {report.added}")
    print(f"    already present   : {report.skipped_duplicate}")

    if report.unresolved_symbols:
        shown = sorted(report.unresolved_symbols)
        print(f"    no ISIN ({len(shown)}): {', '.join(shown[:8])}"
              f"{' ...' if len(shown) > 8 else ''}")
    for note in report.notes[:5]:
        print(f"    note: {note}")


def _verify(db, user_id: int) -> bool:
    """Check the folded ledger against the assets table.

    Compares on the canonical instrument key rather than the raw symbol, since
    folding deliberately merges ticker variants of one security.
    """
    from portfolio_tracker.ledger.backfill import _key_for
    from portfolio_tracker.ledger.repository import fold_user
    from portfolio_tracker.models import AssetModel, PortfolioModel

    book = fold_user(db, user_id)

    portfolio_ids = list(
        db.execute(
            select(PortfolioModel.id).where(PortfolioModel.user_id == user_id)
        ).scalars()
    )
    if not portfolio_ids:
        return True

    expected: dict[str, Decimal] = {}
    labels: dict[str, str] = {}
    for asset in db.execute(
        select(AssetModel).where(AssetModel.portfolio_id.in_(portfolio_ids))
    ).scalars():
        key = _key_for(asset)
        if not key:
            continue
        expected[key] = expected.get(key, Decimal("0")) + Decimal(str(asset.quantity or 0))
        labels.setdefault(key, asset.symbol)

    mismatches = []
    for key, quantity in sorted(expected.items()):
        folded = book.quantity(key)
        if folded != quantity:
            mismatches.append((labels.get(key, key), quantity, folded))

    if mismatches:
        print(f"    MISMATCH on {len(mismatches)} instrument(s):")
        for symbol, want, got in mismatches[:10]:
            print(f"      {symbol:<16} assets={want}  ledger={got}")
        return False

    print(f"    verified: {len(expected)} instruments agree with the assets table")
    if book.unmatched:
        print(f"    {len(book.unmatched)} event(s) the fold could not explain:")
        for event, reason in book.unmatched[:5]:
            print(f"      {event.symbol or event.isin}: {reason}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", type=int, help="Backfill one user id only")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--verify", action="store_true",
                        help="Fold the ledger and compare against the assets table")
    args = parser.parse_args()

    from portfolio_tracker.database import SessionLocal, engine
    from portfolio_tracker.ledger.backfill import backfill_user, build_events
    from portfolio_tracker.models import PortfolioModel

    db = SessionLocal()
    try:
        url = engine.url
        print(f"Database: {url.database} on {url.host or 'local'} ({engine.dialect.name})")

        if args.user:
            user_ids = [args.user]
        else:
            user_ids = sorted(
                set(db.execute(select(PortfolioModel.user_id).distinct()).scalars())
            )

        if not user_ids:
            print("No users with portfolios.")
            return 0

        mode = "DRY RUN - nothing will be written" if args.dry_run else "writing"
        print(f"Users: {len(user_ids)}   ({mode})\n")

        total_written = 0
        all_verified = True

        for user_id in user_ids:
            if args.dry_run:
                events, report = build_events(db, user_id)
                report.added = 0
                _print_report(user_id, report)
                print(f"    would write       : {len(events)}")
            else:
                report = backfill_user(db, user_id)
                _print_report(user_id, report)
                total_written += report.added
                if args.verify:
                    all_verified &= _verify(db, user_id)
            print()

        if not args.dry_run:
            print(f"{total_written} event(s) written.")
            if args.verify and not all_verified:
                print(
                    "\nThe ledger disagrees with the assets table for at least one "
                    "instrument. Resolve that before anything reads from the ledger."
                )
                return 1
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
