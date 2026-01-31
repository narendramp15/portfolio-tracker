"""Pytest configuration and fixtures for integration tests."""

# =============================================================================
# CRITICAL: Set testing mode BEFORE importing anything from portfolio_tracker
# The config module checks TESTING env var at import time
# =============================================================================
import os

os.environ['TESTING'] = '1'

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import sessionmaker

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False

# Now safe to import portfolio_tracker - config will see TESTING=1
from portfolio_tracker import database, models
from portfolio_tracker.auth import create_access_token, hash_password
from portfolio_tracker.config import settings
from portfolio_tracker.crud import create_asset, create_portfolio

# Verify we're in testing mode
assert settings.TESTING, "TESTING mode not enabled! Set os.environ['TESTING'] = '1' before imports"
assert settings.is_sqlite(), f"Expected SQLite in tests, got: {settings.DATABASE_URL}"

# Use the engine created by database.py (configured via settings)
test_engine = database.engine
TestingSessionLocal = database.SessionLocal
Base = database.Base


def override_get_db():
    """Override get_db dependency to use test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def app():
    """Create FastAPI app with test database."""
    # Import app first
    from portfolio_tracker.main import app as _app

    # Override database dependency to ensure it uses test engine
    _app.dependency_overrides[database.get_db] = override_get_db
    
    yield _app
    
    # Cleanup
    _app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app):
    """Create TestClient for API testing - function scoped for test isolation."""
    if not TESTCLIENT_AVAILABLE:
        pytest.skip("httpx not installed")
    
    # Create tables fresh for each test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup after test
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(client):
    """Create a fresh database session for each test.
    
    Depends on client to ensure tables are created first.
    """
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = models.UserModel(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("test123"),
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Store user data before session might close
    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name
    }
    
    return user_data


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test user."""
    token = create_access_token(
        data={"sub": test_user['email']},
        expires_delta=None
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_portfolio(db_session, test_user):
    """Create a test portfolio with assets and transactions."""
    # Create portfolio
    portfolio = create_portfolio(
        db_session,
        user_id=test_user['id'],
        name="Test Portfolio",
        description="Integration test portfolio"
    )
    
    # Create assets
    asset1 = create_asset(
        db_session,
        portfolio_id=portfolio.id,
        symbol="RELIANCE",
        name="Reliance Industries",
        quantity=Decimal("10.0"),
        purchase_price=Decimal("2500.00"),
        current_price=Decimal("2700.00")
    )
    
    asset2 = create_asset(
        db_session,
        portfolio_id=portfolio.id,
        symbol="TCS",
        name="Tata Consultancy Services",
        quantity=Decimal("5.0"),
        purchase_price=Decimal("3400.00"),
        current_price=Decimal("3600.00")
    )
    
    # Create transactions
    transaction1 = models.TransactionModel(
        portfolio_id=portfolio.id,
        asset_id=asset1.id,
        type="buy",
        quantity=Decimal("10.0"),
        price=Decimal("2500.00"),
        transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        notes="Initial purchase"
    )
    db_session.add(transaction1)
    
    transaction2 = models.TransactionModel(
        portfolio_id=portfolio.id,
        asset_id=asset2.id,
        type="buy",
        quantity=Decimal("5.0"),
        price=Decimal("3400.00"),
        transaction_date=datetime(2024, 2, 10, tzinfo=timezone.utc),
        notes="Second purchase"
    )
    db_session.add(transaction2)
    
    db_session.commit()
    
    # Store portfolio data before session might close
    portfolio_data = {
        'id': portfolio.id,
        'name': portfolio.name,
        'user_id': portfolio.user_id
    }
    
    return portfolio_data
