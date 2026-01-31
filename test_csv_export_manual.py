"""Manual test script for CSV export functionality.

Run this script to manually verify the CSV export endpoints work correctly.
This script creates sample data and downloads the CSV files.

Run: uv run python test_csv_export_manual.py
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from portfolio_tracker.auth import create_access_token
from portfolio_tracker.crud import (create_asset, create_portfolio,
                                    create_transaction, create_user)
from portfolio_tracker.database import Base

# Setup test database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_export.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def setup_test_data():
    """Create test user and sample portfolio data."""
    db = SessionLocal()
    
    try:
        # Create test user
        user = create_user(
            db,
            email="testuser@example.com",
            password="test123",
            first_name="Test",
            last_name="User"
        )
        print(f"✓ Created user: {user.email}")
        
        # Create portfolio
        portfolio = create_portfolio(
            db,
            user_id=user.id,
            name="Demo Portfolio",
            description="Sample portfolio for CSV export testing"
        )
        print(f"✓ Created portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        # Create assets
        asset1 = create_asset(
            db,
            portfolio_id=portfolio.id,
            symbol="RELIANCE",
            name="Reliance Industries Ltd",
            quantity=Decimal("15.0"),
            purchase_price=Decimal("2450.00"),
            current_price=Decimal("2680.00")
        )
        print(f"✓ Added asset: {asset1.symbol}")
        
        asset2 = create_asset(
            db,
            portfolio_id=portfolio.id,
            symbol="TCS",
            name="Tata Consultancy Services",
            quantity=Decimal("8.0"),
            purchase_price=Decimal("3350.00"),
            current_price=Decimal("3580.00")
        )
        print(f"✓ Added asset: {asset2.symbol}")
        
        asset3 = create_asset(
            db,
            portfolio_id=portfolio.id,
            symbol="INFY",
            name="Infosys Ltd",
            quantity=Decimal("20.0"),
            purchase_price=Decimal("1420.00"),
            current_price=Decimal("1510.00")
        )
        print(f"✓ Added asset: {asset3.symbol}")
        
        # Create transactions
        tx1 = create_transaction(
            db,
            portfolio_id=portfolio.id,
            asset_id=asset1.id,
            transaction_type="buy",
            quantity=Decimal("15.0"),
            price=Decimal("2450.00"),
            transaction_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            notes="Initial purchase - Reliance"
        )
        print(f"✓ Added transaction: BUY {asset1.symbol}")
        
        tx2 = create_transaction(
            db,
            portfolio_id=portfolio.id,
            asset_id=asset2.id,
            transaction_type="buy",
            quantity=Decimal("8.0"),
            price=Decimal("3350.00"),
            transaction_date=datetime(2024, 1, 25, tzinfo=timezone.utc),
            notes="Initial purchase - TCS"
        )
        print(f"✓ Added transaction: BUY {asset2.symbol}")
        
        tx3 = create_transaction(
            db,
            portfolio_id=portfolio.id,
            asset_id=asset3.id,
            transaction_type="buy",
            quantity=Decimal("20.0"),
            price=Decimal("1420.00"),
            transaction_date=datetime(2024, 2, 5, tzinfo=timezone.utc),
            notes="Initial purchase - Infosys"
        )
        print(f"✓ Added transaction: BUY {asset3.symbol}")
        
        # Generate access token
        token = create_access_token(
            data={"sub": user.email},
            expires_delta=None
        )
        
        print("\n" + "="*60)
        print("TEST DATA CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"\nUser Email: {user.email}")
        print(f"User ID: {user.id}")
        print(f"Portfolio ID: {portfolio.id}")
        print(f"Access Token: {token[:50]}...")
        print("\n" + "="*60)
        print("TEST THE CSV EXPORT:")
        print("="*60)
        print("\n1. Start the server:")
        print("   uv run uvicorn portfolio_tracker.main:app --reload")
        print("\n2. Test Portfolio Export:")
        print(f"   curl -H 'Authorization: Bearer {token}' \\")
        print(f"        http://localhost:8000/api/portfolio/{portfolio.id}/export \\")
        print(f"        -o portfolio_export.csv")
        print("\n3. Test Transactions Export:")
        print(f"   curl -H 'Authorization: Bearer {token}' \\")
        print(f"        http://localhost:8000/api/transactions/export \\")
        print(f"        -o transactions_export.csv")
        print("\n4. Or use the frontend:")
        print("   - Navigate to Holdings page")
        print("   - Select 'Demo Portfolio'")
        print("   - Click 'Export CSV' button")
        print("   - Navigate to Transactions page")
        print("   - Click 'Export CSV' button")
        print("\n" + "="*60)
        
        return user, portfolio, token
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Setting up test data for CSV export...\n")
    setup_test_data()
    print("\n✓ Done! You can now test the CSV export functionality.")
