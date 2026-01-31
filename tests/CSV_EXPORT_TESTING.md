# CSV Export Testing Guide

This guide explains how to test the CSV export functionality for portfolios and transactions.

## Automated Tests

### Run All CSV Export Tests

```bash
# Run the CSV export test suite
uv run pytest tests/test_csv_export.py -v

# Run with coverage
uv run pytest tests/test_csv_export.py --cov=portfolio_tracker.routers --cov-report=html -v

# Run a specific test
uv run pytest tests/test_csv_export.py::TestCSVExport::test_portfolio_csv_export_success -v
```

### Test Coverage

The automated tests cover:

✅ **Portfolio Export**
- Successful CSV export with correct data
- Correct CSV headers and format
- Calculations (gain/loss, percentages)
- Authorization checks
- Error handling (404, unauthorized, wrong user)

✅ **Transaction Export**
- Successful CSV export with correct data
- Correct CSV headers and format
- Transaction ordering (date descending)
- Empty transaction list handling
- Authorization checks

## Manual Testing

### Option 1: Using the Manual Test Script

```bash
# Create sample test data
uv run python test_csv_export_manual.py
```

This will:
1. Create a test user and portfolio with sample stocks (RELIANCE, TCS, INFY)
2. Add transactions
3. Print curl commands to test the endpoints
4. Provide instructions for frontend testing

### Option 2: Using the API Directly

1. **Start the backend server:**
```bash
uv run uvicorn portfolio_tracker.main:app --reload
```

2. **Login and get your access token:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_email@example.com&password=your_password"
```

3. **Export portfolio CSV:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/portfolio/1/export \
  -o portfolio.csv
```

4. **Export transactions CSV:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/transactions/export \
  -o transactions.csv
```

### Option 3: Using the Frontend

1. **Start backend:**
```bash
uv run uvicorn portfolio_tracker.main:app --reload
```

2. **Start frontend (in another terminal):**
```bash
cd frontend
npm run dev
```

3. **Test in browser:**
   - Navigate to http://localhost:5173
   - Login with your account
   - Go to **Holdings** page
   - Select a portfolio from dropdown
   - Click **"Export CSV"** button
   - Verify the downloaded CSV file
   - Go to **Transactions** page
   - Click **"Export CSV"** button
   - Verify the downloaded CSV file

## Expected CSV Formats

### Portfolio Export Format

```csv
Symbol,Name,Quantity,Purchase Price (₹),Current Price (₹),Invested Value (₹),Current Value (₹),Gain/Loss (₹),Gain/Loss (%),Purchase Date
RELIANCE,Reliance Industries Ltd,15.0,2450.0,2680.0,36750.0,40200.0,3450.0,9.39,2024-01-10
TCS,Tata Consultancy Services,8.0,3350.0,3580.0,26800.0,28640.0,1840.0,6.87,2024-01-25
```

### Transaction Export Format

```csv
Date,Portfolio,Symbol,Asset Name,Type,Quantity,Price per Unit (₹),Total Value (₹),Notes
2024-02-05,Demo Portfolio,INFY,Infosys Ltd,BUY,20.0,1420.0,28400.0,Initial purchase - Infosys
2024-01-25,Demo Portfolio,TCS,Tata Consultancy Services,BUY,8.0,3350.0,26800.0,Initial purchase - TCS
2024-01-10,Demo Portfolio,RELIANCE,Reliance Industries Ltd,BUY,15.0,2450.0,36750.0,Initial purchase - Reliance
```

## Troubleshooting

### Test Fails: "401 Unauthorized"
- Check that the token is valid
- Ensure token is properly passed in Authorization header

### Test Fails: "404 Not Found"
- Verify portfolio/user exists in database
- Check that portfolio belongs to the authenticated user

### CSV Empty or Incorrect Data
- Verify assets exist in the portfolio
- Check transactions are linked to correct portfolio and assets
- Review database content using SQL query

### Frontend Export Button Not Working
- Open browser DevTools (F12)
- Check Console for JavaScript errors
- Verify network request shows correct Authorization header
- Check backend logs for errors

## Verify CSV Content

### Using Python
```python
import csv

with open('portfolio.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{row['Symbol']}: {row['Gain/Loss (₹)']} (₹)")
```

### Using Excel/LibreOffice
- Open the downloaded CSV file
- Verify columns are properly formatted
- Check calculations are correct

### Using Command Line
```bash
# View CSV content
cat portfolio.csv

# Count rows (excluding header)
tail -n +2 portfolio.csv | wc -l

# Filter specific columns
csvcut -c Symbol,Name,Quantity portfolio.csv
```

## Next Steps

After verifying CSV export works:
- ✅ Todo #1 Complete: CSV Export
- Move to Todo #2: Price Alerts
- Move to Todo #3: Tax Reports
- Add subscription tiers (Todo #4-7)
