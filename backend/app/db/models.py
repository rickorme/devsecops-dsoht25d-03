"""
User model for authentication (Async SQLAlchemy 2.0)
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Role(Base):
    """
    Role model for system and circle permissions
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # One-to-many relationship back to users
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    """
    User model for authentication with async PostgreSQL

    Attributes:
        id: Unique user identifier
        username: User's username (UNIQUE, PRIMARY LOGIN FIELD)
        email: User's email (UNIQUE, optional/display only)
        full_name: User's full name
        hashed_password: Argon2 hashed password
        is_active: Whether user account is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Foreign key and relationship to Role
    # We use server_default="1" so if there are already users in the DB, Alembic won't crash when migrating
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), server_default="1", nullable=False)
    role: Mapped["Role"] = relationship(back_populates="users")

    # Relationships
    owned_circles: Mapped[list["Circle"]] = relationship(back_populates="owner",
                                                         foreign_keys="Circle.owner_id")
    circle_memberships: Mapped[list["CircleMember"]] = relationship(back_populates="user")
    posts: Mapped[list["Post"]] = relationship(back_populates="author")

class Circle(Base):
    """
    Circle model for groups of users
    """
    __tablename__ = "circles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    owner: Mapped["User"] = relationship(back_populates="owned_circles", foreign_keys=[owner_id])
    members: Mapped[list["CircleMember"]] = relationship(back_populates="circle")
    posts: Mapped[list["Post"]] = relationship(back_populates="circle")


class CircleMember(Base):
    """
    Association table for Circle members
    """
    __tablename__ = "circle_members"

    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # "owner","moderator","member"
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    circle: Mapped["Circle"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="circle_memberships")


class Post(Base):
    """
    Post model for user content
    """
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    circle_id: Mapped[int | None] = mapped_column(ForeignKey("circles.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                        onupdate=func.now())

    # Relationships
    author: Mapped["User"] = relationship(back_populates="posts")
    circle: Mapped["Circle | None"] = relationship(back_populates="posts")

# Session model for session-based authentication (alternative to JWT)
class UserSession(Base):
    """
    User session model for session-based authentication
    Frontend team requested sessions instead of just JWT tokens
    """
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"
