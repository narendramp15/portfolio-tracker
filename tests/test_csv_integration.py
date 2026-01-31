"""Integration tests for CSV export API endpoints.

These tests use FastAPI's TestClient which handles the app lifecycle.
No need to start the server separately - TestClient does it automatically.

Run: uv run pytest tests/test_csv_integration.py -v -m integration
Or run all tests: uv run pytest tests/test_csv_integration.py -v
"""

import csv
from io import StringIO

import pytest

pytestmark = pytest.mark.integration


class TestCSVExportIntegration:
    """Integration tests for CSV export endpoints using TestClient."""
    
    def test_portfolio_export_endpoint(self, client, auth_headers, test_portfolio):
        """Test GET /api/portfolio/{id}/export endpoint."""
        response = client.get(
            f"/api/portfolio/{test_portfolio['id']}/export",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Test_Portfolio_holdings.csv" in response.headers["Content-Disposition"]
        
        # Verify CSV content
        csv_reader = csv.DictReader(StringIO(response.text))
        rows = list(csv_reader)
        
        assert len(rows) == 2
        assert any(r['Symbol'] == 'RELIANCE' for r in rows)
        assert any(r['Symbol'] == 'TCS' for r in rows)
    
    def test_transactions_export_endpoint(self, client, auth_headers, test_portfolio):
        """Test GET /api/transactions/export endpoint."""
        response = client.get(
            "/api/transactions/export",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "all_transactions.csv" in response.headers["Content-Disposition"]
        
        # Verify CSV content
        csv_reader = csv.DictReader(StringIO(response.text))
        rows = list(csv_reader)
        
        assert len(rows) == 2
        # Check sorting (newest first)
        assert rows[0]['Date'] == '2024-02-10'
        assert rows[1]['Date'] == '2024-01-15'
    
    def test_portfolio_export_unauthorized(self, client, test_portfolio):
        """Test portfolio export without authentication."""
        response = client.get(f"/api/portfolio/{test_portfolio['id']}/export")
        assert response.status_code == 401
    
    def test_transactions_export_unauthorized(self, client):
        """Test transactions export without authentication."""
        response = client.get("/api/transactions/export")
        assert response.status_code == 401
    
    def test_portfolio_export_calculations(self, client, auth_headers, test_portfolio):
        """Test that CSV export calculations are correct."""
        response = client.get(
            f"/api/portfolio/{test_portfolio['id']}/export",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        csv_reader = csv.DictReader(StringIO(response.text))
        rows = list(csv_reader)
        
        # Verify RELIANCE calculations
        reliance = next(r for r in rows if r['Symbol'] == 'RELIANCE')
        assert float(reliance['Gain/Loss (₹)']) == 2000.00
        assert float(reliance['Gain/Loss (%)']) == 8.0
        
        # Verify TCS calculations
        tcs = next(r for r in rows if r['Symbol'] == 'TCS')
        assert float(tcs['Gain/Loss (₹)']) == 1000.00
    
    def test_transactions_export_content(self, client, auth_headers, test_portfolio):
        """Test that transactions CSV has correct data."""
        response = client.get(
            "/api/transactions/export",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        csv_reader = csv.DictReader(StringIO(response.text))
        rows = list(csv_reader)
        
        # Verify TCS transaction
        tcs_tx = rows[0]
        assert tcs_tx['Symbol'] == 'TCS'
        assert tcs_tx['Type'] == 'BUY'
        assert float(tcs_tx['Total Value (₹)']) == 17000.00
        
        # Verify RELIANCE transaction
        reliance_tx = rows[1]
        assert reliance_tx['Symbol'] == 'RELIANCE'
        assert reliance_tx['Type'] == 'BUY'
        assert float(reliance_tx['Total Value (₹)']) == 25000.00
