"""
Centralized configuration management for Portfolio Tracker.

Priority order (highest to lowest):
1. Environment variables set programmatically (e.g., in tests)
2. Environment variables from system
3. .env file values
4. Default values

Usage:
    from portfolio_tracker.config import settings
    
    # Access settings
    database_url = settings.DATABASE_URL
    secret_key = settings.SECRET_KEY
    
    # Check if in testing mode
    if settings.TESTING:
        ...

For tests:
    import os
    os.environ['TESTING'] = '1'  # Set BEFORE importing anything from portfolio_tracker
"""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv


class Settings:
    """
    Application settings with environment variable support.
    
    Priority:
    1. Already-set environment variables (allows test overrides)
    2. .env file (loaded with override=False)
    3. Default values
    """
    
    def __init__(self):
        # Check for testing mode FIRST, before loading .env
        # This allows tests to set TESTING=1 before import
        self._testing = os.getenv("TESTING", "").lower() in ("1", "true", "yes")
        
        # Only load .env in non-testing mode
        # override=False means existing env vars take priority
        if not self._testing:
            load_dotenv(override=False)
        
        # Re-check testing after potential .env load
        self._testing = os.getenv("TESTING", "").lower() in ("1", "true", "yes")
    
    @property
    def TESTING(self) -> bool:
        """Whether the application is running in test mode."""
        return self._testing
    
    @property
    def DEBUG(self) -> bool:
        """Whether debug mode is enabled."""
        return os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    
    # ===================
    # Database Settings
    # ===================
    
    @property
    def DATABASE_URL(self) -> str:
        """
        Get the database URL.
        
        In testing mode, uses a unique file-based SQLite database per test session.
        This avoids the shared-cache in-memory issues while still being fast.
        Otherwise, constructs from PG* vars or falls back to DATABASE_URL env var.
        """
        if self._testing:
            # Use a file-based test database for better isolation
            # The file will be in the project root and can be cleaned up
            import tempfile
            return f"sqlite:///{tempfile.gettempdir()}/test_portfolio.db"
        
        # Try individual PostgreSQL variables (Neon/Supabase style)
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")
        pg_host = os.getenv("PGHOST")
        pg_port = os.getenv("PGPORT", "5432")
        pg_database = os.getenv("PGDATABASE")
        
        if all([pg_user, pg_password, pg_host, pg_database]):
            return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        
        # Fall back to DATABASE_URL or SQLite
        return os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    
    @property
    def DB_ECHO(self) -> bool:
        """Whether to echo SQL statements (for debugging)."""
        return os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")
    
    # ===================
    # Security Settings
    # ===================
    
    @property
    def SECRET_KEY(self) -> str:
        """Secret key for JWT tokens."""
        default = "dev-secret-key-change-in-production"
        return os.getenv("SECRET_KEY", default)
    
    @property
    def ENCRYPTION_KEY(self) -> Optional[str]:
        """Key for encrypting sensitive data (broker credentials)."""
        return os.getenv("ENCRYPTION_KEY")
    
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """JWT token expiration time in minutes."""
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 days default
    
    @property
    def ALGORITHM(self) -> str:
        """JWT algorithm."""
        return os.getenv("JWT_ALGORITHM", "HS256")
    
    # ===================
    # Google OAuth Settings
    # ===================
    
    @property
    def GOOGLE_CLIENT_ID(self) -> Optional[str]:
        """Google OAuth client ID."""
        return os.getenv("GOOGLE_CLIENT_ID")
    
    @property
    def GOOGLE_CLIENT_SECRET(self) -> Optional[str]:
        """Google OAuth client secret."""
        return os.getenv("GOOGLE_CLIENT_SECRET")
    
    @property
    def GOOGLE_REDIRECT_URI(self) -> str:
        """Google OAuth redirect URI."""
        return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    
    # ===================
    # Frontend Settings
    # ===================
    
    @property
    def FRONTEND_URL(self) -> str:
        """Frontend URL for redirects."""
        return os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Allowed CORS origins."""
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000")
        origin_list = [origin.strip() for origin in origins.split(",") if origin.strip()]
        
        # Also add FRONTEND_URL if set and not already included
        frontend = self.FRONTEND_URL
        if frontend and frontend not in origin_list:
            origin_list.append(frontend)
        
        return origin_list
    
    # ===================
    # Broker Settings
    # ===================
    
    @property
    def ZERODHA_API_KEY(self) -> Optional[str]:
        """Zerodha API key."""
        return os.getenv("ZERODHA_API_KEY")
    
    @property
    def ZERODHA_API_SECRET(self) -> Optional[str]:
        """Zerodha API secret."""
        return os.getenv("ZERODHA_API_SECRET")
    
    @property
    def ZERODHA_REDIRECT_URL(self) -> str:
        """Zerodha OAuth redirect URL."""
        return os.getenv("ZERODHA_REDIRECT_URL", "http://localhost:8000/api/broker/zerodha/callback")
    
    # ===================
    # Logging Settings
    # ===================
    
    @property
    def LOG_LEVEL(self) -> str:
        """Logging level."""
        return os.getenv("LOG_LEVEL", "INFO")
    
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in self.DATABASE_URL
    
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL database."""
        return "postgresql" in self.DATABASE_URL
    
    def print_config_summary(self):
        """Print a summary of current configuration (for debugging)."""
        db_type = "SQLite" if self.is_sqlite() else "PostgreSQL"
        print(f"{'='*50}")
        print(f"Configuration Summary")
        print(f"{'='*50}")
        print(f"Testing Mode: {self.TESTING}")
        print(f"Debug Mode: {self.DEBUG}")
        print(f"Database Type: {db_type}")
        if not self._testing and not self.is_sqlite():
            # Don't print sensitive URL, just host
            pg_host = os.getenv("PGHOST", "unknown")
            pg_db = os.getenv("PGDATABASE", "unknown")
            print(f"Database: {pg_db} @ {pg_host}")
        print(f"Frontend URL: {self.FRONTEND_URL}")
        print(f"Google OAuth: {'Configured' if self.GOOGLE_CLIENT_ID else 'Not configured'}")
        print(f"Zerodha: {'Configured' if self.ZERODHA_API_KEY else 'Not configured'}")
        print(f"{'='*50}")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Note: This is cached, so the settings are only loaded once.
    For tests, set environment variables BEFORE first import.
    """
    return Settings()


# Singleton instance for easy import
settings = get_settings()
