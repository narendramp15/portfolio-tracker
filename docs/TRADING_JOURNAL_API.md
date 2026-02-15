# Trading Journal API Documentation

This document describes the Trading Journal feature API endpoints for the Portfolio Tracker application.

## Overview

The Trading Journal feature allows users to record and analyze their trades. It provides functionality to:
- Record trades with entry/exit prices, quantities, and dates
- Track profit/loss for each trade
- Calculate portfolio statistics (win rate, total P/L, etc.)
- Add notes and annotations to trades

## Base URL

```
/api/journal
```

## Authentication

All endpoints require Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Create Trading Journal Entry

Creates a new trading journal entry for a portfolio.

**Endpoint:** `POST /{portfolio_id}`

**Request Body:**
```json
{
  "symbol": "RELIANCE.NS",
  "entry_price": 2500.00,
  "exit_price": 2700.00,
  "quantity": 10,
  "entry_date": "2024-06-01T10:00:00Z",
  "exit_date": "2024-06-15T14:30:00Z",
  "notes": "Long position in Reliance Industries"
}
```

**Required Fields:**
- `symbol` (string): Stock symbol (e.g., "RELIANCE.NS")
- `entry_price` (number): Price at which the trade was entered
- `quantity` (number): Number of shares traded
- `entry_date` (datetime): Date and time when the trade was entered

**Optional Fields:**
- `exit_price` (number): Price at which the trade was exited
- `exit_date` (datetime): Date and time when the trade was exited
- `notes` (string): Additional notes about the trade

**Response:** `201 Created`
```json
{
  "id": 1,
  "portfolio_id": 1,
  "trade_id": 1,
  "symbol": "RELIANCE.NS",
  "entry_price": 2500.00,
  "exit_price": 2700.00,
  "quantity": 10,
  "entry_date": "2024-06-01T10:00:00Z",
  "exit_date": "2024-06-15T14:30:00Z",
  "profit_loss": 2000.00,
  "notes": "Long position in Reliance Industries",
  "created_at": "2024-06-16T10:00:00Z",
  "updated_at": "2024-06-16T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Portfolio not found

---

### Get Portfolio Journal Entries

Retrieves all trading journal entries for a portfolio.

**Endpoint:** `GET /{portfolio_id}`

**Query Parameters:**
- `skip` (integer, optional): Number of records to skip (default: 0)
- `limit` (integer, optional): Maximum number of records (default: 100, max: 500)
- `symbol` (string, optional): Filter by symbol
- `start_date` (datetime, optional): Filter by entry date (start)
- `end_date` (datetime, optional): Filter by entry date (end)

**Response:** `200 OK`
```json
[
  {
    "id": 2,
    "portfolio_id": 1,
    "trade_id": 2,
    "symbol": "TCS.NS",
    "entry_price": 3500.00,
    "exit_price": 3400.00,
    "quantity": 5,
    "entry_date": "2024-06-05T09:00:00Z",
    "exit_date": "2024-06-20T16:00:00Z",
    "profit_loss": -500.00,
    "notes": null,
    "created_at": "2024-06-21T10:00:00Z",
    "updated_at": "2024-06-21T10:00:00Z"
  },
  {
    "id": 1,
    "portfolio_id": 1,
    "trade_id": 1,
    "symbol": "RELIANCE.NS",
    "entry_price": 2500.00,
    "exit_price": 2700.00,
    "quantity": 10,
    "entry_date": "2024-06-01T10:00:00Z",
    "exit_date": "2024-06-15T14:30:00Z",
    "profit_loss": 2000.00,
    "notes": "Long position",
    "created_at": "2024-06-16T10:00:00Z",
    "updated_at": "2024-06-16T10:00:00Z"
  }
]
```

---

### Get Journal Statistics

Retrieves trading journal statistics for a portfolio.

**Endpoint:** `GET /{portfolio_id}/stats`

**Query Parameters:**
- `start_date` (datetime, optional): Filter by entry date (start)
- `end_date` (datetime, optional): Filter by entry date (end)

**Response:** `200 OK`
```json
{
  "total_trades": 10,
  "winning_trades": 6,
  "losing_trades": 4,
  "win_rate": 60.0,
  "total_profit_loss": 15000.00,
  "average_profit_loss": 1500.00,
  "best_trade": 5000.00,
  "worst_trade": -1000.00
}
```

**Statistics Explained:**
- `total_trades`: Total number of completed trades
- `winning_trades`: Number of profitable trades
- `losing_trades`: Number of losing trades
- `win_rate`: Percentage of winning trades
- `total_profit_loss`: Sum of all profit/loss amounts
- `average_profit_loss`: Average profit/loss per trade
- `best_trade`: Highest single trade profit
- `worst_trade`: Lowest single trade (highest loss)

---

### Get Specific Journal Entry

Retrieves a specific trading journal entry.

**Endpoint:** `GET /{portfolio_id}/{journal_id}`

**Response:** `200 OK`
```json
{
  "id": 1,
  "portfolio_id": 1,
  "trade_id": 1,
  "symbol": "RELIANCE.NS",
  "entry_price": 2500.00,
  "exit_price": 2700.00,
  "quantity": 10,
  "entry_date": "2024-06-01T10:00:00Z",
  "exit_date": "2024-06-15T14:30:00Z",
  "profit_loss": 2000.00,
  "notes": "Long position in Reliance Industries",
  "created_at": "2024-06-16T10:00:00Z",
  "updated_at": "2024-06-16T10:00:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Journal entry not found

---

### Update Journal Entry

Updates an existing trading journal entry.

**Endpoint:** `PATCH /{portfolio_id}/{journal_id}`

**Request Body:**
```json
{
  "exit_price": 2750.00,
  "exit_date": "2024-06-20T16:00:00Z",
  "notes": "Updated exit - took profit early"
}
```

**Note:** Only `exit_price`, `exit_date`, and `notes` can be updated.

**Response:** `200 OK`
```json
{
  "id": 1,
  "portfolio_id": 1,
  "trade_id": 1,
  "symbol": "RELIANCE.NS",
  "entry_price": 2500.00,
  "exit_price": 2750.00,
  "quantity": 10,
  "entry_date": "2024-06-01T10:00:00Z",
  "exit_date": "2024-06-20T16:00:00Z",
  "profit_loss": 2500.00,
  "notes": "Updated exit - took profit early",
  "created_at": "2024-06-16T10:00:00Z",
  "updated_at": "2024-06-21T10:00:00Z"
}
```

**Note:** When `exit_price` is updated, `profit_loss` is automatically recalculated.

---

### Delete Journal Entry

Deletes a trading journal entry.

**Endpoint:** `DELETE /{portfolio_id}/{journal_id}`

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Journal entry not found

---

## Data Flow

### Creating a Trade
1. User provides symbol, entry price, quantity, and entry date
2. System creates the journal entry with `trade_id` auto-incremented
3. If exit details are provided, `profit_loss` is calculated
4. Entry is saved with timestamps

### Updating a Trade
1. User provides updated exit price/date or notes
2. System recalculates `profit_loss` if exit price changed
3. `updated_at` timestamp is refreshed

### Calculating Statistics
- **Win Rate**: `(winning_trades / total_trades) * 100`
- **Total P/L**: Sum of all `profit_loss` values
- **Average P/L**: `total_profit_loss / total_trades`
- **Best/Worst Trade**: Min/max of `profit_loss` values

---

## Error Handling

All errors follow standard FastAPI error response format:

```json
{
  "detail": "Error message description"
}
```

Common error codes:
- `401 Unauthorized`: Invalid or missing authentication token
- `404 Not Found`: Portfolio or journal entry not found
- `422 Unprocessable Entity`: Validation error in request data

---

## Notes

- Each portfolio has its own sequence of `trade_id` values
- `profit_loss` is calculated as: `(exit_price - entry_price) * quantity`
- Positive values indicate profit, negative values indicate loss
- Entries are sorted by `entry_date` in descending order (most recent first)
- Both Indian (INR) and international currencies can be used
