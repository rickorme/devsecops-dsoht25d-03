from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Create an asynchronous engine to connect to the PostgreSQL database
# The DATABASE_URL is loaded from settings, which defaults to the local dev container DB
# or can be overridden by an environment variable (e.g., for Railway).
# We want to make sure the URL is in the correct format for asyncpg, which SQLAlchemy uses for async PostgreSQL connections.
# If the URL starts with "postgresql://", we replace it with "postgresql+asyncpg://".
# This is necessary because SQLAlchemy needs the "asyncpg" driver specified in the URL to know to use it for asynchronous operations.
db_url = str(settings.DATABASE_URL)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url, echo=True)

# Create a sessionmaker for asynchronous sessions
# expire_on_commit=False prevents objects from being expired after commit,
# which can be useful for accessing attributes outside of the session.
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevents lazy loading issues with async PostgreSQL
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an asynchronous database session.

    Yields an AsyncSession object that can be used for database operations.
    The session is automatically closed after the request is finished.
    """
    async with AsyncSessionLocal() as session:
        yield session
