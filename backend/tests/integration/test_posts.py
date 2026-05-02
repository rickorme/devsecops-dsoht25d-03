# backend/tests/integration/test_posts.py
"""
Integration tests for Post endpoints.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Circle, CircleMember, Post, User
from app.schemas.social import CircleRole


@pytest_asyncio.fixture
async def test_author(create_test_user, client: AsyncClient) -> User:
    """Create a user to act as post author and log in"""
    user = await create_test_user("author", "password123")

    # Login to get session token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "author",
        "password": "password123"
    })
    assert login_response.status_code == 200
    session_token = login_response.cookies.get("session_token")
    assert session_token is not None
    user.session_token = session_token
    return user

@pytest_asyncio.fixture
async def test_non_member(create_test_user, client: AsyncClient) -> User:
    """Create a user who is not a member of this circle"""
    user = await create_test_user("nonmember", "password123")

    # Login to get session token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "nonmember",
        "password": "password123"
    })

    assert login_response.status_code == 200
    session_token = login_response.cookies.get("session_token")
    assert session_token is not None
    user.session_token = session_token
    return user

@pytest_asyncio.fixture
async def test_circle_with_members(db_session: AsyncSession, test_author: User, create_test_user) -> Circle:
    """Create a circle with owner and author as members"""
    owner = await create_test_user("owner", "password123")
    circle = Circle(
        name="Test Circle",
        description="For posts testing",
        owner_id=owner.id
    )
    db_session.add(circle)
    await db_session.flush()

    # Add owner
    db_session.add(CircleMember(
        circle_id=circle.id,
        user_id=owner.id,
        role=CircleRole.OWNER
    ))

    # Add author
    db_session.add(CircleMember(
        circle_id=circle.id,
        user_id=test_author.id,
        role=CircleRole.MEMBER
    ))

    await db_session.commit()
    await db_session.refresh(circle)
    return circle


@pytest.mark.asyncio
async def test_get_feed_empty(client: AsyncClient, test_author: User):
    """GET /posts/feed returns empty list if user has no circles"""
    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)
    response = await client.get("/api/v1/posts/feed")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_feed_with_posts(client: AsyncClient, test_author: User, test_circle_with_members: Circle, db_session: AsyncSession):
    """GET /posts/feed returns posts for user's circles"""
    # Create two posts
    post1 = Post(title="Post 1", content="Content 1", author_id=test_author.id, circle_id=test_circle_with_members.id)
    post2 = Post(title="Post 2", content="Content 2", author_id=test_author.id, circle_id=test_circle_with_members.id)
    db_session.add_all([post1, post2])
    await db_session.commit()

    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)

    response = await client.get("/api/v1/posts/feed")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = [p["title"] for p in data]
    assert "Post 1" in titles
    assert "Post 2" in titles


@pytest.mark.asyncio
async def test_create_post_in_circle(client: AsyncClient, test_author: User, test_non_member: User, test_circle_with_members: Circle):
    """POST /posts/ creates post successfully in a circle"""
    payload = {"title": "New Post", "content": "New Content", "circle_id": test_circle_with_members.id}

    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)

    response = await client.post("/api/v1/posts/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Post"
    assert data["circle_id"] == test_circle_with_members.id
    assert data["author_id"] == test_author.id

    # Set cookie on client
    client.cookies.set("session_token", test_non_member.session_token)

    response = await client.post("/api/v1/posts/", json=payload)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_post(client: AsyncClient, test_author: User, test_non_member: User, test_circle_with_members: Circle, db_session: AsyncSession):
    """GET /posts/{post_id} returns post if user has access"""
    post = Post(title="Single Post", content="Content", author_id=test_author.id, circle_id=test_circle_with_members.id)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)

    # Access as author
    response = await client.get(f"/api/v1/posts/{post.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Single Post"

    # Access non-existent post
    response = await client.get("/api/v1/posts/99999")
    assert response.status_code == 404

    # Set cookie on client
    client.cookies.set("session_token", test_non_member.session_token)

    # Access as non-member
    response = await client.get(f"/api/v1/posts/{post.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient, test_author: User, test_non_member: User, test_circle_with_members: Circle, db_session: AsyncSession):
    """DELETE /posts/{post_id} allows author to delete"""
    post = Post(title="To Delete", content="Delete me", author_id=test_author.id, circle_id=test_circle_with_members.id)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    # Set cookie on client
    client.cookies.set("session_token", test_non_member.session_token)

    # Access as non-member
    response = await client.delete(f"/api/v1/posts/{post.id}")
    assert response.status_code == 403

    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)

    # Author deletes
    response = await client.delete(f"/api/v1/posts/{post.id}")
    assert response.status_code == 204

    # Confirm deletion
    deleted = await db_session.get(Post, post.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_get_circle_posts(client: AsyncClient, test_author: User, test_non_member: User, test_circle_with_members: Circle, db_session: AsyncSession):
    """GET /posts/circle/{circle_id} returns posts from circle"""
    # Add posts to circle
    posts = [
        Post(title=f"Circle Post {i}", content="Content", author_id=test_author.id, circle_id=test_circle_with_members.id)
        for i in range(3)
    ]
    db_session.add_all(posts)
    await db_session.commit()

    # Set cookie on client
    client.cookies.set("session_token", test_author.session_token)

    response = await client.get(f"/api/v1/posts/circle/{test_circle_with_members.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    titles = [p["title"] for p in data]
    for i in range(3):
        assert f"Circle Post {i}" in titles

    # Set cookie on client
    client.cookies.set("session_token", test_non_member.session_token)

    # Access as non-member
    response = await client.get(f"/api/v1/posts/circle/{test_circle_with_members.id}")
    assert response.status_code == 403
