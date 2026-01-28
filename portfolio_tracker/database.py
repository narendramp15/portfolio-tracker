"""Database configuration and session management."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Build DATABASE_URL from individual PostgreSQL env vars if available
# Otherwise fall back to DATABASE_URL env var or SQLite
def get_database_url() -> str:
    """Construct database URL from environment variables."""
    # Try individual PostgreSQL variables first (Neon/Supabase style)
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_host = os.getenv("PGHOST")
    pg_port = os.getenv("PGPORT", "5432")
    pg_database = os.getenv("PGDATABASE")
    
    if all([pg_user, pg_password, pg_host, pg_database]):
        # Construct PostgreSQL URL from individual components
        database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        print(f"✓ Using PostgreSQL database: {pg_database} at {pg_host}")
        return database_url
    
    # Fall back to DATABASE_URL or SQLite
    database_url = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    if "sqlite" in database_url:
        print("⚠️  Using SQLite (local file) - data will be lost on Render/Railway restarts!")
    else:
        print(f"✓ Using database from DATABASE_URL")
    return database_url

DATABASE_URL = get_database_url()

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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
