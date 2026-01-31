"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from portfolio_tracker.config import settings

# Get database URL from centralized config
DATABASE_URL = settings.DATABASE_URL

# Log database type (only in non-testing mode to keep test output clean)
if not settings.TESTING:
    if settings.is_postgres():
        import os
        pg_host = os.getenv("PGHOST", "unknown")
        pg_db = os.getenv("PGDATABASE", "unknown")
        print(f"✓ Using PostgreSQL database: {pg_db} at {pg_host}")
    elif settings.is_sqlite():
        print("⚠️  Using SQLite (local file) - data will be lost on Render/Railway restarts!")

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.is_sqlite() else {},
    echo=settings.DB_ECHO,
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
