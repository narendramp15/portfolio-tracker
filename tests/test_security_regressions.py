"""Regression tests for the security fixes applied to the audit's Critical findings.

Each test corresponds to a specific defect that shipped. They are written so
that reverting the fix fails the test, rather than merely exercising the happy
path.
"""

import hashlib
import hmac

import pytest

from portfolio_tracker.auth import create_access_token

try:
    from fastapi.testclient import TestClient  # noqa: F401
    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TESTCLIENT_AVAILABLE, reason="httpx not installed")

SENSITIVE_PARAM_NAMES = {
    "api_key", "api_secret", "encryption_key", "password", "access_token",
    "client_id", "request_token", "signature", "payment_id", "token",
    "user_key",
}


# ---------------------------------------------------------------------------
# Bearer tokens must not be accepted from the query string
# ---------------------------------------------------------------------------

class TestTokenNotAcceptedInQueryString:
    """A 30-day JWT in a query parameter lands in every access log en route."""

    def test_query_param_token_is_rejected(self, client, test_user):
        token = create_access_token(data={"sub": test_user["email"]}, expires_delta=None)

        response = client.get("/api/auth/me", params={"token": token})

        assert response.status_code == 401

    def test_authorization_header_still_works(self, client, test_user, auth_headers):
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    def test_no_route_declares_a_credential_as_a_query_parameter(self):
        """Structural guard covering the endpoints no test calls directly."""
        from portfolio_tracker.main import fastapi_app

        offenders = []
        for route in fastapi_app.routes:
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            for param in dependant.query_params:
                if param.name in SENSITIVE_PARAM_NAMES:
                    offenders.append(f"{getattr(route, 'path', '?')} -> {param.name}")

        assert not offenders, f"credentials declared as query parameters: {offenders}"


# ---------------------------------------------------------------------------
# The diagnostic endpoint that published the database's location
# ---------------------------------------------------------------------------

def test_health_db_endpoint_is_gone(client):
    response = client.get("/health/db")
    assert response.status_code == 404


def test_plain_health_endpoint_still_works(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Payment verification must be bound to the payer and the price
# ---------------------------------------------------------------------------

def _signed(order_id: str, payment_id: str, secret: str) -> str:
    message = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class TestVerifyPaymentBinding:

    ENDPOINT = "/api/billing/verify-payment"

    def _stub_gateway(self, monkeypatch, order):
        """Point the endpoint at a fake Razorpay that returns ``order``."""
        from portfolio_tracker.routers import billing

        class _Orders:
            def fetch(self, order_id):
                return order

        class _Client:
            order = _Orders()

        monkeypatch.setattr(billing, "RAZORPAY_KEY_SECRET", "test_secret")
        monkeypatch.setattr(billing, "_razorpay_client", lambda: _Client())

    def test_query_parameters_are_no_longer_accepted(self, client, auth_headers):
        response = client.post(
            self.ENDPOINT,
            params={"payment_id": "pay_x", "order_id": "order_x", "signature": "sig"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_bad_signature_is_rejected(self, client, auth_headers, monkeypatch):
        from portfolio_tracker.routers import billing

        monkeypatch.setattr(billing, "RAZORPAY_KEY_SECRET", "test_secret")

        response = client.post(
            self.ENDPOINT,
            json={"payment_id": "pay_x", "order_id": "order_x", "signature": "not-the-hmac"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_valid_signature_for_another_users_order_is_rejected(
        self, client, test_user, auth_headers, monkeypatch
    ):
        """The core bug: a real signature used to be sufficient on its own."""
        self._stub_gateway(monkeypatch, {
            "id": "order_x",
            "amount": 19900,
            "status": "paid",
            "notes": {"user_id": str(test_user["id"] + 9999)},
        })

        response = client.post(
            self.ENDPOINT,
            json={
                "payment_id": "pay_x",
                "order_id": "order_x",
                "signature": _signed("order_x", "pay_x", "test_secret"),
            },
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_underpaid_order_is_rejected(self, client, test_user, auth_headers, monkeypatch):
        self._stub_gateway(monkeypatch, {
            "id": "order_x",
            "amount": 100,  # 1 rupee instead of 199
            "status": "paid",
            "notes": {"user_id": str(test_user["id"])},
        })

        response = client.post(
            self.ENDPOINT,
            json={
                "payment_id": "pay_x",
                "order_id": "order_x",
                "signature": _signed("order_x", "pay_x", "test_secret"),
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "amount" in response.json()["detail"].lower()

    def test_unpaid_order_is_rejected(self, client, test_user, auth_headers, monkeypatch):
        self._stub_gateway(monkeypatch, {
            "id": "order_x",
            "amount": 19900,
            "status": "created",
            "notes": {"user_id": str(test_user["id"])},
        })

        response = client.post(
            self.ENDPOINT,
            json={
                "payment_id": "pay_x",
                "order_id": "order_x",
                "signature": _signed("order_x", "pay_x", "test_secret"),
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_valid_payment_grants_pro_exactly_once(
        self, client, db_session, test_user, auth_headers, monkeypatch
    ):
        from portfolio_tracker.models import ProcessedPaymentModel, UserModel

        self._stub_gateway(monkeypatch, {
            "id": "order_x",
            "amount": 19900,
            "status": "paid",
            "notes": {"user_id": str(test_user["id"])},
        })
        payload = {
            "payment_id": "pay_x",
            "order_id": "order_x",
            "signature": _signed("order_x", "pay_x", "test_secret"),
        }

        first = client.post(self.ENDPOINT, json=payload, headers=auth_headers)
        assert first.status_code == 200, first.text
        assert first.json()["tier"] == "pro"

        # Replaying the same payment must not extend the subscription again.
        second = client.post(self.ENDPOINT, json=payload, headers=auth_headers)
        assert second.status_code == 409

        db_session.expire_all()
        user = db_session.query(UserModel).filter(UserModel.id == test_user["id"]).one()
        assert user.subscription_tier == "pro"

        recorded = db_session.query(ProcessedPaymentModel).filter(
            ProcessedPaymentModel.payment_id == "pay_x"
        ).all()
        assert len(recorded) == 1


# ---------------------------------------------------------------------------
# The webhook must fail closed
# ---------------------------------------------------------------------------

class TestWebhookFailsClosed:

    ENDPOINT = "/api/billing/webhook"

    def test_unconfigured_secret_disables_the_endpoint(self, client, monkeypatch):
        """It used to skip verification entirely, making this an open grant API."""
        from portfolio_tracker.routers import billing

        monkeypatch.setattr(billing, "RAZORPAY_WEBHOOK_SECRET", "")

        response = client.post(
            self.ENDPOINT,
            json={"event": "subscription.activated", "payload": {}},
        )

        assert response.status_code == 503

    def test_invalid_signature_is_rejected(self, client, monkeypatch):
        from portfolio_tracker.routers import billing

        monkeypatch.setattr(billing, "RAZORPAY_WEBHOOK_SECRET", "hook_secret")

        response = client.post(
            self.ENDPOINT,
            json={"event": "subscription.activated", "payload": {}},
            headers={"x-razorpay-signature": "wrong"},
        )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Startup refuses to run a deployment without real secrets
# ---------------------------------------------------------------------------

class TestStartupValidation:

    def _settings(self, monkeypatch, **env):
        """Build a Settings instance that sees exactly ``env``.

        ``Settings.__init__`` calls ``load_dotenv`` outside test mode, and the
        repo's own .env supplies both SECRET_KEY and ENCRYPTION_KEY — so without
        stubbing it these tests would silently assert against the developer's
        local secrets instead of an empty environment.
        """
        from portfolio_tracker import config as config_module

        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **k: False)
        for key in ("TESTING", "ENVIRONMENT", "SECRET_KEY", "ENCRYPTION_KEY"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return config_module.Settings()

    def test_production_without_secret_key_refuses_to_start(self, monkeypatch):
        from portfolio_tracker.config import ConfigurationError, validate_or_die

        cfg = self._settings(monkeypatch, ENVIRONMENT="production", ENCRYPTION_KEY="x" * 44)

        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            validate_or_die(cfg)

    def test_production_with_the_dev_default_refuses_to_start(self, monkeypatch):
        from portfolio_tracker.config import (DEV_SECRET_KEY_DEFAULT,
                                              ConfigurationError,
                                              validate_or_die)

        cfg = self._settings(
            monkeypatch,
            ENVIRONMENT="production",
            SECRET_KEY=DEV_SECRET_KEY_DEFAULT,
            ENCRYPTION_KEY="x" * 44,
        )

        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            validate_or_die(cfg)

    def test_production_without_encryption_key_refuses_to_start(self, monkeypatch):
        from portfolio_tracker.config import ConfigurationError, validate_or_die

        cfg = self._settings(monkeypatch, ENVIRONMENT="production", SECRET_KEY="s" * 48)

        with pytest.raises(ConfigurationError, match="ENCRYPTION_KEY"):
            validate_or_die(cfg)

    def test_production_with_real_secrets_starts(self, monkeypatch):
        from portfolio_tracker.config import validate_or_die

        cfg = self._settings(
            monkeypatch,
            ENVIRONMENT="production",
            SECRET_KEY="s" * 48,
            ENCRYPTION_KEY="x" * 44,
        )

        validate_or_die(cfg)  # must not raise

    def test_development_is_left_alone(self, monkeypatch):
        from portfolio_tracker.config import validate_or_die

        cfg = self._settings(monkeypatch, ENVIRONMENT="development")

        validate_or_die(cfg)  # must not raise


# ---------------------------------------------------------------------------
# Encryption failures are loud
# ---------------------------------------------------------------------------

class TestEncryptionFailsLoud:

    def test_missing_key_raises_outside_tests(self, monkeypatch):
        """A generated fallback key silently orphans every stored credential."""
        from portfolio_tracker import encryption
        from portfolio_tracker.encryption import (EncryptionKeyMissing,
                                                  EncryptionManager)

        monkeypatch.setattr(EncryptionManager, "_cipher", None)
        monkeypatch.setattr(encryption.settings, "_testing", False, raising=False)
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        try:
            with pytest.raises(EncryptionKeyMissing):
                EncryptionManager.encrypt("some-broker-secret")
        finally:
            EncryptionManager.reset_cipher()

    def test_malformed_key_raises_rather_than_regenerating(self, monkeypatch):
        from portfolio_tracker import encryption
        from portfolio_tracker.encryption import (EncryptionKeyMissing,
                                                  EncryptionManager)

        monkeypatch.setattr(EncryptionManager, "_cipher", None)
        monkeypatch.setattr(encryption.settings, "_testing", False, raising=False)
        monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-fernet-key")

        try:
            with pytest.raises(EncryptionKeyMissing):
                EncryptionManager.encrypt("some-broker-secret")
        finally:
            EncryptionManager.reset_cipher()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:

    def test_headers_are_present_on_a_normal_response(self, client):
        response = client.get("/health")

        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        assert "content-security-policy" in response.headers

    def test_docs_are_exempt_from_the_csp(self, client):
        """A strict CSP blanks out Swagger's CDN-hosted assets."""
        response = client.get("/docs")

        assert "content-security-policy" not in response.headers


# ---------------------------------------------------------------------------
# The reset-password endpoint is throttled
# ---------------------------------------------------------------------------

def test_reset_password_is_rate_limited(client):
    """Without this, the 32-byte reset token can be brute-forced for free."""
    from portfolio_tracker.rate_limit import password_reset_rate_limiter

    password_reset_rate_limiter._hits.clear()
    payload = {"token": "definitely-not-a-real-token", "new_password": "NewPassw0rd!"}

    try:
        statuses = [
            client.post("/api/auth/reset-password", json=payload).status_code
            for _ in range(password_reset_rate_limiter.max_requests + 1)
        ]
        assert statuses[-1] == 429, statuses
    finally:
        password_reset_rate_limiter._hits.clear()
