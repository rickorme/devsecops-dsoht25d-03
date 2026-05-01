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

import secrets
from datetime import datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.db import get_db
from app.core.logger import logger
from app.core.security import get_password_hash, verify_password
from app.db.models import User, UserSession
from app.schemas.auth import SessionResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,  # Added so we can extract source.ip
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:

    # Extract client IP for ECS compliance
    client_ip = request.client.host if request.client else "unknown"

    # 1. Initialize ECS Context for the entire request
    # These fields will be automatically attached to every log in this function
    log = logger.bind(**{
        "event.category": ["iam", "authentication"],
        "event.action": "user_registration",
        "user.name": user_data.username,
        "user.email": user_data.email,
        "source.ip": client_ip
    })

    error_detail = None

    # 2. Perform all validations (The Guard Clauses)
    username_exists = await db.execute(select(User).where(User.username == user_data.username))
    if username_exists.scalar_one_or_none():
        error_detail = "Username already taken"
    else:
        email_exists = await db.execute(select(User).where(func.lower(User.email) == func.lower(user_data.email)))
        if email_exists.scalar_one_or_none():
            error_detail = "Email already taken"

    # 3. The Single Error Exit Point
    if error_detail:
        # Append failure outcome and error details to the existing context
        log.bind(**{
            "event.outcome": "failure",
            "error.message": error_detail
        }).warning(f"Registration validation failed: {error_detail}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
        )

    # 4. The Happy Path Execution
    try:
        hashed_password = get_password_hash(user_data.password)
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

        # 5. The Single Success Exit Point
        # Append success outcome and the newly generated user ID
        log.bind(**{
            "event.outcome": "success",
            "user.id": str(new_user.id)
        }).info(f"User registration successful for {new_user.username}")

        return SessionResponse(
            success=True,
            username=new_user.username,
            session_token=None,
            user=UserResponse.model_validate(new_user)
        )

    except Exception as e:
        # 6. Catch unexpected DB/Hashing errors
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected server error during registration")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        ) from e

@router.post("/login", response_model=SessionResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:

    # Extract client IP for ECS compliance
    client_ip = request.client.host if request.client else "unknown"

    # 1. Initialize ECS Context
    log = logger.bind(**{
        "event.category": ["iam", "authentication"],
        "event.action": "login",
        "user.name": credentials.username,
        "source.ip": client_ip
    })

    error_detail = None
    error_status = status.HTTP_401_UNAUTHORIZED
    user = None

    try:
        # 2. Perform Validations (Guard Clauses)
        result = await db.execute(select(User).where(User.username == credentials.username))
        user = result.scalar_one_or_none()

        if not user:
            error_detail = "Invalid username or password"
        elif not verify_password(credentials.password, user.hashed_password):
            error_detail = "Invalid username or password"
        elif not user.is_active:
            error_detail = "Account is inactive"
            error_status = status.HTTP_403_FORBIDDEN

        # 3. The Single Error Exit Point
        if error_detail:
            log.bind(**{
                "event.outcome": "failure",
                "error.message": error_detail
            }).warning(f"Login failed: {error_detail}")

            raise HTTPException(
                status_code=error_status,
                detail=error_detail
            )

        # TELL MYPY: If we reach here, we guarantee 'user' is a valid User object.
        # This satisfies mypy without triggering Bandit's assert rule!
        user = cast(User, user)

        # 4. The Happy Path Execution
        session_token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires_at = now + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)

        new_session = UserSession(
            session_token=session_token,
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )

        db.add(new_session)
        await db.commit()

        # Cookie configuration for cross-domain auth
        is_production = settings.ENVIRONMENT == "production"
        custom_domain = settings.COOKIE_DOMAIN if is_production else None

        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=is_production,
            samesite="none" if is_production else "lax",
            domain=custom_domain,
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            path="/",
        )

        # Build user response
        user_response = UserResponse.model_validate(user)

        # 5. The Single Success Exit Point
        log.bind(**{
            "event.outcome": "success",
            "user.id": str(user.id),
            "user.email": user.email
        }).info(f"User login successful for {user.username}")

        return SessionResponse(
            success=True,
            username=user.username,
            session_token=session_token,
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        # 6. Catch unexpected server errors
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected server error during login")

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
        select(User).options(joinedload(User.role)).where(User.id == session.user_id)
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
        role=current_user.role.name if current_user.role else None,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:

    # Extract client IP
    client_ip = request.client.host if request.client else "unknown"

    # 1. Initialize ECS Context
    log = logger.bind(**{
        "event.category": ["iam", "authentication"],
        "event.action": "logout",
        "source.ip": client_ip
    })

    try:
        session_token = request.cookies.get("session_token")
        user_id_for_log = None

        if session_token:
            # Check for active session in DB
            result = await db.execute(
                select(UserSession).where(UserSession.session_token == session_token)
            )
            session = result.scalar_one_or_none()

            if session:
                user_id_for_log = str(session.user_id)
                await db.delete(session)
                await db.commit()

            # Clear cookie with matching domain logic
            is_production = settings.ENVIRONMENT == "production"
            custom_domain = settings.COOKIE_DOMAIN if is_production else None

            response.delete_cookie(
                "session_token",
                path="/",
                domain=custom_domain,
                secure=is_production,
                samesite="none" if is_production else "lax",
            )

        # 2. Append Success Outcome (add user_id if we found it)
        log_context = {"event.outcome": "success"}
        if user_id_for_log:
            log_context["user.id"] = user_id_for_log

        log.bind(**log_context).info("User logged out successfully")

        return {
            "success": True,
            "message": "Logged out successfully"
        }

    except Exception as e:
        # 3. Catch unexpected server errors
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected server error during logout")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed due to server error"
        ) from e


class RequireRole:
    """
    RBAC Dependency Factory
    Usage: @router.get("/admin", dependencies=[Depends(RequireRole(["admin", "superadmin"]))])
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user_from_session)) -> User:
        # Check if the user's role name exists in the allowed list
        if not current_user.role or current_user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to access this resource"
            )
        return current_user

