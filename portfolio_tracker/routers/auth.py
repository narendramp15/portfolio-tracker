"""Authentication API endpoints."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from portfolio_tracker import models, schemas
from portfolio_tracker.auth import (ACCESS_TOKEN_EXPIRE_MINUTES,
                                    create_access_token, decode_access_token,
                                    hash_password, verify_password)
from portfolio_tracker.config import settings
from portfolio_tracker.database import get_db
from portfolio_tracker.deps import get_current_user
from portfolio_tracker.rate_limit import (auth_rate_limiter,
                                          password_reset_rate_limiter,
                                          register_rate_limiter)
from portfolio_tracker.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize OAuth client using centralized config
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


@router.post("/register", response_model=schemas.Token)
async def register(request: Request, user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    register_rate_limiter.check(request)
    logger.info(f"Registration attempt for email: {user_data.email}, username: {user_data.username}")
    
    # Check if user already exists
    existing_user = db.query(models.UserModel).filter(
        (models.UserModel.email == user_data.email) |
        (models.UserModel.username == user_data.username)
    ).first()
    
    if existing_user:
        logger.warning(f"Registration failed - email/username already exists: {user_data.email}/{user_data.username}")
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
    
    logger.info(f"User registered successfully: {user.email} (ID: {user.id})")
    
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
async def login(request: Request, user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    auth_rate_limiter.check(request)
    logger.info(f"Login attempt for email: {user_data.email}")
    
    # Find user by email
    user = db.query(models.UserModel).filter(
        models.UserModel.email == user_data.email
    ).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        logger.warning(f"Login failed - invalid credentials for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        logger.warning(f"Login failed - inactive account: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"Login successful for: {user.email} (ID: {user.id})")
    
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
async def get_current_user_endpoint(current_user: models.UserModel = Depends(get_current_user)):
    """Get current authenticated user."""
    logger.debug(f"User info requested: {current_user.email}")
    return current_user


@router.post("/forgot-password", response_model=schemas.MessageResponse)
async def forgot_password(
    http_request: Request,
    request: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset token."""
    password_reset_rate_limiter.check(http_request)

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
    
    # Send password-reset email (falls back to console log if SMTP not configured)
    send_password_reset_email(user.email, token, settings.FRONTEND_URL)
    logger.info("Password reset requested for user_id=%s", user.id)
    
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


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login."""
    logger.info(f"Google OAuth login initiated - Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    logger.info("Google OAuth callback received")
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            logger.error("Failed to get user info from Google token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google"
            )
        
        email = user_info.get('email')
        full_name = user_info.get('name', '')
        google_id = user_info.get('sub')  # Google's unique user ID
        
        logger.info(f"Google OAuth user info retrieved - Email: {email}, Name: {full_name}, Google ID: {google_id}")
        
        if not email:
            logger.error("Email not provided by Google")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Check if user exists
        user = db.query(models.UserModel).filter(
            models.UserModel.email == email
        ).first()
        
        if not user:
            logger.info(f"Creating new user via Google OAuth: {email}")
            # Create new user with Google OAuth
            # Generate a random username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while db.query(models.UserModel).filter(
                models.UserModel.username == username
            ).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = models.UserModel(
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=hash_password(secrets.token_urlsafe(32)),  # Random password for OAuth users
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Google OAuth user created successfully: {email} (ID: {user.id}, Username: {username})")
        else:
            logger.info(f"Existing user logged in via Google OAuth: {email} (ID: {user.id})")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        logger.info(f"Google OAuth token created, redirecting to: {settings.FRONTEND_URL}/auth/callback")
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        )
        
    except Exception as e:
        # Log the actual error for debugging
        logger.error(f"Google OAuth error: {type(e).__name__}: {str(e)}", exc_info=True)
        
        # Redirect to login with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=google_auth_failed"
        )
