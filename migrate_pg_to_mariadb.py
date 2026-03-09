"""
PostgreSQL → MariaDB Migration Script
======================================
Migrates all data from the Neon PostgreSQL database to MariaDB.

Safety features:
  - Reads PG creds from PGHOST/PGUSER/PGPASSWORD/PGDATABASE env vars (unchanged)
  - Reads MariaDB creds from MARIADB_* env vars
  - Creates all tables in MariaDB using SQLAlchemy ORM (same models the app uses)
  - Transfers data table-by-table, respecting FK order
  - After transfer, resets AUTO_INCREMENT sequences so new inserts don't collide
  - Dry-run mode: pass --dry-run to simulate without writing to MariaDB
  - Idempotent: re-running skips tables that already have data (unless --force)

Usage:
    uv run python migrate_pg_to_mariadb.py              # full migration
    uv run python migrate_pg_to_mariadb.py --dry-run    # simulate only
    uv run python migrate_pg_to_mariadb.py --force      # re-copy even if rows exist
    uv run python migrate_pg_to_mariadb.py --tables users,portfolios  # specific tables only
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

load_dotenv(override=False)

# ── Connection helpers ────────────────────────────────────────────────────────

def _pg_url() -> str:
    user = os.environ["PGUSER"]
    password = os.environ["PGPASSWORD"]
    host = os.environ["PGHOST"]
    port = os.environ.get("PGPORT", "5432")
    db = os.environ["PGDATABASE"]
    ssl = os.environ.get("PGSSLMODE", "require")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}?sslmode={ssl}"


def _mariadb_url() -> str:
    user = quote_plus(os.environ["MARIADB_USER"])
    password = quote_plus(os.environ["MARIADB_PASSWORD"])
    host = os.environ["MARIADB_HOST"]
    port = os.environ.get("MARIADB_PORT", "3306")
    db = os.environ["MARIADB_DATABASE"]
    # pymysql driver; charset=utf8mb4 for full unicode support
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


# ── Table migration order (respects FK dependencies) ─────────────────────────
# Parent tables must come before child tables.
TABLE_ORDER = [
    "users",
    "password_reset_tokens",
    "portfolios",
    "assets",
    "transactions",
    "broker_templates",
    "broker_configs",
    "price_history",
    "export_logs",
    "options_analysis_logs",
]


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a plain dict, normalising types for MariaDB."""
    d = dict(row._mapping)
    result = {}
    for k, v in d.items():
        if isinstance(v, datetime):
            # Strip timezone info — MariaDB DATETIME columns are naive
            if v.tzinfo is not None:
                v = v.replace(tzinfo=None)
        elif isinstance(v, Decimal):
            v = float(v)  # MariaDB DECIMAL columns accept float in pymysql
        result[k] = v
    return result


def migrate_table(
    table: str,
    pg_conn,
    maria_conn,
    dry_run: bool,
    force: bool,
    batch_size: int = 500,
) -> int:
    """Copy all rows from PG table to MariaDB table. Returns row count copied."""

    # Count source rows first (always needed for progress/dry-run report)
    total = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()

    if dry_run:
        if total == 0:
            print(f"  ○  {table}: empty in source — skipping")
        else:
            print(f"  →  {table}: {total} rows would be copied [DRY RUN]")
        return total

    # Check how many rows exist in target
    existing = maria_conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
    if existing > 0 and not force:
        print(f"  ⏭  {table}: {existing} rows already exist — skipping (use --force to re-copy)")
        return 0

    if total == 0:
        print(f"  ○  {table}: empty in source — skipping")
        return 0

    # Read column names from MariaDB (authoritative schema after CREATE)
    cols_result = maria_conn.execute(text(
        f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' "
        f"ORDER BY ORDINAL_POSITION"
    ))
    columns = [r[0] for r in cols_result]
    if not columns:
        print(f"  ✗  {table}: table not found in MariaDB — skipping")
        return 0

    col_list = ", ".join(f'"{c}"' for c in columns)
    maria_col_list = ", ".join(f"`{c}`" for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)

    print(f"  → {table}: copying {total} rows", end="", flush=True)

    copied = 0
    offset = 0

    # Disable FK checks during bulk load to speed things up
    maria_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    maria_conn.execute(text(f"DELETE FROM `{table}`"))  # clear if force

    while True:
        rows = pg_conn.execute(
            text(f'SELECT {col_list} FROM "{table}" ORDER BY id LIMIT :lim OFFSET :off'),
            {"lim": batch_size, "off": offset},
        ).fetchall()
        if not rows:
            break

        batch = [_row_to_dict(r) for r in rows]
        maria_conn.execute(
            text(f"INSERT INTO `{table}` ({maria_col_list}) VALUES ({placeholders})"),
            batch,
        )
        copied += len(rows)
        offset += batch_size
        print(f"\r  → {table}: {copied}/{total}", end="", flush=True)

    # Re-enable FK checks
    maria_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    maria_conn.commit()

    # Reset AUTO_INCREMENT to max(id) + 1
    max_id_row = maria_conn.execute(text(f"SELECT MAX(id) FROM `{table}`")).scalar()
    if max_id_row:
        maria_conn.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = {max_id_row + 1}"))
        maria_conn.commit()

    print(f"\r  ✓  {table}: {copied} rows copied")
    return copied


def main():
    parser = argparse.ArgumentParser(description="Migrate PostgreSQL → MariaDB")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    parser.add_argument("--force", action="store_true", help="Re-copy tables that already have data")
    parser.add_argument("--tables", help="Comma-separated list of tables to migrate (default: all)")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per INSERT batch (default 500)")
    args = parser.parse_args()

    tables_to_migrate = (
        [t.strip() for t in args.tables.split(",")]
        if args.tables
        else TABLE_ORDER
    )

    print("=" * 60)
    print("  PostgreSQL → MariaDB Migration")
    print("=" * 60)
    if args.dry_run:
        print("  ⚠  DRY RUN — nothing will be written to MariaDB")
    print()

    # ── Step 1: connect to both databases ─────────────────────────────────────
    try:
        pg_url = _pg_url()
        print(f"PG source   : {os.environ['PGHOST']}/{os.environ['PGDATABASE']}")
    except KeyError as e:
        print(f"✗ Missing PostgreSQL env var: {e}")
        sys.exit(1)

    try:
        maria_url = _mariadb_url()
        print(f"MariaDB dest: {os.environ['MARIADB_HOST']}:{os.environ.get('MARIADB_PORT','3306')}/{os.environ['MARIADB_DATABASE']}")
    except KeyError as e:
        print(f"✗ Missing MariaDB env var: {e}")
        sys.exit(1)

    print()

    pg_engine = create_engine(pg_url, pool_pre_ping=True)
    maria_engine = create_engine(
        maria_url,
        pool_pre_ping=True,
        # MariaDB with pymysql needs this for DECIMAL/DATETIME handling
        connect_args={"local_infile": True},
    )

    # ── Step 2: create all tables in MariaDB via ORM ──────────────────────────
    # Import models AFTER dotenv is loaded so SQLAlchemy Base sees the right URL
    os.environ["DATABASE_URL"] = maria_url  # point ORM at MariaDB for create_all
    # Import all models so they register against Base
    import portfolio_tracker.models  # noqa: F401
    from portfolio_tracker.database import Base

    print("Creating tables in MariaDB (if not exist)...")
    if not args.dry_run:
        # Use MariaDB engine directly — not the app's engine (which still points to PG env vars)
        Base.metadata.create_all(bind=maria_engine)
        print("  ✓ Schema ready\n")
    else:
        print("  [DRY RUN]\n")

    # ── Step 3: migrate data ──────────────────────────────────────────────────
    print("Migrating data:")
    total_copied = 0

    with pg_engine.connect() as pg_conn, maria_engine.connect() as maria_conn:
        for table in tables_to_migrate:
            if table not in TABLE_ORDER:
                print(f"  ✗  Unknown table '{table}' — skipping")
                continue
            try:
                n = migrate_table(
                    table,
                    pg_conn,
                    maria_conn,
                    dry_run=args.dry_run,
                    force=args.force,
                    batch_size=args.batch_size,
                )
                total_copied += n
            except Exception as exc:
                print(f"\n  ✗  {table}: ERROR — {exc}")
                import traceback; traceback.print_exc()
                print("      Continuing with next table...")

    # ── Step 4: summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    if args.dry_run:
        print(f"  DRY RUN complete — {total_copied} rows would be copied")
    else:
        print(f"  Migration complete — {total_copied} rows copied")
    print("=" * 60)

    if not args.dry_run and total_copied > 0:
        print()
        print("Next steps:")
        print("  1. Update .env — replace PG* vars with:")
        print("       DATABASE_URL=mysql+pymysql://MARIADB_USER:MARIADB_PASSWORD@MARIADB_HOST:3306/MARIADB_DATABASE?charset=utf8mb4")
        print("  2. Add pymysql to pyproject.toml dependencies")
        print("  3. Restart the FastAPI server")
        print("  4. Verify the app works, then decommission Neon")


if __name__ == "__main__":
    main()
