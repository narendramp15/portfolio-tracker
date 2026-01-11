"""Authentication API endpoints."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from portfolio_tracker import models, schemas
from portfolio_tracker.auth import (ACCESS_TOKEN_EXPIRE_MINUTES,
                                    create_access_token, decode_access_token,
                                    hash_password, verify_password)
from portfolio_tracker.database import get_db

router = APIRouter()


@router.post("/register", response_model=schemas.Token)
async def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(models.UserModel).filter(
        (models.UserModel.email == user_data.email) |
        (models.UserModel.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = models.UserModel(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
    }


@router.post("/login", response_model=schemas.Token)
async def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    # Find user by email
    user = db.query(models.UserModel).filter(
        models.UserModel.email == user_data.email
    ).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
    }


@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user(db: Session = Depends(get_db), token: str = None):
    """Get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    email = decode_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    user = db.query(models.UserModel).filter(
        models.UserModel.email == email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.post("/forgot-password", response_model=schemas.MessageResponse)
async def forgot_password(
    request: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset token."""
    # Find user by email
    user = db.query(models.UserModel).filter(
        models.UserModel.email == request.email
    ).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a reset token has been generated. Use it within 1 hour."}
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Invalidate any existing tokens for this user
    db.query(models.PasswordResetTokenModel).filter(
        models.PasswordResetTokenModel.user_id == user.id,
        models.PasswordResetTokenModel.used == False
    ).update({"used": True})
    
    # Create new reset token
    reset_token = models.PasswordResetTokenModel(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
        used=False
    )
    db.add(reset_token)
    db.commit()
    
    # In production, send email here
    # For now, just log the token (development only!)
    print(f"🔑 Password reset token for {user.email}: {token}")
    print(f"   Token expires at: {expires_at}")
    print(f"   Use this token in the reset password form within 1 hour.")
    
    return {"message": "If the email exists, a reset token has been generated. Use it within 1 hour."}


@router.post("/reset-password", response_model=schemas.MessageResponse)
async def reset_password(
    request: schemas.PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using a valid token."""
    # Find the reset token
    reset_token = db.query(models.PasswordResetTokenModel).filter(
        models.PasswordResetTokenModel.token == request.token,
        models.PasswordResetTokenModel.used == False
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired - handle timezone-aware/naive comparison
    now = datetime.now(timezone.utc)
    expires_at = reset_token.expires_at
    
    # Ensure both datetimes are timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if now > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Get the user
    user = db.query(models.UserModel).filter(
        models.UserModel.id == reset_token.user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = hash_password(request.new_password)
    
    # Mark token as used
    reset_token.used = True
    
    db.commit()
    
    return {"message": "Password has been reset successfully"}
