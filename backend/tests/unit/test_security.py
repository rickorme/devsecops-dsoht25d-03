"""
Unit tests for backend/app/core/security.py
Tests password hashing, JWT tokens, and session management
"""
import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from itsdangerous import BadSignature, TimestampSigner

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_session_expiry,
    create_session_token,
    decode_token,
    get_password_hash,
    sign_session_token,
    verify_password,
    verify_session_token,
)


class TestPasswordFunctions:
    """Test password hashing and verification"""

    def test_password_hash_and_verify_correct(self):
        """Test that a correct password verifies successfully"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_verify_incorrect(self):
        """Test that an incorrect password fails verification"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_password_hash_different_for_same_password(self):
        """Test that hashing the same password twice produces different hashes (salt)"""
        password = "SamePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_password_hash_format_argon2(self):
        """Test that hash starts with Argon2 identifier"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        # Argon2 hashes start with $argon2
        assert hashed.startswith("$argon2")

    def test_password_with_special_characters(self):
        """Test password hashing with special characters"""
        password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_with_unicode(self):
        """Test password hashing with unicode characters"""
        password = "Пароль123🔒"  # Russian + emoji
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_empty_password_handling(self):
        """Test behavior with empty password"""
        password = ""
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_very_long_password(self):
        """Test hashing a very long password"""
        password = "a" * 1000  # 1000 character password
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_case_sensitive_verification(self):
        """Test that password verification is case-sensitive"""
        password = "CaseSensitive123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password(password.lower(), hashed) is False
        assert verify_password(password.upper(), hashed) is False

    def test_whitespace_in_password(self):
        """Test password with leading/trailing whitespace"""
        password = "  password with spaces  "
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password(password.strip(), hashed) is False


class TestJWTTokens:
    """Test JWT token creation and decoding"""

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify expiration
        decoded = decode_token(token)
        assert decoded["sub"] == "testuser"
        assert "exp" in decoded

    def test_create_token_with_default_expiry(self):
        """Test token creation with default expiration from settings"""
        data = {"sub": "defaultuser"}
        token = create_access_token(data)

        assert token is not None
        decoded = decode_token(token)
        assert decoded["sub"] == "defaultuser"

        # Verify expiration is roughly ACCESS_TOKEN_EXPIRE_MINUTES from now
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
        now = datetime.now(UTC)
        delta = exp_time - now
        # Should be close to settings value (within 1 minute tolerance)
        expected_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        assert expected_minutes - 1 <= delta.total_seconds() / 60 <= expected_minutes + 1

    def test_token_contains_correct_data(self):
        """Test that token payload contains all provided data"""
        data = {
            "sub": "testuser",
            "email": "test@example.com",
            "role": "admin"
        }
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded["sub"] == "testuser"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_token_uniqueness(self):
        """Test that different tokens are created for different data"""
        token1 = create_access_token({"sub": "user1"})
        token2 = create_access_token({"sub": "user2"})
        assert token1 != token2

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "validuser", "id": 123}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded["sub"] == "validuser"
        assert decoded["id"] == 123

    def test_decode_expired_token(self):
        """Test that expired token raises error"""
        data = {"sub": "expireduser"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_invalid_signature(self):
        """Test that token with wrong signature fails"""
        data = {"sub": "testuser"}
        # Create token with different secret
        fake_token = jwt.encode(
            {**data, "exp": datetime.now(UTC) + timedelta(minutes=30)},
            "wrong-secret-key",
            algorithm=settings.ALGORITHM
        )

        with pytest.raises(jwt.InvalidSignatureError):
            decode_token(fake_token)

    def test_decode_malformed_token(self):
        """Test that malformed token raises error"""
        malformed_token = "this.is.not.a.valid.jwt"

        with pytest.raises(jwt.DecodeError):
            decode_token(malformed_token)

    def test_decode_token_with_wrong_algorithm(self):
        """Test token created with different algorithm fails"""
        data = {"sub": "testuser"}
        # Create token with HS512 instead of HS256
        wrong_algo_token = jwt.encode(
            {**data, "exp": datetime.now(UTC) + timedelta(minutes=30)},
            settings.SECRET_KEY,
            algorithm="HS512"
        )

        with pytest.raises(jwt.InvalidAlgorithmError):
            decode_token(wrong_algo_token)

    def test_empty_data_token(self):
        """Test creating token with empty data dict"""
        token = create_access_token({})
        decoded = decode_token(token)
        # Should only contain exp claim
        assert "exp" in decoded
        assert len(decoded) == 1

    def test_token_expiry_precision(self):
        """Test that custom expiry is precisely set"""
        data = {"sub": "preciseuser"}
        custom_minutes = 45
        expires_delta = timedelta(minutes=custom_minutes)
        token = create_access_token(data, expires_delta)

        decoded = decode_token(token)
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
        now = datetime.now(UTC)
        delta = exp_time - now

        # Should be within 1 second of the specified time
        assert abs(delta.total_seconds() - (custom_minutes * 60)) < 1


class TestSessionManagement:
    """Test session token and expiry functions"""

    def test_session_token_creation(self):
        """Test that session token is created"""
        token = create_session_token()
        assert token is not None
        assert isinstance(token, str)

    def test_session_token_length(self):
        """Test that session token has correct length (64 hex chars)"""
        token = create_session_token()
        # token_hex(32) produces 64 hex characters
        assert len(token) == 64

    def test_session_token_format(self):
        """Test that session token is valid hexadecimal"""
        token = create_session_token()
        # Should only contain hex characters (0-9, a-f)
        assert re.match(r'^[0-9a-f]{64}$', token) is not None

    def test_session_token_uniqueness(self):
        """Test that session tokens are unique"""
        tokens = [create_session_token() for _ in range(100)]
        # All tokens should be unique
        assert len(tokens) == len(set(tokens))

    def test_session_expiry_default(self):
        """Test session expiry with default hours (24)"""
        before = datetime.now(UTC)
        expiry = create_session_expiry()
        after = datetime.now(UTC)

        # Should be 24 hours from now (default)
        expected_delta = timedelta(hours=24)
        actual_delta = expiry - before

        # Allow 1 second tolerance
        assert abs(actual_delta.total_seconds() - expected_delta.total_seconds()) < 1
        assert expiry > after

    def test_session_expiry_custom_hours(self):
        """Test session expiry with custom hours"""
        custom_hours = 48
        before = datetime.now(UTC)
        expiry = create_session_expiry(hours=custom_hours)

        expected_delta = timedelta(hours=custom_hours)
        actual_delta = expiry - before

        # Allow 1 second tolerance
        assert abs(actual_delta.total_seconds() - expected_delta.total_seconds()) < 1

    def test_session_expiry_timezone(self):
        """Test that session expiry uses UTC timezone"""
        expiry = create_session_expiry()
        assert expiry.tzinfo is not None
        assert expiry.tzinfo == UTC

    def test_session_expiry_in_future(self):
        """Test that session expiry is always in the future"""
        expiry = create_session_expiry()
        now = datetime.now(UTC)
        assert expiry > now

    def test_session_expiry_short_duration(self):
        """Test session expiry with very short duration"""
        expiry = create_session_expiry(hours=1)
        now = datetime.now(UTC)
        delta = expiry - now

        # Should be approximately 1 hour (3600 seconds)
        assert 3599 <= delta.total_seconds() <= 3601

    def test_session_expiry_long_duration(self):
        """Test session expiry with very long duration"""
        expiry = create_session_expiry(hours=720)  # 30 days
        now = datetime.now(UTC)
        delta = expiry - now

        # Should be approximately 30 days
        expected_seconds = 720 * 3600
        assert abs(delta.total_seconds() - expected_seconds) < 1


class TestSecurityIntegration:
    """Integration tests for security functions working together"""

    def test_password_and_token_workflow(self):
        """Test complete auth workflow: hash password, create token, verify"""
        # Step 1: User registers - hash their password
        password = "UserPassword123!"
        hashed = get_password_hash(password)

        # Step 2: User logs in - verify password
        assert verify_password(password, hashed) is True

        # Step 3: Create access token for user
        token = create_access_token({"sub": "testuser", "id": 1})

        # Step 4: Verify token can be decoded
        decoded = decode_token(token)
        assert decoded["sub"] == "testuser"
        assert decoded["id"] == 1

    def test_session_token_storage_simulation(self):
        """Test session token creation for storage in database"""
        # Create session token
        session_token = create_session_token()
        session_expiry = create_session_expiry()

        # Simulate storing in DB (check we have valid values)
        assert len(session_token) == 64
        assert session_expiry > datetime.now(UTC)

        # Simulate checking if session is expired
        is_expired = datetime.now(UTC) > session_expiry
        assert is_expired is False

    def test_multiple_tokens_independence(self):
        """Test that multiple tokens for different users are independent"""
        user1_token = create_access_token({"sub": "user1", "role": "user"})
        user2_token = create_access_token({"sub": "user2", "role": "admin"})

        decoded1 = decode_token(user1_token)
        decoded2 = decode_token(user2_token)

        assert decoded1["sub"] == "user1"
        assert decoded1["role"] == "user"
        assert decoded2["sub"] == "user2"
        assert decoded2["role"] == "admin"

        # Tokens should be different
        assert user1_token != user2_token

class TestCryptographicSessionSignatures:
    """Test cryptographic signing and verification of session tokens using itsdangerous"""

    def test_sign_session_token_format(self):
        """Test that the signed token contains the raw token, timestamp, and signature"""
        raw_token = "my_secure_session_token_123"
        signed_token = sign_session_token(raw_token)

        assert signed_token is not None
        assert isinstance(signed_token, str)
        assert signed_token != raw_token

        # itsdangerous TimestampSigner format: payload.timestamp.signature
        parts = signed_token.split(".")
        assert len(parts) >= 3
        # The payload (first part) should match the raw token exactly
        assert parts[0] == raw_token

    def test_verify_valid_session_token(self):
        """Test that a valid signed token is successfully verified and returns the raw token"""
        raw_token = "valid_session_token_xyz"
        signed_token = sign_session_token(raw_token)

        verified_raw_token = verify_session_token(signed_token)

        # The verification should strip the signature and return the original token
        assert verified_raw_token == raw_token

    def test_verify_tampered_token_payload(self):
        """Test that tampering with the token payload invalidates the signature"""
        raw_token = "valid_session_token"
        signed_token = sign_session_token(raw_token)

        # Tamper with the payload (the first part before the dot)
        # Change 'valid' to 'xalid'
        tampered_token = "x" + signed_token[1:]

        verified_raw_token = verify_session_token(tampered_token)

        # The cryptographic check should fail and return None
        assert verified_raw_token is None

    def test_verify_tampered_token_signature(self):
        """Test that tampering with the mathematical signature invalidates the token"""
        raw_token = "valid_session_token"
        signed_token = sign_session_token(raw_token)

        # Tamper with the signature (the last part)
        # Flip the last character
        tampered_token = signed_token[:-1] + ("X" if signed_token[-1] != "X" else "Y")

        verified_raw_token = verify_session_token(tampered_token)

        # The cryptographic check should fail and return None
        assert verified_raw_token is None

    def test_verify_expired_session_token(self):
        """Test that an explicitly expired token is rejected"""
        raw_token = "expired_session_token"
        signed_token = sign_session_token(raw_token)

        # Verify with a max_age of -1 seconds (so it is instantly expired)
        verified_raw_token = verify_session_token(signed_token, max_age=-1)

        # The timestamp check should fail and return None
        assert verified_raw_token is None

    def test_signer_uses_application_secret_key(self):
        """Test that the signer strictly relies on the application's SECRET_KEY"""
        raw_token = "secret_key_test_token"

        # Sign it with the application's actual key
        signed_token = sign_session_token(raw_token)

        # Attempt to verify it using a different, fake secret key
        # We manually instantiate a signer with a bad key to simulate this
        rogue_signer = TimestampSigner("wrong_secret_key_12345")

        with pytest.raises(BadSignature):
            rogue_signer.unsign(signed_token)
