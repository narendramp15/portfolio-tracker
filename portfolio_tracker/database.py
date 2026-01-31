"""Database configuration and session management."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from portfolio_tracker.config import settings

logger = logging.getLogger(__name__)

# Get database URL from centralized config
DATABASE_URL = settings.DATABASE_URL

# Log database type (only in non-testing mode to keep test output clean)
if not settings.TESTING:
    if settings.is_postgres():
        import os
        pg_host = os.getenv("PGHOST", "unknown")
        pg_db = os.getenv("PGDATABASE", "unknown")
        logger.info(f"Using PostgreSQL database: {pg_db} at {pg_host}")
    elif settings.is_sqlite():
        logger.warning("Using SQLite (local file) - data will be lost on Render/Railway restarts!")

# Create engine with appropriate settings
if settings.is_sqlite():
    # SQLite settings
    logger.info("Creating SQLite engine")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DB_ECHO,
    )
else:
    # PostgreSQL settings with connection pool configuration for Neon
    # Neon has aggressive connection timeouts, so we need to:
    # 1. Pre-ping connections to check if they're still alive
    # 2. Recycle connections frequently
    # 3. Handle dropped connections gracefully
    logger.info(f"Creating PostgreSQL engine with connection pool (size=5, max_overflow=10, recycle=300s)")
    engine = create_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=QueuePool,
        pool_size=5,  # Number of connections to keep in the pool
        max_overflow=10,  # Additional connections allowed beyond pool_size
        pool_timeout=30,  # Seconds to wait for a connection from pool
        pool_recycle=300,  # Recycle connections after 5 minutes (Neon idle timeout)
        pool_pre_ping=True,  # Check connection validity before using (handles SSL drops)
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
