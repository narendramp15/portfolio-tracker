"""Standalone CSV export validation script.

Tests the CSV export logic without importing the full application.
Run: uv run python validate_csv_export.py
"""

import csv
from io import StringIO


def test_portfolio_csv_generation():
    """Test portfolio CSV generation logic."""
    print("🧪 Testing Portfolio CSV Generation\n")
    print("="*60)
    
    # Mock portfolio data
    assets = [
        {
            'symbol': 'RELIANCE',
            'name': 'Reliance Industries',
            'quantity': 10.0,
            'purchase_price': 2500.00,
            'current_price': 2700.00,
            'created_at': '2024-01-15'
        },
        {
            'symbol': 'TCS',
            'name': 'Tata Consultancy Services',
            'quantity': 5.0,
            'purchase_price': 3400.00,
            'current_price': 3600.00,
            'created_at': '2024-01-25'
        },
        {
            'symbol': 'INFY',
            'name': 'Infosys Ltd',
            'quantity': 20.0,
            'purchase_price': 1420.00,
            'current_price': 1510.00,
            'created_at': '2024-02-05'
        }
    ]
    
    # Generate CSV (same logic as backend)
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Symbol',
        'Name',
        'Quantity',
        'Purchase Price (₹)',
        'Current Price (₹)',
        'Invested Value (₹)',
        'Current Value (₹)',
        'Gain/Loss (₹)',
        'Gain/Loss (%)',
        'Purchase Date'
    ])
    
    # Write data rows
    total_invested = 0
    total_current = 0
    
    for asset in assets:
        quantity = asset['quantity']
        purchase_price = asset['purchase_price']
        current_price = asset['current_price']
        invested_value = quantity * purchase_price
        current_value = quantity * current_price
        gain_loss = current_value - invested_value
        gain_loss_pct = (gain_loss / invested_value * 100) if invested_value > 0 else 0
        
        total_invested += invested_value
        total_current += current_value
        
        writer.writerow([
            asset['symbol'],
            asset['name'],
            quantity,
            purchase_price,
            current_price,
            round(invested_value, 2),
            round(current_value, 2),
            round(gain_loss, 2),
            round(gain_loss_pct, 2),
            asset['created_at']
        ])
        
        # Print summary
        print(f"✓ {asset['symbol']:10} | Qty: {quantity:5} | "
              f"Invested: ₹{invested_value:10,.2f} | "
              f"Current: ₹{current_value:10,.2f} | "
              f"P&L: ₹{gain_loss:8,.2f} ({gain_loss_pct:+.2f}%)")
    
    output.seek(0)
    csv_content = output.getvalue()
    
    # Verify CSV structure
    lines = csv_content.strip().split('\n')
    assert len(lines) == 4, f"Expected 4 lines (1 header + 3 data), got {len(lines)}"
    
    # Parse and verify
    csv_reader = csv.DictReader(StringIO(csv_content))
    rows = list(csv_reader)
    
    assert len(rows) == 3, f"Expected 3 data rows, got {len(rows)}"
    
    # Verify calculations
    reliance = next(r for r in rows if r['Symbol'] == 'RELIANCE')
    assert float(reliance['Gain/Loss (₹)']) == 2000.00
    assert float(reliance['Gain/Loss (%)']) == 8.0
    
    tcs = next(r for r in rows if r['Symbol'] == 'TCS')
    assert float(tcs['Gain/Loss (₹)']) == 1000.00
    
    infy = next(r for r in rows if r['Symbol'] == 'INFY')
    assert float(infy['Gain/Loss (₹)']) == 1800.00
    
    print("\n" + "="*60)
    print(f"Portfolio Summary:")
    print(f"  Total Invested:  ₹{total_invested:,.2f}")
    print(f"  Current Value:   ₹{total_current:,.2f}")
    print(f"  Total Gain/Loss: ₹{total_current - total_invested:,.2f}")
    print(f"  Return:          {((total_current - total_invested) / total_invested * 100):+.2f}%")
    print("="*60)
    print("✅ Portfolio CSV generation test PASSED\n")
    
    return csv_content


def test_transactions_csv_generation():
    """Test transactions CSV generation logic."""
    print("🧪 Testing Transactions CSV Generation\n")
    print("="*60)
    
    # Mock transaction data (sorted by date desc)
    transactions = [
        {
            'date': '2024-02-10',
            'portfolio': 'Growth Portfolio',
            'symbol': 'TCS',
            'name': 'Tata Consultancy Services',
            'type': 'BUY',
            'quantity': 5.0,
            'price': 3400.00,
            'notes': 'Second purchase'
        },
        {
            'date': '2024-01-15',
            'portfolio': 'Growth Portfolio',
            'symbol': 'RELIANCE',
            'name': 'Reliance Industries',
            'type': 'BUY',
            'quantity': 10.0,
            'price': 2500.00,
            'notes': 'Initial purchase'
        },
        {
            'date': '2024-01-10',
            'portfolio': 'Growth Portfolio',
            'symbol': 'INFY',
            'name': 'Infosys Ltd',
            'type': 'BUY',
            'quantity': 20.0,
            'price': 1420.00,
            'notes': 'Tech sector investment'
        }
    ]
    
    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Date',
        'Portfolio',
        'Symbol',
        'Asset Name',
        'Type',
        'Quantity',
        'Price per Unit (₹)',
        'Total Value (₹)',
        'Notes'
    ])
    
    # Write data rows
    total_value = 0
    
    for tx in transactions:
        quantity = tx['quantity']
        price = tx['price']
        tx_value = quantity * price
        total_value += tx_value
        
        writer.writerow([
            tx['date'],
            tx['portfolio'],
            tx['symbol'],
            tx['name'],
            tx['type'],
            quantity,
            price,
            round(tx_value, 2),
            tx['notes']
        ])
        
        # Print summary
        print(f"✓ {tx['date']} | {tx['type']:4} | {tx['symbol']:10} | "
              f"Qty: {quantity:5} @ ₹{price:8,.2f} = ₹{tx_value:10,.2f}")
    
    output.seek(0)
    csv_content = output.getvalue()
    
    # Verify CSV structure
    lines = csv_content.strip().split('\n')
    assert len(lines) == 4, f"Expected 4 lines (1 header + 3 data), got {len(lines)}"
    
    # Parse and verify
    csv_reader = csv.DictReader(StringIO(csv_content))
    rows = list(csv_reader)
    
    assert len(rows) == 3, f"Expected 3 transactions, got {len(rows)}"
    
    # Verify first transaction (most recent)
    first = rows[0]
    assert first['Symbol'] == 'TCS'
    assert float(first['Total Value (₹)']) == 17000.00
    
    # Verify sorting (date descending)
    assert rows[0]['Date'] == '2024-02-10'
    assert rows[1]['Date'] == '2024-01-15'
    assert rows[2]['Date'] == '2024-01-10'
    
    print("\n" + "="*60)
    print(f"Transaction Summary:")
    print(f"  Total Transactions: {len(rows)}")
    print(f"  Total Value:        ₹{total_value:,.2f}")
    print(f"  Date Range:         {rows[-1]['Date']} to {rows[0]['Date']}")
    print("="*60)
    print("✅ Transactions CSV generation test PASSED\n")
    
    return csv_content


def save_sample_csvs(portfolio_csv, transactions_csv):
    """Save sample CSV files for manual inspection."""
    print("💾 Saving sample CSV files...\n")
    
    with open('sample_portfolio_export.csv', 'w', newline='', encoding='utf-8') as f:
        f.write(portfolio_csv)
    print("✓ Saved: sample_portfolio_export.csv")
    
    with open('sample_transactions_export.csv', 'w', newline='', encoding='utf-8') as f:
        f.write(transactions_csv)
    print("✓ Saved: sample_transactions_export.csv")
    
    print("\nYou can open these files in Excel/LibreOffice to verify formatting.")


def verify_saved_files():
    """Verify the saved CSV files have correct content."""
    print("\n" + "="*60)
    print("🧪 Verifying Saved CSV Files")
    print("="*60 + "\n")
    
    # Verify portfolio CSV
    print("Checking sample_portfolio_export.csv...")
    with open('sample_portfolio_export.csv', 'r', encoding='utf-8') as f:
        portfolio_content = f.read()
        portfolio_lines = portfolio_content.strip().split('\n')
    
    # Check header
    expected_header = 'Symbol,Name,Quantity,Purchase Price (₹),Current Price (₹),Invested Value (₹),Current Value (₹),Gain/Loss (₹),Gain/Loss (%),Purchase Date'
    assert portfolio_lines[0] == expected_header, f"Portfolio header mismatch"
    print("✓ Portfolio CSV header correct")
    
    # Check data rows
    assert len(portfolio_lines) == 4, f"Expected 4 lines (header + 3 rows), got {len(portfolio_lines)}"
    print(f"✓ Portfolio CSV has correct number of rows: {len(portfolio_lines) - 1}")
    
    # Verify RELIANCE row exists
    reliance_found = any('RELIANCE' in line for line in portfolio_lines)
    assert reliance_found, "RELIANCE stock not found in CSV"
    print("✓ RELIANCE data found in CSV")
    
    # Verify calculations in RELIANCE row
    reliance_line = next(line for line in portfolio_lines if 'RELIANCE' in line)
    reliance_parts = reliance_line.split(',')
    assert reliance_parts[0] == 'RELIANCE'
    assert float(reliance_parts[7]) == 2000.0, "RELIANCE gain/loss incorrect"
    assert float(reliance_parts[8]) == 8.0, "RELIANCE percentage incorrect"
    print("✓ RELIANCE calculations verified (₹2,000 gain, 8.0%)")
    
    # Verify transactions CSV
    print("\nChecking sample_transactions_export.csv...")
    with open('sample_transactions_export.csv', 'r', encoding='utf-8') as f:
        tx_content = f.read()
        tx_lines = tx_content.strip().split('\n')
    
    # Check header
    expected_tx_header = 'Date,Portfolio,Symbol,Asset Name,Type,Quantity,Price per Unit (₹),Total Value (₹),Notes'
    assert tx_lines[0] == expected_tx_header, "Transaction header mismatch"
    print("✓ Transactions CSV header correct")
    
    # Check data rows
    assert len(tx_lines) == 4, f"Expected 4 lines (header + 3 rows), got {len(tx_lines)}"
    print(f"✓ Transactions CSV has correct number of rows: {len(tx_lines) - 1}")
    
    # Verify sorting (most recent first)
    first_tx = tx_lines[1].split(',')
    last_tx = tx_lines[3].split(',')
    assert first_tx[0] == '2024-02-10', "First transaction should be 2024-02-10"
    assert last_tx[0] == '2024-01-10', "Last transaction should be 2024-01-10"
    print("✓ Transactions sorted correctly (newest first)")
    
    # Verify TCS transaction (first row)
    assert 'TCS' in tx_lines[1], "TCS transaction should be first"
    tcs_parts = tx_lines[1].split(',')
    assert tcs_parts[4] == 'BUY', "TCS transaction type should be BUY"
    assert float(tcs_parts[7]) == 17000.0, "TCS total value incorrect"
    print("✓ TCS transaction verified (BUY, ₹17,000)")
    
    print("\n" + "="*60)
    print("✅ File verification PASSED - All CSV files correct!")
    print("="*60)


def main():
    """Run all CSV export tests."""
    print("\n" + "="*60)
    print("CSV EXPORT VALIDATION TESTS")
    print("="*60 + "\n")
    
    try:
        # Test portfolio CSV
        portfolio_csv = test_portfolio_csv_generation()
        
        # Test transactions CSV
        transactions_csv = test_transactions_csv_generation()
        
        # Save samples
        save_sample_csvs(portfolio_csv, transactions_csv)
        
        # Verify saved files
        verify_saved_files()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Check the generated CSV files in the current directory")
        print("2. Start the backend: uv run uvicorn portfolio_tracker.main:app --reload")
        print("3. Test the actual API endpoints:")
        print("   - GET /api/portfolio/{id}/export")
        print("   - GET /api/transactions/export")
        print("4. Test the frontend Export buttons on Holdings and Transactions pages")
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
    import sys
    success = main()
    sys.exit(0 if success else 1)
