# auth.py - Authentication endpoints (ASYNC for PostgreSQL)
"""
Authentication endpoints (ASYNC for PostgreSQL)
Matches frontend expectations:
- POST /api/v1/auth/register - Create new user account
- POST /api/v1/auth/login - Login and get session
- GET /api/v1/auth/me - Get current user
- POST /api/v1/auth/logout - Logout and clear session
- Username-based authentication (not email!)
"""

import logging
import secrets
import traceback
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_password_hash, verify_password
from app.db.models import User, UserSession
from app.schemas.auth import SessionResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """
    Register a new user (ASYNC)

    Frontend sends POST request to /api/auth/register with:
    ```json
    {
        "username": "johndoe",
        "email": "user@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe"  # Optional
    }
    ```

    Returns:
    - 201: User created successfully
    - 400: Username already taken
    - 400: Email already taken
    """
    # Check if username already exists
    username = await db.execute(select(User).where(User.username == user_data.username))
    db_username = username.scalar_one_or_none()

    if db_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Check if email already exists
    email = await db.execute(select(User).where(
            func.lower(User.email) == func.lower(user_data.email)
        ))
    db_email = email.scalar_one_or_none()

    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken"
        )

    # Hash password using Argon2
    hashed_password = get_password_hash(user_data.password)

    # Create new user (no role_id - removed)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Return success response matching frontend expectations
    return SessionResponse(
        success=True,
        username=new_user.username,
        session_token=None,  # No session token on registration - user must login separately
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Login user and create session (SESSION-BASED AUTH)

    Frontend sends POST request to /api/auth/login with:
    ```json
    {
        "username": "johndoe",
        "password": "SecurePass123!"
    }
    ```

    Returns:
    - 200: Login successful with session token
    - 401: Invalid credentials
    - 403: Account inactive
    """
    try:
        # Find user by username
        result = await db.execute(
            select(User).where(User.username == credentials.username)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        # Generate secure session token
        session_token = secrets.token_urlsafe(32)

        # Create session in database
        now = datetime.now()
        expires_at = now + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
        new_session = UserSession(
            session_token=session_token,
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        db.add(new_session)
        await db.commit()

        # Determine if we are in production
        is_production = settings.ENVIRONMENT == "production"

        # Set HTTP-only cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=is_production,                     # True on Railway, False locally
            samesite="none" if is_production else "lax", # "none" on Railway, "lax" locally
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            path="/",
        )

        # Build user response (no role_id)
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return SessionResponse(
            success=True,
            username=user.username,
            session_token=session_token,
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        ) from e


# Dependency returns current authenticated user based on session token
async def get_current_user_from_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    Can be used in any endpoint that needs the current user
    """
    session_token = request.cookies.get("session_token")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Find valid session
    session_result = await db.execute(
        select(UserSession)
        .where(UserSession.session_token == session_token)
        .where(UserSession.expires_at > datetime.now())
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    # Find user
    user_result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# Endpoints that require authentication can use this dependency to get the current user
@router.get("/me", response_model=UserResponse)
async def get_current_user_endpoint(
    current_user: User = Depends(get_current_user_from_session)
) -> UserResponse:
    """
    Get current authenticated user
    Returns 401 if not authenticated
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Logout user - invalidate session and clear cookie
    """
    session_token = request.cookies.get("session_token")

    if session_token:
        # Delete session from database
        result = await db.execute(
            select(UserSession).where(UserSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()

        if session:
            await db.delete(session)
            await db.commit()

        # Clear cookie
        response.delete_cookie("session_token", path="/")

    return {
        "success": True,
        "message": "Logged out successfully"
    }


