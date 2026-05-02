# backend/tests/integration/test_users.py
"""
Tests for searching users to add to circles.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Circle, CircleMember, User
from app.schemas.social import CircleRole


@pytest_asyncio.fixture
async def test_owner(create_test_user, client: AsyncClient) -> User:
    """Create circle owner and login to get session token"""
    # Create user
    user = await create_test_user("owner", "password123")

    # Login to get session token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "owner",
        "password": "password123"
    })

    assert login_response.status_code == 200
    session_token = login_response.cookies.get("session_token")
    assert session_token is not None

    user.session_token = session_token
    return user


@pytest_asyncio.fixture
async def test_users(create_test_user) -> list[User]:
    """Create test users for searching (3 users)"""
    users = []
    for i in range(3):
        user = await create_test_user(f"user{i}", "password123")
        users.append(user)
    return users


@pytest_asyncio.fixture
async def test_circle(
    db_session: AsyncSession,
    test_owner: User,
    test_users: list[User]
) -> Circle:
    """Create a circle with owner and one member"""
    # Create circle
    circle = Circle(
        name="Test Circle",
        description="For testing",
        owner_id=test_owner.id
    )
    db_session.add(circle)
    await db_session.flush()

    # Add owner as member
    owner_member = CircleMember(
        circle_id=circle.id,
        user_id=test_owner.id,
        role=CircleRole.OWNER
    )
    db_session.add(owner_member)

    # Add first user as member (user0)
    member = CircleMember(
        circle_id=circle.id,
        user_id=test_users[0].id,
        role=CircleRole.MEMBER
    )
    db_session.add(member)

    await db_session.commit()
    await db_session.refresh(circle)
    return circle


@pytest.mark.asyncio
async def test_search_users_by_username(
    client: AsyncClient,
    test_circle: Circle,
    test_owner: User
) -> None:
    """Test searching users by username"""
    response = await client.get(
        f"/api/v1/users/search?query=user&circle_id={test_circle.id}",
        cookies={"session_token": test_owner.session_token}
    )

    assert response.status_code == 200
    results = response.json()

    # Should find users 1 and 2 (user0 is already member)
    assert len(results) == 2
    for result in results:
        assert result["is_already_member"] is False
        assert "user" in result["username"]


@pytest.mark.asyncio
async def test_search_users_empty_query(
    client: AsyncClient,
    test_circle: Circle,
    test_owner: User
) -> None:
    """Test search with empty query"""
    response = await client.get(
        f"/api/v1/users/search?query=&circle_id={test_circle.id}",
        cookies={"session_token": test_owner.session_token}
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0

@pytest.mark.asyncio
async def test_search_users_no_results(
    client: AsyncClient,
    test_circle: Circle,
    test_owner: User
) -> None:
    """Test search with query that returns nothing"""
    response = await client.get(
        f"/api/v1/users/search?query=nonexistent&circle_id={test_circle.id}",
        cookies={"session_token": test_owner.session_token}
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0

@pytest.mark.asyncio
async def test_search_users_circle_not_found(
    client: AsyncClient,
    test_owner: User
) -> None:
    """Test search with invalid circle ID"""
    client.cookies.set("session_token", test_owner.session_token)

    response = await client.get(
        "/api/v1/users/search?query=user&circle_id=99999"
    )

    # User not in circle -> 403
    assert response.status_code == 403
