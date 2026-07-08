"""User persistence."""

from typing import Optional

from sqlalchemy.orm import Session

from portfolio_tracker.models import UserModel


def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Get a user by email."""
    return db.query(UserModel).filter(UserModel.email == email).first()


def create_user(
    db: Session,
    email: str,
    username: Optional[str] = None,
    hashed_password: Optional[str] = None,
    full_name: Optional[str] = None,
    is_active: bool = True,
    # Legacy parameters for backwards compatibility with tests
    password: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
):
    """
    Create a new user.

    Supports two calling conventions:
    1. New: (email, username, hashed_password, full_name)
    2. Legacy: (email, password, first_name, last_name) - auto-hashes password
    """
    # Imported lazily: auth pulls in passlib/jwt, which repositories must not
    # require at import time.
    from portfolio_tracker.auth import hash_password

    # Handle legacy parameters
    if password and not hashed_password:
        hashed_password = hash_password(password)

    if not username:
        # Generate username from email if not provided
        username = email.split("@")[0]

    if not full_name and (first_name or last_name):
        # Build full_name from first_name/last_name
        full_name = f"{first_name or ''} {last_name or ''}".strip()

    user = UserModel(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
