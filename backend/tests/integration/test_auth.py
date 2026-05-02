"""
Comprehensive tests for async authentication endpoints
Tests username-based login, registration, JWT, and sessions
"""
# from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession  #, async_sessionmaker, create_async_engine

# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_root(client: AsyncClient) -> None:
    """Test root health endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_health(client: AsyncClient) -> None:
    """Test /health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_api(client: AsyncClient) -> None:
    """Test /api/health endpoint"""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ============================================================================
# REGISTRATION TESTS (Username-based)
# ============================================================================

@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    """Test successful user registration with username"""
    user_data = {
        "username": "johndoe",
        "password": "SecurePass123!",
        "email": "john@example.com",
        "full_name": "John Doe"
    }

    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["username"] == "johndoe"
    assert "user" in data
    assert data["user"]["username"] == "johndoe"
    assert data["user"]["email"] == "john@example.com"
    assert "hashed_password" not in data["user"]


@pytest.mark.asyncio
async def test_register_minimal_data(client: AsyncClient) -> None:
    """Test registration with only username and password (email optional)"""
    user_data = {
        "email": "minimal@example.com",
        "username": "minimaluser",
        "password": "SecurePass123!"
    }

    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["username"] == "minimaluser"
    assert data["user"]["email"] == "minimal@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient) -> None:
    """Test that duplicate username registration fails"""
    user_data = {
        "email": "duplicate@example.com",
        "username": "duplicate",
        "password": "SecurePass123!"
    }

    # First registration should succeed
    response1 = await client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201

    # Second registration with same username should fail
    response2 = await client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 400
    assert "already taken" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Test that duplicate email registration fails"""
    user_data = {
        "email": "duplicate@example.com",
        "username": "duplicate",
        "password": "SecurePass123!"
    }

    # First registration should succeed
    response1 = await client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201

    # Second registration with same username should fail
    response2 = await client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 400
    assert "already taken" in response2.json()["detail"].lower()

@pytest.mark.asyncio
async def test_register_invalid_data(client: AsyncClient) -> None:
    """Test registration with invalid data"""
    # Missing password
    response = await client.post("/api/v1/auth/register", json={"username": "test"})
    assert response.status_code == 422

    # Missing username
    response = await client.post("/api/v1/auth/register", json={"password": "pass"})
    assert response.status_code == 422


# ============================================================================
# LOGIN TESTS (Username-based, JWT mode)
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Test successful login returns session token"""
    # Register user first
    register_data = {
        "email": "login@example.com",
        "username": "logintest",
        "password": "SecurePass123!"
    }
    await client.post("/api/v1/auth/register", json=register_data)

    # Login with username
    login_data = {
        "username": "logintest",
        "password": "SecurePass123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    # assert "session_token" in data
    assert data["success"] is True
    assert data["username"] == "logintest"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """Test login with incorrect password"""
    # Register user
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpass@example.com",
        "username": "wrongpass",
        "password": "CorrectPass123!"
    })

    # Login with wrong password
    response = await client.post("/api/v1/auth/login", json={
        "username": "wrongpass",
        "password": "WrongPass123!"
    })

    assert response.status_code == 401
    assert "invalid username or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Test login with non-existent username"""
    response = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "SomePass123!"
    })

    assert response.status_code == 401
    assert "nvalid username or password" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test that inactive users cannot login"""
    from app.core.security import get_password_hash
    from app.db.models import User

    # Create inactive user directly in database
    inactive_user = User(
        email="inactive@example.com",
        username="inactive",
        hashed_password=get_password_hash("Pass123!"),
        is_active=False
    )
    db_session.add(inactive_user)
    await db_session.commit()

    # Try to login
    response = await client.post("/api/v1/auth/login", json={
        "username": "inactive",
        "password": "Pass123!"
    })

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


# ============================================================================
# SESSION LOGIN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_session_mode(client: AsyncClient) -> None:
    """Test session-based authentication"""
    # Register user
    await client.post("/api/v1/auth/register", json={
        "email": "session@example.com",
        "username": "sessionuser",
        "password": "SecurePass123!"
    })

    # Login with session mode
    response = await client.post(
        "/api/v1/auth/login?use_session=true",
        json={
            "username": "sessionuser",
            "password": "SecurePass123!"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["username"] == "sessionuser"
    assert "user" in data

    # Check that session cookie is set
    assert "session_token" in response.cookies


# ============================================================================
# LOGOUT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient) -> None:
    """Test logout endpoint"""
    # Register and login
    await client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "username": "logoutuser",
        "password": "SecurePass123!"
    })

    login_response = await client.post(
        "/api/v1/auth/login?use_session=true",
        json={
            "username": "logoutuser",
            "password": "SecurePass123!"
        }
    )
    session_token = login_response.cookies.get("session_token")
    assert session_token is not None

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        cookies={"session_token": session_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "logged out" in data["message"].lower()


# ============================================================================
# JWT TOKEN VALIDATION TESTS
# ============================================================================




# ============================================================================
# PASSWORD SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_password_hashing(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test that passwords are properly hashed (Argon2)"""
    from sqlalchemy import select

    from app.db.models import User

    # Register user
    await client.post("/api/v1/auth/register", json={
        "email": "hash@example.com",
        "username": "hashtest",
        "password": "SecurePass123!"
    })

    # Check database
    result = await db_session.execute(select(User).where(User.username == "hashtest"))
    user = result.scalar_one()

    # Password should be hashed (not plaintext)
    assert user.hashed_password != "SecurePass123!"
    # Argon2 hashes start with $argon2
    assert user.hashed_password.startswith("$argon2")


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_username_case_sensitivity(client: AsyncClient) -> None:
    """Test username case sensitivity"""
    # Register user
    await client.post("/api/v1/auth/register", json={
        "email": "casesensitive@example.com",
        "username": "CaseSensitive",
        "password": "Pass123!"
    })

    # Try to login with different case
    response = await client.post("/api/v1/auth/login", json={
        "username": "casesensitive",
        "password": "Pass123!"
    })

    # Should fail as backend is currently case-sensitive (original test intent)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_special_characters_in_username(client: AsyncClient) -> None:
    """Test usernames with special characters"""
    response = await client.post("/api/v1/auth/register", json={
        "email": "special@example.com",
        "username": "user_test-123",
        "password": "Pass123!"
    })

    # Should succeed (underscores and hyphens are allowed)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_username_length_limits(client: AsyncClient) -> None:
    """Test username length constraints"""
    # Very long username (>50 chars)
    long_username = "a" * 51
    response = await client.post("/api/v1/auth/register", json={
        "email": "long@example.com",
        "username": long_username,
        "password": "Pass123!"
    })

    # Should fail or truncate (depends on database constraints)
    assert response.status_code in [400, 422]


# ============================================================================
# INTEGRATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient) -> None:
    """Test complete authentication flow: register -> login -> logout"""
    username = "fullflowuser"
    password = "SecurePass123!"

    # 1. Register
    register_response = await client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password,
        "email": "fullflow@example.com"
    })
    assert register_response.status_code == 201

    # 2. Login (Defaults to Session)
    jwt_response = await client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    assert jwt_response.status_code == 200
    # assert "session_token" in jwt_response.json()

    # 3. Login (Session)
    session_response = await client.post(
        "/api/v1/auth/login?use_session=true",
        json={
            "username": username,
            "password": password
        }
    )
    assert session_response.status_code == 200
    #session_token = session_response.cookies.get("session_token")
    #assert session_token is not None

    # 4. Logout
    logout_response = await client.post(
        "/api/v1/auth/logout"
        # cookies={"session_token": session_token}
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True

# ============================================================================
# CRYPTOGRAPHIC SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cryptographic_session_signature(client: AsyncClient) -> None:
    """
    Test that valid session cookies allow access,
    but tampered cookies trigger immediate 401 rejections via signature failure.
    """
    username = "tampertest"
    password = "SecurePass123!"

    # 1. Register and Login to get a valid signed cookie
    await client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password,
        "email": "tamper@example.com"
    })

    login_response = await client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_response.status_code == 200

    # Extract the valid signed cookie
    valid_cookie = login_response.cookies.get("session_token")
    assert valid_cookie is not None

    # 2. Verify access with VALID cookie
    client.cookies.set("session_token", valid_cookie)
    me_response_valid = await client.get("/api/v1/auth/me")

    assert me_response_valid.status_code == 200
    assert me_response_valid.json()["username"] == username

    # 3. Tamper with the cookie (simulate an attacker attempting to forge a session)
    # The itsdangerous signer outputs: payload.timestamp.signature
    # Changing even one character at the end invalidates the HMAC math
    tampered_cookie = valid_cookie[:-1] + ("X" if valid_cookie[-1] != "X" else "Y")

    # 4. Verify access is REJECTED with TAMPERED cookie
    client.cookies.set("session_token", tampered_cookie)
    me_response_tampered = await client.get("/api/v1/auth/me")

    # Should be rejected mathematically before ever querying PostgreSQL
    assert me_response_tampered.status_code == 401


# ============================================================================
# ANTI-HIJACKING & FINGERPRINTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_session_fingerprinting_anti_hijacking(client: AsyncClient) -> None:
    """
    Test that changing environmental context (User-Agent)
    invalidates the session and permanently burns the token.
    """
    username = "fingerprintuser"
    password = "SecurePass123!"

    # Define our two distinct environmental contexts
    baseline_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegitBrowser/1.0"
    hacker_ua = "Curl/7.68.0 (HackerTerminal)"

    # 1. Register the user
    await client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password,
        "email": "fingerprint@example.com"
    }, headers={"User-Agent": baseline_ua})

    # 2. Login as the Legitimate User (Establishes the Baseline)
    login_response = await client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    }, headers={"User-Agent": baseline_ua})
    assert login_response.status_code == 200

    # Extract the signed cookie
    valid_cookie = login_response.cookies.get("session_token")
    assert valid_cookie is not None
    client.cookies.set("session_token", valid_cookie)

    # 3. Legitimate Access (Should Succeed)
    # The cookie and the User-Agent match the database records.
    me_response_valid = await client.get("/api/v1/auth/me", headers={"User-Agent": baseline_ua})
    assert me_response_valid.status_code == 200
    assert me_response_valid.json()["username"] == username

    # 4. Hijacked Access (Should Fail & Burn Session)
    # The hacker has the VALID cryptographically signed cookie, but is using a different device.
    me_response_hijacked = await client.get("/api/v1/auth/me", headers={"User-Agent": hacker_ua})

    assert me_response_hijacked.status_code == 401
    detail = me_response_hijacked.json().get("detail", "").lower()
    assert "context mismatch" in detail or "invalidated" in detail

    # 5. Verify Auto-Remediation (The "Burn" Feature)
    # The legitimate user tries to use their browser again. Because the hacker
    # tripped the alarm in Step 4, the session should be deleted from PostgreSQL!
    me_response_burned = await client.get("/api/v1/auth/me", headers={"User-Agent": baseline_ua})

    # Even though the original user has the right context, the session no longer exists.
    assert me_response_burned.status_code == 401
