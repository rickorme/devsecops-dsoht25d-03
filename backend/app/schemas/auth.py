"""
Authentication schemas
Request and response models for registration, login, and user data
Updated to match frontend expectations: username-based login!
"""
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """
    Schema for user registration request from frontend

    Frontend sends (from RegisterPage.jsx):
    {
        "username": "johndoe",
        "password": "SecurePass123!"
        "full_name": "John Doe",  # Optional
        "email": "john.doe@example.com"
    }
    """
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=8, max_length=50, description="Password (min 8 characters)")
    full_name: str | None = Field(None, max_length=100, description="User's full name")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    """
    Schema for user login request from frontend

    Frontend sends (from LoginPage.jsx and auth.service.js):
    {
        "username": "johndoe",
        "password": "SecurePass123!"
    }

    Note: Frontend uses USERNAME, not email!
    """
    username: str = Field(..., description="Username")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """
    Schema for user data in API responses

    Note: Never includes password or hashed_password
    Email re-added as per frontend team request
    """
    id: int
    username: str
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    role: str | None

    @field_validator("role", mode="before")
    @classmethod
    def extract_role_name(cls, v: Any) -> str | None:
        # If SQLAlchemy hands us the Role object, explicitly cast the name to a string
        if hasattr(v, "name"):
            return str(v.name)

        # Use type narrowing: if it's already a string, Mypy now guarantees it's safe to return
        if isinstance(v, str):
            return v

        # Fallback for None (or any other unexpected type)
        return None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """
    Schema for JWT token response after successful login

    Example response:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class SessionResponse(BaseModel):
    """
    Schema for session-based authentication response
    Frontend team requested sessions as alternative to JWT

    Example response:
    {
        "success": true,
        "username": "johndoe",
        "session_token": "abc123...",
        "user": {...}
    }
    """
    success: bool = Field(default=True)
    username: str
    user: UserResponse | None = Field(None, description="User data if requested")


class TokenData(BaseModel):
    """
    Schema for decoded token data
    Used internally for token validation
    """
    username: str | None = None
