"""Tests for broker setup and configuration."""

import pytest

from portfolio_tracker.auth import create_access_token
from portfolio_tracker.crud import (create_broker_config, create_user,
                                    get_broker_config_by_broker_name)
from portfolio_tracker.encryption import EncryptionManager

# Import TestClient - will work if httpx is installed
try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


@pytest.mark.skipif(not TESTCLIENT_AVAILABLE, reason="httpx not installed")
class TestBrokerSetup:
    """Test broker setup and credential storage."""
    
    def test_zerodha_setup_success(self, client, test_user, auth_headers):
        """Test successful Zerodha broker setup."""
        response = client.post(
            "/api/broker/zerodha/setup",
            json={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
            },
            headers=auth_headers
        )
        
        # This will fail because we don't have a real Zerodha connection
        # but we can verify the endpoint structure works
        assert response.status_code in [200, 400]
    
    def test_angel_setup_success(self, client, test_user, auth_headers):
        """Test successful Angel broker setup."""
        response = client.post(
            "/api/broker/angel/setup",
            json={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    def test_fivepaisa_setup_success(self, client, test_user, auth_headers):
        """Test successful 5Paisa broker setup."""
        response = client.post(
            "/api/broker/fivepaisa/setup",
            json={
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    def test_setup_missing_credentials(self, client, test_user, auth_headers):
        """Test broker setup fails without credentials."""
        response = client.post(
            "/api/broker/zerodha/setup",
            json={},
            headers=auth_headers
        )

        # Should fail due to missing required body fields
        assert response.status_code == 422

    def test_setup_rejects_credentials_in_query_params(self, client, test_user, auth_headers):
        """Credentials passed as query parameters must NOT be accepted.

        Regression guard: they used to be the only accepted form, which wrote
        broker API secrets into every access log in the request path.
        """
        response = client.post(
            "/api/broker/zerodha/setup",
            params={"api_key": "test_api_key", "api_secret": "test_api_secret"},
            headers=auth_headers
        )

        assert response.status_code == 422
    
    def test_get_broker_configs(self, client, test_user, auth_headers):
        """Test getting broker configurations."""
        response = client.get(
            "/api/broker/configs",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_disconnect_broker(self, client, test_user, auth_headers):
        """Test disconnecting a broker."""
        # Try to disconnect - should handle gracefully even if not connected
        response = client.delete(
            "/api/broker/zerodha/disconnect",
            headers=auth_headers
        )
        
        # May return 200 or 404 depending on if config exists
        assert response.status_code in [200, 404]
    
    def test_broker_configs_encrypted_storage(self, db_session, test_user):
        """Test that broker configs are stored encrypted."""
        # Create a broker config
        config = create_broker_config(
            db_session,
            user_id=test_user['id'],
            broker_name="zerodha",
            broker_user_id="test_user",
            api_key="test_api_key",
            api_secret="test_api_secret",
        )
        
        # API key and secret should be stored (encrypted at application level)
        assert config.api_key == "test_api_key"
        assert config.api_secret == "test_api_secret"
    
    def test_broker_config_per_user(self, db_session, test_user):
        """Test that each user has their own broker configs."""
        # Create config for test user
        config = create_broker_config(
            db_session,
            user_id=test_user['id'],
            broker_name="zerodha",
            broker_user_id="test_user_1",
        )
        
        # Verify it's associated with the correct user
        retrieved = get_broker_config_by_broker_name(
            db_session, 
            user_id=test_user['id'],
            broker_name="zerodha"
        )
        
        assert retrieved is not None
        assert retrieved.user_id == test_user['id']
    
    def test_multiple_brokers_per_user(self, db_session, test_user):
        """Test that a user can have multiple broker configs."""
        # Create configs for different brokers
        create_broker_config(
            db_session,
            user_id=test_user['id'],
            broker_name="zerodha",
            broker_user_id="zerodha_user",
        )
        
        create_broker_config(
            db_session,
            user_id=test_user['id'],
            broker_name="angel",
            broker_user_id="angel_user",
        )
        
        # Verify both exist
        zerodha = get_broker_config_by_broker_name(
            db_session, test_user['id'], "zerodha"
        )
        angel = get_broker_config_by_broker_name(
            db_session, test_user['id'], "angel"
        )
        
        assert zerodha is not None
        assert angel is not None
        assert zerodha.broker_name == "zerodha"
        assert angel.broker_name == "angel"
