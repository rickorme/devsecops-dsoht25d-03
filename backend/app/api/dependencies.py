# app/api/dependencies.py
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.core.logger import logger
from app.db.models import Circle, CircleMember, Post, User
from app.schemas.social import CircleRole


class RequireRole:
    """
    RBAC Dependency Factory
    Ensures the current user has one of the allowed roles.
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user_from_session)) -> User:
        # Check if the user has a role, and if it's in our allowed list
        if not current_user.role or current_user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to perform this action"
            )
        return current_user


class RequireCirclePermission:
    """
    Unified ABAC/RBAC Dependency
    Checks if a user has a specific role in a circle OR is a global admin.
    """
    def __init__(self, allowed_circle_roles: list[CircleRole], action: str = "read"):
        self.allowed_circle_roles = allowed_circle_roles
        self.action = action  # "read", "update" or "delete"

    async def __call__(
        self,
        circle_id: int, # FastAPI automatically extracts this from the URL path!
        request: Request,
        current_user: User = Depends(get_current_user_from_session),
        db: AsyncSession = Depends(get_db)
    ) -> Circle:

        # 1. Initialize ECS Context for Authorization Audit
        client_ip = request.client.host if request.client else "unknown"
        log = logger.bind(**{
            "event.category": ["iam", "authorization"],
            "event.action": f"circle_{self.action}",
            "user.id": str(current_user.id),
            "target.circle_id": str(circle_id),
            "source.ip": client_ip
        })

        # 1. Look up the requested circle WITH members eager-loaded
        result = await db.execute(
            select(Circle)
            .options(selectinload(Circle.members))
            .where(Circle.id == circle_id)
        )
        circle = result.scalar_one_or_none()

        if not circle:
            log.bind(event_outcome="failure").warning(f"Attempted to {self.action} non-existent circle")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Circle not found"
            )

        # 2. RBAC OVERRIDE (Global Admin Bypass)
        if current_user.role and current_user.role.name in ["admin", "superadmin"]:
            return circle # Admins skip the circle membership check entirely!

        # 3. ABAC CHECK (Circle Membership)
        member_result = await db.execute(
            select(CircleMember)
            .where(CircleMember.circle_id == circle_id)
            .where(CircleMember.user_id == current_user.id)
        )
        membership = member_result.scalar_one_or_none()

        # 4. Enforce Permissions
        if not membership:
            log.bind(event_outcome="failure").warning(f"Denied {self.action}: User not a member of the circle")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this circle"
            )

        if membership.role not in [role.value for role in self.allowed_circle_roles]:
            log.bind(event_outcome="failure").warning(f"Denied {self.action}: Insufficient circle permissions")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient circle permissions to perform this action"
            )

        return circle

class RequirePostPermission:
    """
    Unified ABAC/RBAC Dependency for Posts
    Allows access if: Global Admin OR Post Author OR has required Circle Role.
    """
    def __init__(self, action: str = "read"):
        self.action = action  # "read", "update" or "delete"

    async def __call__(
        self,
        post_id: int,
        request: Request,
        current_user: User = Depends(get_current_user_from_session),
        db: AsyncSession = Depends(get_db)
    ) -> Post:

        # 1. Initialize ECS Context for Authorization Audit
        client_ip = request.client.host if request.client else "unknown"
        log = logger.bind(**{
            "event.category": ["iam", "authorization"],
            "event.action": f"post_{self.action}",
            "user.id": str(current_user.id),
            "target.post_id": str(post_id),
            "source.ip": client_ip
        })

        # 1. Fetch Post with eager-loaded author and circle data
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.circle))
            .where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            log.bind(event_outcome="failure").warning(f"Attempted to {self.action} non-existent post")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # 2. RBAC OVERRIDE (Global Admin Bypass)
        if current_user.role and current_user.role.name in ["admin", "superadmin"]:
            return post

        # 3. ABAC OVERRIDE (Author Bypass)
        if post.author_id == current_user.id:
            return post

        # 4. ABAC INHERITED (Circle Roles)
        if post.circle_id:
            member_result = await db.execute(
                select(CircleMember)
                .where(CircleMember.circle_id == post.circle_id)
                .where(CircleMember.user_id == current_user.id)
            )
            membership = member_result.scalar_one_or_none()

            if not membership:
                log.bind(event_outcome="failure").warning(f"Denied {self.action}: User not in circle")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this post")

            # If deleting, require elevated circle privileges
            if self.action == "delete" and membership.role not in ["owner", "moderator"]:
                log.bind(event_outcome="failure").warning(f"Denied {self.action}: Insufficient circle privileges")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this post")

            return post

        # 5. Public Posts
        if self.action == "delete":
            log.bind(event_outcome="failure").warning(f"Denied {self.action}: Cannot delete public post")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this post")

        return post
