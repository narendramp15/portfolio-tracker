"""Apply a numbered SQL migration through the app's own database connection.

The repo keeps migrations as plain numbered .sql files under migrations/.
Running them with a vendor client (`psql`, `mysql`) means installing that
client and re-typing credentials that already live in DATABASE_URL, and the
Postgres and MariaDB clients take different flags. This runs a file through
SQLAlchemy instead, so the same command works against either.

Usage:
    uv run python run_sql_migration.py 011_add_transaction_charges.sql
    uv run python run_sql_migration.py 011_add_transaction_charges.sql --dry-run

Statements run inside one transaction where the backend supports it. Note
that MySQL/MariaDB commit DDL implicitly, so a failure partway through an
ALTER-heavy migration there leaves earlier statements applied - which is why
the migrations in this repo are written to be safe to re-run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def strip_comments(sql: str) -> str:
    """Remove -- line comments and /* */ blocks before splitting statements."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    lines = []
    for line in sql.splitlines():
        # Only strip a -- that starts a comment, not one inside a quoted string.
        in_single = in_double = False
        cut = None
        for i, char in enumerate(line):
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif (
                char == "-"
                and not in_single
                and not in_double
                and line[i : i + 2] == "--"
            ):
                cut = i
                break
        lines.append(line[:cut] if cut is not None else line)
    return "\n".join(lines)


def split_statements(sql: str) -> list[str]:
    """Split a migration into individual statements on semicolons."""
    return [stmt.strip() for stmt in strip_comments(sql).split(";") if stmt.strip()]


def resolve(name: str) -> Path:
    """Find a migration by filename or by its numeric prefix."""
    candidate = MIGRATIONS_DIR / name
    if candidate.is_file():
        return candidate

    # Allow `011` as shorthand for `011_add_transaction_charges.sql`.
    matches = sorted(MIGRATIONS_DIR.glob(f"{name}*.sql"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise SystemExit(f"'{name}' is ambiguous: {names}")

    available = "\n  ".join(sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql")))
    raise SystemExit(f"No migration matching '{name}'. Available:\n  {available}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("migration", help="Filename under migrations/, or its number")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the statements and the target database, then exit without running",
    )
    args = parser.parse_args()

    path = resolve(args.migration)
    statements = split_statements(path.read_text(encoding="utf-8"))
    if not statements:
        print(f"{path.name} contains no statements.")
        return 0

    # Imported here so --help works without a reachable database.
    from portfolio_tracker.database import engine

    url = engine.url
    target = f"{url.database} on {url.host or 'local'} ({engine.dialect.name})"

    print(f"Migration: {path.name}")
    print(f"Target:    {target}")
    print(f"Statements: {len(statements)}\n")
    for i, stmt in enumerate(statements, 1):
        collapsed = " ".join(stmt.split())
        print(f"  {i}. {collapsed[:150]}{'...' if len(collapsed) > 150 else ''}")

    if args.dry_run:
        print("\nDry run - nothing was executed.")
        return 0

    print()
    try:
        with engine.begin() as connection:
            for i, stmt in enumerate(statements, 1):
                connection.execute(text(stmt))
                print(f"  [{i}/{len(statements)}] ok")
    except SQLAlchemyError as exc:
        # Keep the message tight: the driver's full repr can echo the DSN.
        print(f"\nFailed on statement {i}: {type(exc).__name__}", file=sys.stderr)
        print(f"  {str(exc.orig if hasattr(exc, 'orig') else exc)[:300]}", file=sys.stderr)
        print(
            "\nThe migrations here are written to be safe to re-run, so fix the "
            "cause and run it again.",
            file=sys.stderr,
        )
        return 1

    print(f"\n{path.name} applied to {target}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
