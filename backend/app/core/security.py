"""
Security utilities for authentication
Handles password hashing, JWT tokens, and session management
"""
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings

# Password hasher using Argon2 (more secure than bcrypt)
pwd_context = PasswordHash((Argon2Hasher(),))


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: The password to verify (from user input)
        hashed_password: The stored hash from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string

    Example:
        hashed = get_password_hash("MySecurePassword123!")
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in token (usually {"sub": username})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        token = create_access_token({"sub": "johndoe"})
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Any:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload dict

    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_session_token() -> str:
    """
    Create a secure random session token

    Returns:
        64-character hexadecimal session token

    Example:
        session_id = create_session_token()
        # Returns: "a3f2b9e1c5d7..." (64 chars)
    """
    return secrets.token_hex(32)


def create_session_expiry(hours: int = 24) -> datetime:
    """
    Create session expiration datetime

    Args:
        hours: Number of hours until session expires (default 24)

    Returns:
        Datetime object for session expiration
    """
    return datetime.now(UTC) + timedelta(hours=hours)


# ============================================================================
# SESSION TOEEN SIGNING
# ============================================================================

def sign_session_token(session_token: str) -> str:
    """Cryptographically signs the session token."""
    # Uses your app's secret key to create an HMAC signature
    signer = TimestampSigner(settings.SECRET_KEY)

    # Returns a string like: "raw_token.Timestamp.CryptographicSignature"
    return signer.sign(session_token).decode("utf-8")

def verify_session_token(signed_token: str, max_age: int = 604800) -> str | None:
    """
    Verifies the signature. If valid, returns the raw token.
    If tampered with or expired, returns None.
    max_age=604800 is 7 days in seconds.
    """
    signer = TimestampSigner(settings.SECRET_KEY)
    try:
        # .unsign() automatically checks the signature and the timestamp
        return signer.unsign(signed_token, max_age=max_age).decode("utf-8")
    except (BadSignature, SignatureExpired):
        # Attack detected! The token was forged, altered, or is too old.
        return None
