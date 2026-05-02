# backend/tests/integration/test_circle_members.py
"""
Comprehensive tests for circle_members covering all CRUD operations and role-based permissions.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Circle, CircleMember, User
from app.schemas.social import CircleRole

# ======================================================
# FIXTURES (test data setup)
# ======================================================

@pytest_asyncio.fixture
async def test_owner(create_test_user, client: AsyncClient) -> User:
    """Create circle owner and login"""
    user = await create_test_user("owner", "password123")

    # Login to get session token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "owner",
        "password": "password123"
    })

    assert login_response.status_code == 200
    user.session_token = login_response.cookies.get("session_token")
    assert user.session_token is not None
    return user


@pytest_asyncio.fixture
async def test_moderator(create_test_user, client: AsyncClient) -> User:
    """Create a moderator user"""
    user = await create_test_user("moderator", "password123")

    login_response = await client.post("/api/v1/auth/login", json={
        "username": "moderator",
        "password": "password123"
    })

    assert login_response.status_code == 200
    user.session_token = login_response.cookies.get("session_token")
    assert user.session_token is not None
    return user


@pytest_asyncio.fixture
async def test_member(create_test_user, client: AsyncClient) -> User:
    """Create a regular member user"""
    user = await create_test_user("member", "password123")

    login_response = await client.post("/api/v1/auth/login", json={
        "username": "member",
        "password": "password123"
    })

    assert login_response.status_code == 200
    user.session_token = login_response.cookies.get("session_token")
    assert user.session_token is not None
    return user


@pytest_asyncio.fixture
async def test_circle(
    db_session: AsyncSession,
    test_owner: User
) -> Circle:
    """Create a test circle owned by test_owner"""
    circle = Circle(
        name="Test Circle",
        description="For testing",
        owner_id=test_owner.id
    )
    db_session.add(circle)
    await db_session.commit()
    await db_session.refresh(circle)
    return circle


@pytest_asyncio.fixture
async def setup_circle_members(
    db_session: AsyncSession,
    test_circle: Circle,
    test_owner: User,
    test_moderator: User,
    test_member: User
) -> dict:
    """Setup complete circle with owner, moderator, and member"""
    # Add owner as member
    owner_member = CircleMember(
        circle_id=test_circle.id,
        user_id=test_owner.id,
        role=CircleRole.OWNER
    )
    db_session.add(owner_member)

    # Add moderator
    mod_member = CircleMember(
        circle_id=test_circle.id,
        user_id=test_moderator.id,
        role=CircleRole.MODERATOR
    )
    db_session.add(mod_member)

    # Add regular member
    reg_member = CircleMember(
        circle_id=test_circle.id,
        user_id=test_member.id,
        role=CircleRole.MEMBER
    )
    db_session.add(reg_member)

    await db_session.commit()

    return {
        "circle": test_circle,
        "owner": test_owner,
        "moderator": test_moderator,
        "member": test_member
    }


# ======================================================
# TESTS FOR REMOVE MEMBER
# ======================================================

@pytest.mark.asyncio
async def test_remove_member_by_owner_success(
    client: AsyncClient,
    setup_circle_members: dict,
    db_session: AsyncSession
) -> None:
    """Test owner can remove a regular member"""
    data = setup_circle_members
    member = data["member"]

    # Set cookie on client
    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{member.id}"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "removed" in result["message"].lower()

    # Verify member is gone from database
    member_check = await db_session.execute(
        select(CircleMember).where(
            CircleMember.circle_id == data["circle"].id,
            CircleMember.user_id == member.id
        )
    )
    assert member_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_remove_member_by_moderator_success(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test moderator can remove a regular member"""
    data = setup_circle_members
    member = data["member"]

    client.cookies.set("session_token", data["moderator"].session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{member.id}"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True


@pytest.mark.asyncio
async def test_moderator_cannot_remove_another_moderator(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test moderator cannot remove another moderator"""
    data = setup_circle_members
    moderator = data["moderator"]
    another_mod = data["moderator"]  # For test purposes, but should fail

    client.cookies.set("session_token", moderator.session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{another_mod.id}"
    )

    assert response.status_code == 403
    result = response.json()
    assert "cannot remove other moderators" in result["detail"].lower()


@pytest.mark.asyncio
async def test_moderator_cannot_remove_owner(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test moderator cannot remove the circle owner"""
    data = setup_circle_members
    moderator = data["moderator"]
    owner = data["owner"]

    client.cookies.set("session_token", moderator.session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{owner.id}"
    )

    assert response.status_code == 403
    result = response.json()
    assert "cannot remove the circle owner" in result["detail"].lower()


@pytest.mark.asyncio
async def test_member_cannot_remove_anyone(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test regular member cannot remove anyone"""
    data = setup_circle_members
    member = data["member"]
    another_member = data["member"]  # Another member

    client.cookies.set("session_token", member.session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{another_member.id}"
    )

    assert response.status_code == 403
    result = response.json()
    assert "Insufficient circle permissions to perform this action" in result["detail"]


@pytest.mark.asyncio
async def test_remove_nonexistent_member(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test removing a user who is not a member"""
    data = setup_circle_members
    owner = data["owner"]
    non_member_id = 99999

    client.cookies.set("session_token", owner.session_token)

    response = await client.delete(
        f"/api/v1/circles/{data['circle'].id}/members/{non_member_id}"
    )

    assert response.status_code == 404
    result = response.json()
    assert "not found" in result["detail"].lower()

# ======================================================
# TESTS FOR ADD MEMBER
# ======================================================

@pytest.mark.asyncio
async def test_add_member_by_owner_success(
    client: AsyncClient,
    setup_circle_members: dict,
    create_test_user
) -> None:
    """Test owner can add a new member"""
    data = setup_circle_members

    # Create a new user to add (doar username și parolă)
    new_user = await create_test_user("newuser", "password123")

    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.post(
        f"/api/v1/circles/{data['circle'].id}/members",
        json={"user_id": new_user.id}
    )

    assert response.status_code == 201
    result = response.json()
    assert result["success"] is True
    assert result["member"]["role"] == "member"
    assert result["member"]["badge"] == "👤"


@pytest.mark.asyncio
async def test_add_member_by_moderator_success(
    client: AsyncClient,
    setup_circle_members: dict,
    create_test_user
) -> None:
    """Test moderator can add a new member"""
    data = setup_circle_members

    new_user = await create_test_user("newuser2", "password123")

    client.cookies.set("session_token", data["moderator"].session_token)

    response = await client.post(
        f"/api/v1/circles/{data['circle'].id}/members",
        json={"user_id": new_user.id}
    )

    assert response.status_code == 201
    result = response.json()
    assert result["success"] is True


@pytest.mark.asyncio
async def test_add_existing_member_fails(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test adding a user who is already a member fails"""
    data = setup_circle_members
    existing_member = data["member"]

    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.post(
        f"/api/v1/circles/{data['circle'].id}/members",
        json={"user_id": existing_member.id}
    )

    assert response.status_code == 400
    result = response.json()
    assert "already a member" in result["detail"].lower()


# ======================================================
# TESTS FOR UPDATE ROLE
# ======================================================

@pytest.mark.asyncio
async def test_owner_promotes_member_to_moderator(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test owner can promote a member to moderator"""
    data = setup_circle_members
    member = data["member"]

    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.put(
        f"/api/v1/circles/{data['circle'].id}/members/{member.id}/role",
        json={"role": "moderator"}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["member"]["role"] == "moderator"
    assert result["member"]["badge"] == "🛡️"

# ======================================================
# TESTS FOR ROLE-BASED PERMISSIONS
# ======================================================
@pytest.mark.asyncio
async def test_moderator_cannot_promote(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test moderator cannot promote another member"""
    data = setup_circle_members
    member = data["member"]

    client.cookies.set("session_token", data["moderator"].session_token)

    response = await client.put(
        f"/api/v1/circles/{data['circle'].id}/members/{member.id}/role",
        json={"role": "moderator"}
    )

    assert response.status_code == 403
    result = response.json()
    assert "Insufficient circle permissions to perform this action" in result["detail"]

@pytest.mark.asyncio
async def test_remove_member_circle_not_found(
    client: AsyncClient,
    test_owner: User
) -> None:
    """Test removing member from non-existent circle"""
    client.cookies.set("session_token", test_owner.session_token)

    response = await client.delete(
        "/api/v1/circles/99999/members/1"
    )

    assert response.status_code == 404
    assert "Circle not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_member_circle_not_found(
    client: AsyncClient,
    test_owner: User
) -> None:
    """Test adding member to non-existent circle"""
    client.cookies.set("session_token", test_owner.session_token)

    response = await client.post(
        "/api/v1/circles/99999/members",
        json={"user_id": 1}
    )

    assert response.status_code == 404
    assert "Circle not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_member_user_not_found(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test adding non-existent user to circle"""
    data = setup_circle_members
    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.post(
        f"/api/v1/circles/{data['circle'].id}/members",
        json={"user_id": 99999}
    )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_role_user_not_found(
    client: AsyncClient,
    setup_circle_members: dict
) -> None:
    """Test updating role for non-existent user"""
    data = setup_circle_members
    client.cookies.set("session_token", data["owner"].session_token)

    response = await client.put(
        f"/api/v1/circles/{data['circle'].id}/members/99999/role",
        json={"role": "moderator"}
    )

    assert response.status_code == 404
    assert "Member not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_role_circle_not_found(
    client: AsyncClient,
    test_owner: User
) -> None:
    """Test updating role in non-existent circle"""
    client.cookies.set("session_token", test_owner.session_token)

    response = await client.put(
        "/api/v1/circles/99999/members/1/role",
        json={"role": "moderator"}
    )

    assert response.status_code == 404
