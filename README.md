# Portfolio Tracker

A modern Python FastAPI application for tracking and managing investment portfolios with a beautiful, responsive web interface.

## ✨ Features

- 📊 **Modern Dashboard** - Real-time portfolio statistics with interactive charts (Doughnut & Bar charts)
- 💼 **Portfolio Management** - Create, organize, and manage multiple investment portfolios
- 💰 **Asset Tracking** - Monitor your investments with detailed asset information
- 📈 **Performance Analytics** - Analyze gain/loss metrics and portfolio performance
- 📱 **Responsive Design** - Beautiful sidebar-based UI with mobile-friendly layout
- 🎨 **Modern UI/UX** - Professional gradient colors, smooth animations, and intuitive navigation
- 🔌 **RESTful API** - Complete API for programmatic access to all features
- ⚡ **Built with FastAPI** - Modern async Python web framework
- 🔒 **Type-Safe** - Full Python 3.13+ type hints and Pydantic validation

## 🎯 UI Features

- **Sidebar Navigation** - Clean, persistent navigation with active state indicators
- **Interactive Charts** - Chart.js integration for portfolio visualization
- **Modern Cards** - Beautiful stat cards with gradient backgrounds and hover effects
- **Modal Dialogs** - Smooth animations and intuitive forms
- **Responsive Tables** - Professional transaction history with filtering
- **Loading States** - Spinner animations and meaningful empty states
- **Dark Theme Ready** - CSS variables for easy theme customization

## Requirements

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) (recommended)

## Installation

### Prerequisites

First, install `uv` - the modern Python package manager:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (using powershell)
powershell -ExecutionPolicy BypassScope -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Using uv (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/portfolio-tracker.git
cd portfolio-tracker
```

2. Install dependencies with uv:
```bash
# Install production dependencies
uv sync

# Install with all development dependencies
uv sync --all-extras
```

3. Run the application:
```bash
# Start FastAPI server
uv run uvicorn portfolio_tracker.main:app --reload

# Or use Python directly
uv run python -m portfolio_tracker.main
```

The application will be available at `http://localhost:8000`
- Web Interface: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Modern UI (React SPA)

This project now includes a modern React + Tailwind SPA under `frontend/`.

### Dev mode (recommended)
1. Start the backend:
```bash
uv run uvicorn portfolio_tracker.main:app --reload
```
2. Start the frontend (Vite dev server):
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` (API requests proxy to `http://localhost:8000/api`).

### Production mode (served by FastAPI)
Build the frontend once:
```bash
cd frontend
npm run build
```
Then run the backend normally. When `frontend/dist/index.html` exists, FastAPI serves the SPA at:
- `http://localhost:8000/login`
- `http://localhost:8000/app/*`

## Configuration

### Database Options

**SQLite (Development - Default)**
```bash
# Automatically created at ./portfolio.db
# Good for local development only
DATABASE_URL=sqlite:///./portfolio.db
```

**PostgreSQL (Production - Recommended)**

Choose one of these free options:

**Option 1: Supabase (Recommended - No expiration)**
1. Create project at https://supabase.com
2. Get connection string from Settings → Database → Connection String (URI)
3. Set in `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
   ```

**Option 2: Render PostgreSQL (Free for 90 days)**
- Auto-created when deploying via Blueprint
- See [RENDER_DEPLOY.md](RENDER_DEPLOY.md) for setup

**Option 3: Other providers**
- Neon (free tier)
- ElephantSQL
- Railway
- Heroku Postgres

### Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update the `.env` file with your configuration:
```env
DEBUG=True
DATABASE_URL=postgresql://user:password@host:5432/dbname  # Use PostgreSQL for persistence
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ENCRYPTION_KEY=your-encryption-key  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Broker API credentials (optional)
ZERODHA_API_KEY=your_zerodha_api_key
ZERODHA_API_SECRET=your_zerodha_api_secret
ZERODHA_REDIRECT_URL=http://localhost:8000/api/broker/zerodha/callback
```

## Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. **Home Dashboard** - View your portfolio statistics and interactive charts
3. **Portfolios** - Create, view, and manage your investment portfolios
4. **Transactions** - Track all your buy/sell transactions with advanced filtering
5. **Dashboard** - Real-time performance metrics with visual analytics

#### UI Navigation
- Use the **sidebar** on the left to navigate between sections
- Click the **menu icon** on mobile to toggle the sidebar
- Use the **search box** in the header to find portfolios
- View **notifications** and **user menu** in the top-right corner

### API Usage

```python
import requests

# Create a portfolio
response = requests.post(
    "http://localhost:8000/api/portfolios/",
    json={"name": "My Portfolio", "description": "My investments"}
)
portfolio = response.json()

# Add an asset
requests.post(
    f"http://localhost:8000/api/portfolios/{portfolio['id']}/assets",
    json={
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "quantity": 10,
        "current_price": 150.00,
        "purchase_price": 140.00
    }
)

# Get dashboard stats
stats = requests.get("http://localhost:8000/api/dashboard/stats").json()
print(f"Total Portfolio Value: ${stats['total_portfolio_value']}")
```

## Testing

Run tests with pytest:
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=portfolio_tracker

# Run specific test file
uv run pytest tests/test_models.py -v
```

## Code Quality

Format code with black:
```bash
uv run black portfolio_tracker tests
```

Lint with ruff:
```bash
uv run ruff check portfolio_tracker tests
```

Type check with mypy:
```bash
uv run mypy portfolio_tracker
```

## Project Structure

```
portfolio-tracker/
├── portfolio_tracker/                    # Main application package
│   ├── __init__.py                      # Package initialization
│   ├── main.py                          # FastAPI application entry point
│   ├── database.py                      # Database configuration (SQLAlchemy)
│   ├── schemas.py                       # Pydantic request/response models
│   ├── crud.py                          # Database operations
│   ├── core.py                          # Core business logic
│   ├── models.py                        # Data models (both DB & core)
│   ├── utils.py                         # Utility functions
│   ├── routers/                         # API route handlers
│   │   ├── __init__.py
│   │   ├── portfolio.py                 # Portfolio endpoints
│   │   ├── transactions.py              # Transaction endpoints
│   │   ├── dashboard.py                 # Dashboard endpoints
│   │   └── reviews.py                   # Reviews endpoints (placeholder)
│   ├── templates/                       # HTML templates
│   │   ├── base.html                    # Base template layout
│   │   ├── portfolio.html               # Portfolio management page
│   │   ├── transactions.html            # Transactions page
│   │   ├── dashboard.html               # Dashboard page
│   │   └── review.html                  # Review page (placeholder)
│   └── static/                          # Static assets
│       └── styles.css                   # Global stylesheets
├── tests/                               # Test suite
│   ├── __init__.py
│   ├── test_core.py                     # Core functionality tests
│   └── test_models.py                   # Model tests
├── docs/                                # Documentation
├── htmlcov/                             # Coverage reports
├── .github/                             # GitHub configuration
│   └── workflows/
│       └── tests.yml                    # CI/CD workflow
├── .vscode/                             # VS Code settings
│   ├── settings.json
│   └── launch.json
├── pyproject.toml                       # Project configuration (PEP 517/518)
├── uv.lock                              # Dependency lock file
├── uv-workspace.toml                    # UV workspace configuration
├── .env.example                         # Environment variables template
├── .gitignore                           # Git ignore rules
├── .pre-commit-config.yaml              # Pre-commit hooks configuration
├── LICENSE                              # MIT License
└── README.md                            # This file
```

## Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern async web framework
- **Database**: SQLAlchemy with SQLite (easily switchable to PostgreSQL/MySQL)
- **Validation**: [Pydantic](https://docs.pydantic.dev/) - Data validation
- **Testing**: [pytest](https://pytest.org/) - Unit and integration testing
- **Code Quality**:
  - [Black](https://black.readthedocs.io/) - Code formatter
  - [Ruff](https://github.com/astral-sh/ruff) - Fast linter
  - [mypy](https://www.mypy-lang.org/) - Static type checker
- **Package Manager**: [uv](https://docs.astral.sh/uv/) - Ultra-fast Python package manager
- **Python**: 3.13+ with modern type hints

## API Endpoints

### Portfolios
- `GET /api/portfolios/` - List all portfolios
- `POST /api/portfolios/` - Create new portfolio
- `GET /api/portfolios/{id}` - Get portfolio details
- `PUT /api/portfolios/{id}` - Update portfolio
- `DELETE /api/portfolios/{id}` - Delete portfolio
- `GET /api/portfolios/{id}/assets` - List portfolio assets
- `POST /api/portfolios/{id}/assets` - Add asset to portfolio

### Transactions
- `GET /api/transactions/{portfolio_id}` - List transactions
- `POST /api/transactions/{portfolio_id}` - Create transaction
- `GET /api/transactions/{portfolio_id}/{id}` - Get transaction
- `DELETE /api/transactions/{portfolio_id}/{id}` - Delete transaction

### Dashboard
- `GET /api/dashboard/stats` - Get overall statistics
- `GET /api/dashboard/portfolio/{id}` - Get portfolio dashboard

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For support, please open an issue on GitHub or contact the maintainers.
