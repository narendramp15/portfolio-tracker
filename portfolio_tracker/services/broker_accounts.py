"""Broker account credential management.

Owns the encrypt/decrypt boundary for broker credentials: everything above
this module works with plaintext credentials, everything below (the
``broker_configs`` repository / DB) only ever sees ciphertext.

Raises ``ValueError`` for domain errors; routers translate to HTTP statuses.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from portfolio_tracker.encryption import EncryptionManager
from portfolio_tracker.models import BrokerConfigModel, UserModel
from portfolio_tracker.repositories import broker_configs
from portfolio_tracker.services.entitlements import check_broker_limit

logger = logging.getLogger(__name__)


def get_config_or_error(
    db: Session,
    user_id: int,
    broker_name: str,
    *,
    missing_msg: str,
    require_token: bool = False,
    unauthorized_msg: Optional[str] = None,
) -> BrokerConfigModel:
    """Fetch a user's broker config, raising ``ValueError`` when absent.

    ``missing_msg`` / ``unauthorized_msg`` are caller-supplied so the exact
    user-facing error strings of each endpoint are preserved.
    """
    config = broker_configs.get_broker_config_by_broker_name(db, user_id, broker_name)
    if not config:
        raise ValueError(missing_msg)
    if require_token and not config.access_token:
        raise ValueError(unauthorized_msg or missing_msg)
    return config


def decrypt_credentials(config: BrokerConfigModel) -> tuple[str, str, str]:
    """Return (api_key, api_secret, access_token) in plaintext ('' when unset)."""
    api_key = EncryptionManager.decrypt(config.api_key or "")
    api_secret = EncryptionManager.decrypt(config.api_secret or "")
    access_token = EncryptionManager.decrypt(config.access_token) if config.access_token else ""
    return api_key, api_secret, access_token


def load_extra_config(config: BrokerConfigModel) -> dict:
    """Decrypt the JSON blob of broker-specific extras (5Paisa app credentials)."""
    if not config.extra_config:
        return {}
    try:
        return json.loads(EncryptionManager.decrypt(config.extra_config))
    except Exception as e:
        logger.warning(f"Failed to decrypt extra_config: {e}")
        return {}


def save_credentials(
    db: Session,
    user: UserModel,
    broker_name: str,
    *,
    broker_user_id: str = "",
    consent_given: bool = False,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    access_token: Optional[str] = None,
    extra_config: Optional[dict] = None,
) -> BrokerConfigModel:
    """Encrypt and persist credentials, creating or updating the user's config.

    The plan broker limit is enforced only for NEW connections, matching the
    original per-endpoint behavior.
    """
    enc = EncryptionManager.encrypt
    encrypted_extra = enc(json.dumps(extra_config)) if extra_config is not None else None

    config = broker_configs.get_broker_config_by_broker_name(db, user.id, broker_name)
    if config:
        return broker_configs.update_broker_config(
            db,
            config.id,
            api_key=enc(api_key) if api_key is not None else None,
            api_secret=enc(api_secret) if api_secret is not None else None,
            access_token=enc(access_token) if access_token is not None else None,
            extra_config=encrypted_extra,
            broker_user_id=broker_user_id or None,
            consent_given=consent_given,
        )

    check_broker_limit(user, db)
    return broker_configs.create_broker_config(
        db,
        user_id=user.id,
        broker_name=broker_name,
        broker_user_id=broker_user_id,
        api_key=enc(api_key) if api_key is not None else None,
        api_secret=enc(api_secret) if api_secret is not None else None,
        access_token=enc(access_token) if access_token is not None else None,
        extra_config=encrypted_extra,
        consent_given=consent_given,
    )


def store_access_token(
    db: Session,
    config: BrokerConfigModel,
    access_token: str,
    *,
    broker_user_id: Optional[str] = None,
    last_synced=None,
) -> BrokerConfigModel:
    """Encrypt and save a freshly obtained OAuth access token."""
    return broker_configs.update_broker_config(
        db,
        config.id,
        access_token=EncryptionManager.encrypt(access_token),
        broker_user_id=broker_user_id,
        last_synced=last_synced,
    )
