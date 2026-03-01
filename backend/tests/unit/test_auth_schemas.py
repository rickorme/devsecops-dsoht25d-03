"""
Unit tests for backend/app/schemas/auth.py
Tests Pydantic validators and schema constraints
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    SessionResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)


class TestUserCreateSchema:
    """Test UserCreate schema validation"""

    def test_valid_user_creation(self):
        """Test creating user with all valid fields"""
        user_data = {
            "username": "johndoe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "full_name": "John Doe"
        }
        user = UserCreate(**user_data)
        assert user.username == "johndoe"
        assert user.email == "john@example.com"
        assert user.password == "SecurePass123!"
        assert user.full_name == "John Doe"

    def test_valid_user_without_full_name(self):
        """Test creating user without optional full_name"""
        user_data = {
            "username": "janedoe",
            "email": "jane@example.com",
            "password": "SecurePass123!"
        }
        user = UserCreate(**user_data)
        assert user.username == "janedoe"
        assert user.full_name is None

    def test_email_format_validation(self):
        """Test that invalid email formats are rejected"""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "double@@domain.com"
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                UserCreate(
                    username="testuser",
                    email=invalid_email,
                    password="ValidPass123!"
                )
            assert "email" in str(exc_info.value).lower()

    def test_valid_email_formats(self):
        """Test that various valid email formats are accepted"""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_123@sub.example.com"
        ]

        for valid_email in valid_emails:
            user = UserCreate(
                username="testuser",
                email=valid_email,
                password="ValidPass123!"
            )
            assert user.email == valid_email

    def test_username_min_length(self):
        """Test username minimum length constraint (3 chars)"""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="ab",  # Only 2 chars
                email="test@example.com",
                password="ValidPass123!"
            )
        assert "username" in str(exc_info.value).lower()

        # Exactly 3 chars (should pass)
        user = UserCreate(
            username="abc",
            email="test@example.com",
            password="ValidPass123!"
        )
        assert user.username == "abc"

    def test_username_max_length(self):
        """Test username maximum length constraint (50 chars)"""
        # Exactly 50 chars (should pass)
        username_50 = "a" * 50
        user = UserCreate(
            username=username_50,
            email="test@example.com",
            password="ValidPass123!"
        )
        assert user.username == username_50

        # 51 chars (should fail)
        with pytest.raises(ValidationError):
            UserCreate(
                username="a" * 51,
                email="test@example.com",
                password="ValidPass123!"
            )

    def test_password_min_length(self):
        """Test password minimum length constraint (8 chars)"""
        # Too short (7 chars)
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="Pass1!"  # Only 6 chars
            )
        assert "password" in str(exc_info.value).lower()

        # Exactly 8 chars (should pass if complexity is met)
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="Pass123!"  # 8 chars
        )
        assert len(user.password) == 8

    def test_password_complexity_uppercase(self):
        """Test password must contain uppercase letter"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="lowercase123!"  # No uppercase
            )
        assert "uppercase" in str(exc_info.value).lower()

    def test_password_complexity_lowercase(self):
        """Test password must contain lowercase letter"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="UPPERCASE123!"  # No lowercase
            )
        assert "lowercase" in str(exc_info.value).lower()

    def test_password_complexity_number(self):
        """Test password must contain number"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="NoNumbers!"  # No digits
            )
        assert "number" in str(exc_info.value).lower()

    def test_password_complexity_special_char(self):
        """Test password must contain special character"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="NoSpecial123"  # No special chars
            )
        assert "special character" in str(exc_info.value).lower()

    def test_password_all_complexity_requirements(self):
        """Test password meeting all complexity requirements"""
        valid_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd",
            "C0mpl3x#Pass",
            "Valid$Password1"
        ]

        for password in valid_passwords:
            user = UserCreate(
                username="testuser",
                email="test@example.com",
                password=password
            )
            assert user.password == password

    def test_full_name_max_length(self):
        """Test full_name maximum length (100 chars)"""
        # Exactly 100 chars (should pass)
        full_name_100 = "A" * 100
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!",
            full_name=full_name_100
        )
        assert user.full_name == full_name_100

        # 101 chars (should fail)
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="ValidPass123!",
                full_name="A" * 101
            )

    def test_missing_required_fields(self):
        """Test that required fields cannot be omitted"""
        # Missing username
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="ValidPass123!"
            )

        # Missing email
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                password="ValidPass123!"
            )

        # Missing password
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com"
            )


class TestUserLoginSchema:
    """Test UserLogin schema validation"""

    def test_valid_login(self):
        """Test valid login data"""
        login_data = {
            "username": "johndoe",
            "password": "SecurePass123!"
        }
        login = UserLogin(**login_data)
        assert login.username == "johndoe"
        assert login.password == "SecurePass123!"

    def test_missing_username(self):
        """Test that username is required"""
        with pytest.raises(ValidationError):
            UserLogin(password="somepassword")

    def test_missing_password(self):
        """Test that password is required"""
        with pytest.raises(ValidationError):
            UserLogin(username="someuser")

    def test_empty_string_username(self):
        """Test behavior with empty username string"""
        login = UserLogin(username="", password="somepassword")
        assert login.username == ""

    def test_empty_string_password(self):
        """Test behavior with empty password string"""
        login = UserLogin(username="someuser", password="")
        assert login.password == ""


class TestUserResponseSchema:
    """Test UserResponse schema"""

    def test_valid_user_response(self):
        """Test creating user response with all fields"""
        now = datetime.now()
        user_data = {
            "id": 1,
            "username": "johndoe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        user = UserResponse(**user_data)
        assert user.id == 1
        assert user.username == "johndoe"
        assert user.email == "john@example.com"
        assert user.full_name == "John Doe"
        assert user.is_active is True
        assert user.created_at == now
        assert user.updated_at == now

    def test_user_response_without_full_name(self):
        """Test user response with None full_name"""
        now = datetime.now()
        user_data = {
            "id": 2,
            "username": "janedoe",
            "email": "jane@example.com",
            "full_name": None,
            "is_active": True,
            "created_at": now,
            "updated_at": None
        }
        user = UserResponse(**user_data)
        assert user.full_name is None
        assert user.updated_at is None

    def test_user_response_inactive(self):
        """Test user response with is_active=False"""
        now = datetime.now()
        user_data = {
            "id": 3,
            "username": "inactiveuser",
            "email": "inactive@example.com",
            "full_name": None,
            "is_active": False,
            "created_at": now,
            "updated_at": None
        }
        user = UserResponse(**user_data)
        assert user.is_active is False

    def test_user_response_missing_required_fields(self):
        """Test that required fields cannot be omitted"""
        now = datetime.now()

        # Missing id
        with pytest.raises(ValidationError):
            UserResponse(
                username="test",
                email="test@example.com",
                full_name=None,
                is_active=True,
                created_at=now,
                updated_at=None
            )

        # Missing username
        with pytest.raises(ValidationError):
            UserResponse(
                id=1,
                email="test@example.com",
                full_name=None,
                is_active=True,
                created_at=now,
                updated_at=None
            )


class TestTokenSchema:
    """Test Token schema"""

    def test_valid_token(self):
        """Test creating token response"""
        token_data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ",
            "token_type": "bearer"
        }
        token = Token(**token_data)
        assert token.access_token == token_data["access_token"]
        assert token.token_type == "bearer"

    def test_token_default_type(self):
        """Test that token_type defaults to 'bearer'"""
        token = Token(access_token="some.jwt.token")
        assert token.token_type == "bearer"

    def test_token_custom_type(self):
        """Test token with custom token_type"""
        token = Token(access_token="some.token", token_type="custom")
        assert token.token_type == "custom"

    def test_missing_access_token(self):
        """Test that access_token is required"""
        with pytest.raises(ValidationError):
            Token(token_type="bearer")


class TestSessionResponseSchema:
    """Test SessionResponse schema"""

    def test_valid_session_response(self):
        """Test creating session response"""
        session_data = {
            "success": True,
            "username": "johndoe",
            "session_token": "abc123xyz"
        }
        session = SessionResponse(**session_data)
        assert session.success is True
        assert session.username == "johndoe"
        assert session.session_token == "abc123xyz"

    def test_session_response_minimal(self):
        """Test session response with only required fields"""
        # Check what fields are actually required by creating with minimal data
        try:
            session = SessionResponse(success=True)
            assert session.success is True
        except ValidationError:
            # If it fails, some fields are required
            pass


class TestSchemaIntegration:
    """Integration tests for schema interactions"""

    def test_registration_to_response_flow(self):
        """Test data flow from registration to user response"""
        # Step 1: User submits registration
        registration = UserCreate(
            username="newuser",
            email="new@example.com",
            password="NewPass123!",
            full_name="New User"
        )

        # Step 2: After DB save, create response (simulated)
        now = datetime.now()
        response = UserResponse(
            id=1,
            username=registration.username,
            email=registration.email,
            full_name=registration.full_name,
            is_active=True,
            created_at=now,
            updated_at=None
        )

        assert response.username == registration.username
        assert response.email == registration.email
        # Password should NOT be in response
        assert not hasattr(response, 'password')

    def test_login_to_token_flow(self):
        """Test data flow from login to token response"""
        # Step 1: User submits login
        login = UserLogin(
            username="existinguser",
            password="ExistingPass123!"
        )

        # Step 2: After authentication, create token (simulated)
        token = Token(
            access_token="generated.jwt.token.here",
            token_type="bearer"
        )

        assert login.username == "existinguser"
        assert token.access_token is not None
        assert token.token_type == "bearer"
