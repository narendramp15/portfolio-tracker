"""Broker configuration persistence (encrypted credentials, sync timestamps)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from portfolio_tracker.models import BrokerConfigModel


def get_broker_config(db: Session, config_id: int):
    """Get broker config by ID."""
    return db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()


def get_broker_configs_by_user(db: Session, user_id: int):
    """Get all broker configs for a user."""
    return db.query(BrokerConfigModel).filter(BrokerConfigModel.user_id == user_id).all()


def get_broker_config_by_broker_name(db: Session, user_id: int, broker_name: str):
    """Get broker config by broker name and user."""
    return db.query(BrokerConfigModel).filter(
        BrokerConfigModel.user_id == user_id,
        BrokerConfigModel.broker_name == broker_name
    ).first()


def create_broker_config(
    db: Session,
    user_id: int,
    broker_name: str,
    broker_user_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    extra_config: str | None = None,
    consent_given: bool = False,
):
    """Create a new broker configuration."""
    config = BrokerConfigModel(
        user_id=user_id,
        broker_name=broker_name,
        broker_user_id=broker_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        api_key=api_key,
        api_secret=api_secret,
        extra_config=extra_config,
        consent_given=consent_given,
        consent_timestamp=datetime.now(timezone.utc) if consent_given else None,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_broker_config(
    db: Session,
    config_id: int,
    access_token: str | None = None,
    refresh_token: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    broker_user_id: str | None = None,
    extra_config: str | None = None,
    last_synced=None,
    consent_given: bool | None = None,
):
    """Update broker configuration tokens."""
    config = db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()
    if not config:
        return None

    if access_token:
        config.access_token = access_token
    if refresh_token:
        config.refresh_token = refresh_token
    if api_key:
        config.api_key = api_key
    if api_secret:
        config.api_secret = api_secret
    if broker_user_id:
        config.broker_user_id = broker_user_id
    if extra_config:
        config.extra_config = extra_config
    # Only stamp last_synced when the caller actually performed a sync. Credential
    # saves / OAuth token stores pass last_synced=None and must NOT be marked
    # synced, otherwise the UI shows a fresh sync time for a never-synced broker.
    if last_synced is not None:
        config.last_synced = last_synced
    if consent_given is not None:
        config.consent_given = consent_given
        config.consent_timestamp = datetime.now(timezone.utc) if consent_given else None

    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def delete_broker_config(db: Session, config_id: int):
    """Delete broker configuration."""
    config = db.query(BrokerConfigModel).filter(BrokerConfigModel.id == config_id).first()
    if config:
        db.delete(config)
        db.commit()
    return config
