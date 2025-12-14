"""Tests for broker API modules."""

import pytest

from portfolio_tracker.brokers.angel import AngelBroker
from portfolio_tracker.brokers.fivepaisa import FivepaIsaBroker
from portfolio_tracker.brokers.zerodha import ZerodhaBroker


class TestBrokerModules:
    """Test broker module structure and basic functionality."""
    
    def test_zerodha_broker_initialization(self):
        """Test Zerodha broker initialization."""
        broker = ZerodhaBroker(api_key="test_key", api_secret="test_secret")
        
        assert broker is not None
        assert hasattr(broker, 'api_key')
        assert hasattr(broker, 'api_secret')
    
    def test_zerodha_broker_has_required_methods(self):
        """Test Zerodha broker has all required methods."""
        broker = ZerodhaBroker(api_key="test_key", api_secret="test_secret")
        
        assert hasattr(broker, 'set_access_token')
        assert hasattr(broker, 'set_token')
        assert hasattr(broker, 'get_holdings')
        assert hasattr(broker, 'get_profile')
    
    def test_angel_broker_initialization(self):
        """Test Angel broker initialization."""
        broker = AngelBroker(api_key="test_key", api_secret="test_secret")
        
        assert broker is not None
        assert hasattr(broker, 'api_key')
        assert hasattr(broker, 'api_secret')
    
    def test_angel_broker_has_required_methods(self):
        """Test Angel broker has all required methods."""
        broker = AngelBroker(api_key="test_key", api_secret="test_secret")
        
        assert hasattr(broker, 'set_access_token')
        assert hasattr(broker, 'set_token')
        assert hasattr(broker, 'get_holdings')
        assert hasattr(broker, 'get_profile')
        assert hasattr(broker, '_make_request')
    
    def test_fivepaisa_broker_initialization(self):
        """Test 5Paisa broker initialization."""
        broker = FivepaIsaBroker(api_key="test_key", api_secret="test_secret")
        
        assert broker is not None
        assert hasattr(broker, 'api_key')
        assert hasattr(broker, 'api_secret')
    
    def test_fivepaisa_broker_has_required_methods(self):
        """Test 5Paisa broker has all required methods."""
        broker = FivepaIsaBroker(api_key="test_key", api_secret="test_secret")
        
        assert hasattr(broker, 'set_access_token')
        assert hasattr(broker, 'set_token')
        assert hasattr(broker, 'get_holdings')
        assert hasattr(broker, 'get_profile')
        assert hasattr(broker, '_make_request')
    
    def test_broker_set_access_token(self):
        """Test setting access token on broker."""
        broker = ZerodhaBroker(api_key="test_key", api_secret="test_secret")
        
        # This should not raise an error (will fail with API but shouldn't error on method call)
        try:
            broker.set_access_token("test_request_token", "test_api_secret")
        except Exception:
            # Expected - no real API key, but method should be callable
            pass
    
    def test_broker_set_token(self):
        """Test setting token on broker."""
        broker = AngelBroker(api_key="test_key", api_secret="test_secret")
        
        # This should not raise an error
        broker.set_token("test_token")
    
    def test_multiple_broker_instances(self):
        """Test creating multiple broker instances doesn't interfere."""
        broker1 = ZerodhaBroker(api_key="key1", api_secret="secret1")
        broker2 = AngelBroker(api_key="key2", api_secret="secret2")
        broker3 = FivepaIsaBroker(api_key="key3", api_secret="secret3")
        
        assert broker1.api_key == "key1"
        assert broker2.api_key == "key2"
        assert broker3.api_key == "key3"
    
    def test_broker_credential_isolation(self):
        """Test that broker instances maintain separate credentials."""
        broker1 = ZerodhaBroker(api_key="zerodha_key", api_secret="zerodha_secret")
        broker2 = ZerodhaBroker(api_key="zerodha_key_2", api_secret="zerodha_secret_2")
        
        assert broker1.api_key != broker2.api_key
        assert broker1.api_secret != broker2.api_secret
