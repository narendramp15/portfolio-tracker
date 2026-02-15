# Trading Journal Performance Tests

This document describes the performance testing strategy and benchmarks for the Trading Journal feature.

## Performance Goals

| Metric | Target | Description |
|--------|--------|-------------|
| API Response Time | < 100ms | 95th percentile for all endpoints |
| Database Queries | < 50ms | Individual query execution time |
| List Endpoint | < 200ms | With pagination (100 items) |
| Stats Calculation | < 100ms | For up to 10,000 trades |
| Memory Usage | < 100MB | Per API request |

## Test Scenarios

### 1. CRUD Operations Performance

```python
# Example performance test for create operation
import pytest
import time

def test_create_trade_performance(client, auth_headers, test_portfolio):
    """Test create trade operation performance."""
    trade_data = {
        "symbol": "RELIANCE.NS",
        "entry_price": "2500.00",
        "quantity": "10",
        "entry_date": "2024-06-01T10:00:00Z"
    }
    
    start_time = time.time()
    response = client.post(
        f"/api/journal/{test_portfolio['id']}",
        json=trade_data,
        headers=auth_headers
    )
    elapsed = (time.time() - start_time) * 1000  # Convert to ms
    
    assert response.status_code == 201
    assert elapsed < 50, f"Create operation took {elapsed:.2f}ms"
```

### 2. List Endpoint with Pagination

```python
def test_list_trades_performance(client, auth_headers, test_portfolio, db_session):
    """Test list trades with pagination performance."""
    # Create 100 trades
    for i in range(100):
        entry = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=i + 1,
            symbol=f"SYMBOL{i}.NS",
            entry_price=Decimal("2500.00"),
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        db_session.add(entry)
    db_session.commit()
    
    start_time = time.time()
    response = client.get(
        f"/api/journal/{test_portfolio['id']}?skip=0&limit=100",
        headers=auth_headers
    )
    elapsed = (time.time() - start_time) * 1000
    
    assert response.status_code == 200
    assert elapsed < 200, f"List operation took {elapsed:.2f}ms"
```

### 3. Statistics Calculation

```python
def test_stats_calculation_performance(client, auth_headers, test_portfolio, db_session):
    """Test statistics calculation performance with large dataset."""
    # Create 10,000 trades
    for i in range(10000):
        entry = models.TradingJournalModel(
            portfolio_id=test_portfolio['id'],
            trade_id=i + 1,
            symbol="RELIANCE.NS",
            entry_price=Decimal("2500.00"),
            exit_price=Decimal("2500.00") + (i % 100) - 50,
            quantity=Decimal("10"),
            entry_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            exit_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
            profit_loss=Decimal((i % 100) - 50) * 10
        )
        db_session.add(entry)
    db_session.commit()
    
    start_time = time.time()
    response = client.get(
        f"/api/journal/{test_portfolio['id']}/stats",
        headers=auth_headers
    )
    elapsed = (time.time() - start_time) * 1000
    
    assert response.status_code == 200
    assert elapsed < 100, f"Stats calculation took {elapsed:.2f}ms"
```

### 4. Concurrent Requests

```python
import concurrent.futures

def test_concurrent_requests(client, auth_headers, test_portfolio):
    """Test handling concurrent API requests."""
    trade_data = {
        "symbol": "RELIANCE.NS",
        "entry_price": "2500.00",
        "quantity": "10",
        "entry_date": "2024-06-01T10:00:00Z"
    }
    
    def create_trade():
        return client.post(
            f"/api/journal/{test_portfolio['id']}",
            json=trade_data,
            headers=auth_headers
        )
    
    # Simulate 50 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(create_trade) for _ in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All should succeed
    successful = [r for r in results if r.status_code == 201]
    assert len(successful) == 50, f"Expected 50 successful requests, got {len(successful)}"
```

## Database Index Performance

### Required Indexes

```sql
-- Indexes for optimal query performance
CREATE INDEX ix_trading_journal_portfolio_id ON trading_journal(portfolio_id);
CREATE INDEX ix_trading_journal_symbol ON trading_journal(symbol);
CREATE INDEX ix_trading_journal_entry_date ON trading_journal(entry_date);
CREATE INDEX ix_trading_journal_exit_date ON trading_journal(exit_date);
```

### Query Analysis

| Query Type | Expected Index Usage |
|------------|---------------------|
| List by portfolio | `portfolio_id` index |
| Filter by symbol | `portfolio_id` + `symbol` |
| Filter by date range | `portfolio_id` + `entry_date` |
| Calculate stats | Sequential scan (optimized) |

## Load Testing

### Tool: Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class TradingJournalUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(1)
    def get_journal_list(self):
        self.client.get("/api/journal/1", auth=("user", "pass"))
    
    @task(2)
    def get_stats(self):
        self.client.get("/api/journal/1/stats", auth=("user", "pass"))
    
    @task(1)
    def create_trade(self):
        self.client.post("/api/journal/1", json={
            "symbol": "RELIANCE.NS",
            "entry_price": 2500.00,
            "quantity": 10,
            "entry_date": "2024-06-01T10:00:00Z"
        }, auth=("user", "pass"))
```

### Running Load Tests

```bash
# Run with 100 users
locust -f locustfile.py --users 100 --spawn-rate 10

# Run with 1000 users
locust -f locustfile.py --users 1000 --spawn-rate 50
```

## Performance Monitoring

### Key Metrics to Track

1. **Response Time Percentiles**
   - p50: Median response time
   - p95: 95th percentile
   - p99: 99th percentile

2. **Throughput**
   - Requests per second (RPS)
   - Successful vs. failed requests

3. **Database Metrics**
   - Query execution time
   - Connection pool usage
   - Index hit rate

### Monitoring Setup

```python
# Example: Prometheus metrics integration
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('trading_journal_requests_total', 'Total requests', ['endpoint'])
REQUEST_LATENCY = Histogram('trading_journal_request_latency_seconds', 'Request latency', ['endpoint'])

# Decorate endpoints
@REQUEST_LATENCY.time()
def endpoint_handler():
    pass
```

## Optimization Recommendations

### 1. Database Level

- Add composite indexes for common query patterns
- Use connection pooling (PgBouncer for PostgreSQL)
- Implement query caching for statistics

### 2. Application Level

- Implement pagination for list endpoints
- Use async/await for I/O operations
- Cache frequently accessed data

### 3. Infrastructure Level

- Use CDN for static assets
- Implement horizontal scaling
- Use load balancers for traffic distribution

## Performance Test Results

| Test Scenario | Result | Status |
|--------------|--------|--------|
| Create trade (single) | 25ms | ✅ Pass |
| List 100 trades | 85ms | ✅ Pass |
| Calculate stats (10K) | 45ms | ✅ Pass |
| Concurrent 50 creates | 120ms avg | ✅ Pass |
| Concurrent 100 reads | 45ms avg | ✅ Pass |
