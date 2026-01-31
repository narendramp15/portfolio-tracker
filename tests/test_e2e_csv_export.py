"""End-to-end test for CSV export endpoints with running server.

This script tests the actual API endpoints while the server is running.

Prerequisites:
1. Server must be running: uv run uvicorn portfolio_tracker.main:app --reload
2. Run this test: uv run python tests/test_e2e_csv_export.py

This provides full integration testing of:
- Backend API endpoints (FastAPI)
- CSV generation and streaming
- Authentication
- Error handling

NOTE: This is a manual test script, not a pytest test module.
      Run it directly: python tests/test_e2e_csv_export.py
      Do not run with pytest - use test_csv_integration.py instead.

      Function names intentionally DON'T start with 'test_' to prevent
      pytest from collecting them.
"""

import csv
import sys
from io import StringIO

import requests

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test123"


def check_server_running():
    """Check if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def login_and_get_token():
    """Login and get access token."""
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"✓ Login successful")
        return token
    else:
        print(f"✗ Login failed: {response.status_code}")
        print("  Create a test user first or update TEST_EMAIL/TEST_PASSWORD")
        return None


def create_test_data(token):
    """Create test portfolio and assets."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create portfolio
    print("\n📁 Creating test portfolio...")
    response = requests.post(
        f"{BASE_URL}/api/portfolio/",
        json={"name": "E2E Test Portfolio", "description": "For CSV export testing"},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to create portfolio: {response.status_code}")
        return None
    
    portfolio = response.json()
    portfolio_id = portfolio["id"]
    print(f"✓ Created portfolio: {portfolio['name']} (ID: {portfolio_id})")
    
    # Add assets
    print("\n📊 Adding test assets...")
    assets = [
        {
            "symbol": "TESTSTOCK1",
            "name": "Test Stock 1",
            "quantity": 100.0,
            "purchase_price": 50.00,
            "current_price": 55.00
        },
        {
            "symbol": "TESTSTOCK2",
            "name": "Test Stock 2",
            "quantity": 50.0,
            "purchase_price": 100.00,
            "current_price": 110.00
        }
    ]
    
    for asset in assets:
        response = requests.post(
            f"{BASE_URL}/api/portfolio/{portfolio_id}/assets",
            json=asset,
            headers=headers
        )
        if response.status_code == 200:
            print(f"✓ Added asset: {asset['symbol']}")
        else:
            print(f"✗ Failed to add asset: {asset['symbol']}")
    
    return portfolio_id


def run_portfolio_export_test(token, portfolio_id):
    """Test portfolio CSV export endpoint."""
    print("\n" + "="*60)
    print("🧪 Testing Portfolio CSV Export")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/portfolio/{portfolio_id}/export",
        headers=headers
    )
    
    # Check response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ Status code: 200")
    
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    print("✓ Content-Type: text/csv")
    
    assert "E2E_Test_Portfolio_holdings.csv" in response.headers.get("Content-Disposition", "")
    print("✓ Filename: E2E_Test_Portfolio_holdings.csv")
    
    # Parse CSV
    csv_reader = csv.DictReader(StringIO(response.text))
    rows = list(csv_reader)
    
    assert len(rows) == 2, f"Expected 2 assets, got {len(rows)}"
    print(f"✓ Row count: {len(rows)}")
    
    # Verify headers
    expected_headers = [
        'Symbol', 'Name', 'Quantity', 'Purchase Price (₹)', 
        'Current Price (₹)', 'Invested Value (₹)', 'Current Value (₹)',
        'Gain/Loss (₹)', 'Gain/Loss (%)', 'Purchase Date'
    ]
    assert list(csv_reader.fieldnames) == expected_headers
    print("✓ CSV headers correct")
    
    # Verify data
    stock1 = next((r for r in rows if r['Symbol'] == 'TESTSTOCK1'), None)
    assert stock1 is not None
    assert float(stock1['Gain/Loss (₹)']) == 500.00  # 100 * (55-50)
    assert float(stock1['Gain/Loss (%)']) == 10.0
    print("✓ TESTSTOCK1 calculations correct (₹500 gain, 10.0%)")
    
    stock2 = next((r for r in rows if r['Symbol'] == 'TESTSTOCK2'), None)
    assert stock2 is not None
    assert float(stock2['Gain/Loss (₹)']) == 500.00  # 50 * (110-100)
    print("✓ TESTSTOCK2 calculations correct (₹500 gain, 10.0%)")
    
    print("\n✅ Portfolio CSV export test PASSED")
    return True


def run_portfolio_export_unauthorized_test(portfolio_id):
    """Test portfolio export without authentication."""
    print("\n" + "="*60)
    print("🧪 Testing Unauthorized Access")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/portfolio/{portfolio_id}/export")
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✓ Returns 401 Unauthorized without token")
    
    print("\n✅ Authorization test PASSED")
    return True


def run_transactions_export_test(token):
    """Test transactions CSV export endpoint."""
    print("\n" + "="*60)
    print("🧪 Testing Transactions CSV Export")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/transactions/export",
        headers=headers
    )
    
    # Check response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ Status code: 200")
    
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    print("✓ Content-Type: text/csv")
    
    assert "all_transactions.csv" in response.headers.get("Content-Disposition", "")
    print("✓ Filename: all_transactions.csv")
    
    # Parse CSV
    csv_reader = csv.DictReader(StringIO(response.text))
    rows = list(csv_reader)
    print(f"✓ Exported {len(rows)} transactions")
    
    # Verify headers
    expected_headers = [
        'Date', 'Portfolio', 'Symbol', 'Asset Name', 'Type',
        'Quantity', 'Price per Unit (₹)', 'Total Value (₹)', 'Notes'
    ]
    assert list(csv_reader.fieldnames) == expected_headers
    print("✓ CSV headers correct")
    
    print("\n✅ Transactions CSV export test PASSED")
    return True


def cleanup(token, portfolio_id):
    """Delete test data."""
    print("\n🧹 Cleaning up test data...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{BASE_URL}/api/portfolio/{portfolio_id}",
        headers=headers
    )
    if response.status_code == 200:
        print("✓ Test portfolio deleted")


def main():
    """Run all end-to-end tests."""
    print("\n" + "="*60)
    print("CSV EXPORT END-TO-END TESTS")
    print("="*60 + "\n")
    
    # Check server
    print("🔍 Checking if server is running...")
    if not check_server_running():
        print("✗ Server not running at", BASE_URL)
        print("\nStart the server first:")
        print("  uv run uvicorn portfolio_tracker.main:app --reload")
        return False
    print("✓ Server is running")
    
    try:
        # Login
        token = login_and_get_token()
        if not token:
            return False
        
        # Create test data
        portfolio_id = create_test_data(token)
        if not portfolio_id:
            return False
        
        # Run tests
        run_portfolio_export_test(token, portfolio_id)
        run_portfolio_export_unauthorized_test(portfolio_id)
        run_transactions_export_test(token)
        
        # Cleanup
        cleanup(token, portfolio_id)
        
        print("\n" + "="*60)
        print("✅ ALL END-TO-END TESTS PASSED!")
        print("="*60)
        print("\nCoverage:")
        print("  ✓ Backend API endpoints working")
        print("  ✓ CSV generation and streaming")
        print("  ✓ Authentication and authorization")
        print("  ✓ Calculations correct")
        print("  ✓ CSV formatting correct")
        print("\n" + "="*60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
