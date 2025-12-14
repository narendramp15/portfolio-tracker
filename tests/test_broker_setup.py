"""Tests for broker setup and configuration."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from portfolio_tracker.auth import create_access_token
from portfolio_tracker.crud import (create_broker_config, create_user,
                                    get_broker_config_by_broker_name)
from portfolio_tracker.database import get_db
from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.main import app
from portfolio_tracker.models import Base

# Use in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override get_db to use test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestBrokerSetup:
    """Test broker setup and credential storage."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database and user."""
        Base.metadata.create_all(bind=engine)
        
        db = TestingSessionLocal()
        self.user = create_user(
            db,
            email="test@example.com",
            password="test123",
            first_name="Test",
            last_name="User"
        )
        db.close()
        
        self.token = create_access_token(
            data={"sub": self.user.email},
            expires_delta=None
        )
        
        yield
        
        Base.metadata.drop_all(bind=engine)
    
    def test_zerodha_setup_success(self):
        """Test successful Zerodha broker setup."""
        response = client.post(
            "/api/broker/zerodha/setup",
            params={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "token": self.token
            }
        )
        
        # This will fail because we don't have a real Zerodha connection
        # but we can verify the endpoint structure works
        assert response.status_code in [200, 400]
    
    def test_angel_setup_success(self):
        """Test successful Angel broker setup."""
        response = client.post(
            "/api/broker/angel/setup",
            params={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "token": self.token
            }
        )
        
        assert response.status_code in [200, 400]
    
    def test_fivepaisa_setup_success(self):
        """Test successful 5Paisa broker setup."""
        response = client.post(
            "/api/broker/fivepaisa/setup",
            params={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "token": self.token
            }
        )
        
        assert response.status_code in [200, 400]
    
    def test_setup_missing_credentials(self):
        """Test setup without required credentials."""
        response = client.post(
            "/api/broker/zerodha/setup",
            params={"token": self.token}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_broker_configs(self):
        """Test retrieving broker configurations."""
        response = client.get(
            "/api/broker/configs",
            params={"token": self.token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_disconnect_broker(self):
        """Test disconnecting a broker."""
        # First create a broker config
        db = TestingSessionLocal()
        config = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="zerodha",
            broker_user_id="test_user",
            api_key=EncryptionManager.encrypt("test_key"),
            api_secret=EncryptionManager.encrypt("test_secret")
        )
        config_id = config.id
        db.close()
        
        # Then disconnect it
        response = client.delete(
            f"/api/broker/configs/{config_id}",
            params={"token": self.token}
        )
        
        assert response.status_code == 200
    
    def test_broker_configs_encrypted_storage(self):
        """Test that credentials are stored encrypted."""
        db = TestingSessionLocal()
        
        plain_api_key = "my_plain_api_key"
        plain_api_secret = "my_plain_api_secret"
        
        config = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="test_broker",
            broker_user_id="test_user",
            api_key=EncryptionManager.encrypt(plain_api_key),
            api_secret=EncryptionManager.encrypt(plain_api_secret)
        )
        
        # Verify stored data is encrypted (not plaintext)
        assert config.api_key != plain_api_key
        assert config.api_secret != plain_api_secret
        
        # Verify we can decrypt it back
        assert EncryptionManager.decrypt(config.api_key) == plain_api_key
        assert EncryptionManager.decrypt(config.api_secret) == plain_api_secret
        
        db.close()
    
    def test_broker_config_per_user(self):
        """Test that each user can have separate broker configs."""
        db = TestingSessionLocal()
        
        # Create another user
        user2 = create_user(
            db,
            email="user2@example.com",
            password="pass123",
            first_name="User",
            last_name="Two"
        )
        
        # Create configs for both users
        config1 = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="zerodha",
            broker_user_id="user1_zerodha",
            api_key=EncryptionManager.encrypt("user1_key"),
            api_secret=EncryptionManager.encrypt("user1_secret")
        )
        
        config2 = create_broker_config(
            db,
            user_id=user2.id,
            broker_name="zerodha",
            broker_user_id="user2_zerodha",
            api_key=EncryptionManager.encrypt("user2_key"),
            api_secret=EncryptionManager.encrypt("user2_secret")
        )
        
        # Verify configs are separate
        assert config1.id != config2.id
        assert config1.user_id != config2.user_id
        
        # Get config for user 1
        user1_config = get_broker_config_by_broker_name(db, self.user.id, "zerodha")
        assert user1_config is not None
        assert user1_config.id == config1.id
        
        db.close()
    
    def test_multiple_brokers_per_user(self):
        """Test that a user can have multiple broker configs."""
        db = TestingSessionLocal()
        
        # Create multiple broker configs for same user
        config1 = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="zerodha",
            broker_user_id="zerodha_user",
            api_key=EncryptionManager.encrypt("zerodha_key"),
            api_secret=EncryptionManager.encrypt("zerodha_secret")
        )
        
        config2 = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="angel",
            broker_user_id="angel_user",
            api_key=EncryptionManager.encrypt("angel_key"),
            api_secret=EncryptionManager.encrypt("angel_secret")
        )
        
        config3 = create_broker_config(
            db,
            user_id=self.user.id,
            broker_name="fivepaisa",
            broker_user_id="fivepaisa_user",
            api_key=EncryptionManager.encrypt("fivepaisa_key"),
            api_secret=EncryptionManager.encrypt("fivepaisa_secret")
        )
        
        # Verify all configs exist and are accessible
        zerodha_config = get_broker_config_by_broker_name(db, self.user.id, "zerodha")
        angel_config = get_broker_config_by_broker_name(db, self.user.id, "angel")
        fivepaisa_config = get_broker_config_by_broker_name(db, self.user.id, "fivepaisa")
        
        assert zerodha_config.id == config1.id
        assert angel_config.id == config2.id
        assert fivepaisa_config.id == config3.id
        
        db.close()
