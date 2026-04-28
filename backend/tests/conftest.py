# backend/tests/conftest.py
"""
Shared fixtures for both API and E2E tests,
including async database setup and a test client for FastAPI.
"""
import asyncio
import os
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from typing import Any

import nest_asyncio
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Import your app components
from app.core.db import get_db
from app.core.security import get_password_hash
from app.db.models import Base, Circle, CircleMember, Post, User
from app.main import app

# Patch asyncio to allow nested event loops (Fixes Playwright sync + Async DB conflicts)
nest_asyncio.apply()

load_dotenv()


# Point to the new Docker test_db (Port 5434)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://user:password@test_db:5432/test_db"
)

# ==========================================
# 1. PLAYWRIGHT CONFIGURATION (For E2E Tests)
# ==========================================
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """
    Configures Playwright.
    Setting the base_url means your step definitions can just use:
    page.goto("/login") instead of page.goto("http://localhost:3000/login")
    """
    return {
        **browser_context_args,
        "base_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "viewport": {"width": 1280, "height": 720},
    }

# ==========================================
# 2.ASYNC DATABASE CONFIGURATION (Shared by API & E2E)
# ==========================================
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Forces pytest to use a single async event loop for the whole test session,
    while respecting Playwright's existing loop if it's already running.
    """
    try:
        # Try to grab Playwright's running loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no loop is running, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # EXPLICITLY patch THIS specific loop so it allows nesting
    nest_asyncio.apply(loop)

    yield loop

    # Note: We purposely DO NOT close the loop here anymore (loop.close()).
    # If Playwright started the loop, closing it will crash the browser teardown!

@pytest_asyncio.fixture(scope="session")
async def async_engine()-> AsyncGenerator[AsyncEngine, None]:
    """Creates the SQLAlchemy async engine once per test run."""
    # NullPool is great for tests to prevent connection state issues
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    # Create tables once per test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        # Seed the Roles table immediately after creating the tables
        await conn.execute(text(
            "INSERT INTO roles (id, name, description) VALUES (1, 'user', 'Standard user') ON CONFLICT DO NOTHING;"
        ))
        await conn.execute(text(
            "INSERT INTO roles (id, name, description) VALUES (2, 'admin', 'System administrator') ON CONFLICT DO NOTHING;"
        ))

    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a transactional database session for a test,
    then ROLLS IT BACK when the test finishes. No cleanup needed!
    """
    async with async_engine.connect() as connection:
        transaction = await connection.begin()

        # ✅ Added join_transaction_mode="create_savepoint"
        # This safely turns all .commit() calls into nested savepoints!
        async_session_maker = async_sessionmaker(
            connection,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )
        session = async_session_maker()

        try:
            # ✅ PROPERLY INDENTED: The test runs WHILE the connection is open!
            yield session
        finally:
            # Test is over. Safely close session and rollback, even if the test crashed!
            try:
                await session.close()
                await transaction.rollback()
            except Exception as teardown_err:
                print(f"Failed to cleanly rollback DB: {teardown_err}")

# ==========================================
# 3. FASTAPI TEST CLIENT (For API Tests)
# ==========================================
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with overridden database dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
def create_test_user_synchronous():
    """
    Bulletproof Synchronous Factory.
    No teardown needed because `clean_database_before_test` handles it!
    """
    def _create_user(username: str, plain_password: str):
        async def _insert():
            engine = create_async_engine(TEST_DATABASE_URL)
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session_maker() as session:
                hashed_pw = get_password_hash(plain_password)
                new_user = User(
                    username=username,
                    email=f"{username.lower()}@example.com",
                    hashed_password=hashed_pw,
                    role_id=1
                )
                session.add(new_user)
                await session.commit()
            await engine.dispose()

        asyncio.run(_insert())

    # We just yield the function. No try/finally block needed anymore!
    yield _create_user

@pytest_asyncio.fixture
async def create_test_user(
    db_session: AsyncSession
) -> AsyncGenerator[Callable[[str, str], Coroutine[Any, Any, User]], None]:
    """
    Async factory to create a user.
    Takes username and password, returns User object.
    """
    async def _create_user(username: str, plain_password: str) -> User:
        hashed_pw = get_password_hash(plain_password)
        new_user = User(
            username=username,
            email=f"{username}@test.com",
            hashed_password=hashed_pw,
            full_name=f"Test User {username}",
            is_active=True,
            role_id=1  # 'user' role
        )
        db_session.add(new_user)
        await db_session.commit()
        await db_session.refresh(new_user)
        return new_user

    yield _create_user

@pytest.fixture(scope="session", autouse=True)
def setup_test_database_schema():
    """
    Runs once per test session.
    Guarantees that all tables exist in the test database before any tests run.
    """
    async def _init_db():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            # Tell SQLAlchemy to look at your models and generate the CREATE TABLE statements
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()

    # We use our bulletproof synchronous wrapper so it doesn't fight Playwright!
    asyncio.run(_init_db())

@pytest.fixture(autouse=True)
def clean_database_before_test(request):
    """
    Automatically wipes all database tables before E2E tests ONLY.
    Integration tests use the db_session transaction rollback instead.
    """
    # ✅ Check if the test is inside the 'e2e' folder.
    # If it isn't, skip the truncate and just run the test!
    print(f"\n[DEBUG] Running test: {request.node.name} at {request.node.path}")
    if "e2e" not in str(request.node.path):
        yield
        return

    async def _truncate():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            # FIX: Filter out the 'roles' table so it survives the purge
            tables = [table.name for table in Base.metadata.sorted_tables if table.name != 'roles']

            if tables:
                table_string = ", ".join(tables)
                await conn.execute(text(f"TRUNCATE TABLE {table_string} RESTART IDENTITY CASCADE;"))
        await engine.dispose()

    asyncio.run(_truncate())

    yield # The Playwright test runs here

@pytest.fixture
def setup_user_circles_synchronous():
    """Seeds the database with circles and assigns the correct roles."""
    def _setup(username: str, circles_data: list[dict]):
        async def _insert():
            engine = create_async_engine(TEST_DATABASE_URL)
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session_maker() as session:
                # 1. Get the primary test user
                user_res = await session.execute(select(User).where(User.username == username))
                user = user_res.scalar_one()

                # 2. Get or create a dummy admin for circles the test user doesn't own
                admin_res = await session.execute(select(User).where(User.username == "circle_admin"))
                admin = admin_res.scalar_one_or_none()
                if not admin:
                    admin = User(username="circle_admin", email="admin@system.com", hashed_password="xxx")
                    session.add(admin)
                    await session.flush()

                # 3. Create the circles and membership records
                for row in circles_data:
                    role = row["role"].lower()

                    # If the user isn't the owner, the dummy admin owns it
                    circle_owner_id = user.id if role == "owner" else admin.id

                    circle = Circle(
                        name=row["circle_name"],
                        description=f"Automated test circle for {row['circle_name']}",
                        owner_id=circle_owner_id
                    )
                    session.add(circle)
                    await session.flush()

                    member = CircleMember(circle_id=circle.id, user_id=user.id, role=role)
                    session.add(member)

                await session.commit()
            await engine.dispose()

        asyncio.run(_insert())
    yield _setup

@pytest.fixture
def create_circle_post_synchronous():
    """Creates a post inside a specific circle."""
    def _create_post(circle_name: str, author_username: str, title: str, content: str):
        async def _insert():
            engine = create_async_engine(TEST_DATABASE_URL)
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session_maker() as session:
                user = (await session.execute(select(User).where(User.username == author_username))).scalar_one()
                circle = (await session.execute(select(Circle).where(Circle.name == circle_name))).scalar_one()

                post = Post(title=title, content=content, author_id=user.id, circle_id=circle.id)
                session.add(post)
                await session.commit()
            await engine.dispose()

        asyncio.run(_insert())
    yield _create_post

# ==========================================
# PYTEST MAGIC HOOK
# ==========================================
def pytest_collection_modifyitems(config, items):
    """
    This hook runs after Pytest reads the feature file but before the tests execute.
    It looks for any scenario tagged with @bug and safely marks it as an Expected Failure.
    """
    for item in items:
        # 'item.keywords' contains all the Gherkin tags!
        if "todo" in item.keywords:
            item.add_marker(
                pytest.mark.xfail(reason="Known backend todo: Implementation pending")
            )
        if "bug" in item.keywords:
            item.add_marker(
                pytest.mark.xfail(reason="Known backend bug: Fix pending")
            )
