# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies import RequireRole
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.core.logger import logger
from app.db.models import CircleMember, User
from app.schemas.auth import UserResponse
from app.schemas.social import UserSearchResponse

router = APIRouter(prefix="/users", tags=["Users"])

# ======================================================
# GET ALL USERS (with pagination)
# ======================================================
@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> list[UserResponse]:
    """
    Get all users with pagination
    - Excludes the current user from the list
    - Authenticated users only
    - Masks roles for non-admin users (Security)
    """
    # 1. Determine if the requester is an admin
    is_admin = current_user.role and current_user.role.name in ["admin", "superadmin"]

    # 2. Build the query
    query = (
        select(User)
        .where(User.id != current_user.id)
        .offset(skip)
        .limit(limit)
    )

    # 3. Only eager-load the roles from the DB if an admin is asking for them!
    if is_admin:
        query = query.options(joinedload(User.role))

    result = await db.execute(query)
    users = result.scalars().all()

    # 4. Conditionally expose the role data
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            role=user.role.name if is_admin and user.role else None # Masked for standard users!
        )
        for user in users
    ]

# ======================================================
# SEARCH USERS (to add to circle)
# ======================================================
@router.get("/search", response_model=list[UserSearchResponse])
async def search_users(
    query: str,
    circle_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> list[UserSearchResponse]:

    # Initialize ECS Context
    client_ip = request.client.host if request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["users", "search"],
        "event.action": "search_circle_candidates",
        "user.id": str(current_user.id),
        "source.ip": client_ip,
        "circle.id": circle_id
    })

    try:
        # 1. Verify current user has permission
        permission_check = await db.execute(
            select(CircleMember)
            .where(
                CircleMember.circle_id == circle_id,
                CircleMember.user_id == current_user.id,
                CircleMember.role.in_(["owner", "moderator"])
            )
        )
        if not permission_check.scalar_one_or_none():
            log.bind(event_outcome="failure").warning("Unauthorized search attempt blocked")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only circle owners and moderators can search for new members"
            )

        # 2. If query is empty, return empty list
        if not query or query.strip() == "":
            return []

        # 3. Get users already in the circle
        existing_members = await db.execute(
            select(CircleMember.user_id).where(CircleMember.circle_id == circle_id)
        )
        existing_ids = [row[0] for row in existing_members.fetchall()]

        # 4. Search users
        stmt = select(User).where(
        User.id != current_user.id,
        User.username.ilike(f"%{query}%")).limit(20)

        # Exclude existing members if any
        if existing_ids:
            stmt = stmt.where(User.id.not_in(existing_ids))

        result = await db.execute(stmt)
        users = result.scalars().all()

        log.bind(event_outcome="success").info(f"Search returned {len(users)} users")

        # 5. Return results
        return [
            UserSearchResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_already_member=False
            )
            for user in users
        ]

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected error during user search")
        raise HTTPException(status_code=500, detail="Internal server error during search") from e


# ======================================================
# DELETE USER (admins only)
# ======================================================
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # The Magic Line: This injects the user ONLY if they are an admin/superadmin
    current_admin: User = Depends(RequireRole(["admin", "superadmin"]))
) -> None:

    """
    Delete a user account.
    Requires 'admin' or 'superadmin' role.
    """
    client_ip = request.client.host if request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["iam", "admin_action"],
        "event.action": "delete_user",
        "user.id": str(current_admin.id),
        "target.user_id": str(user_id),
        "source.ip": client_ip
    })

    try:
        # 1. Prevent admins from accidentally deleting themselves
        if user_id == current_admin.id:
            log.bind(event_outcome="failure").warning("Admin attempted self-deletion")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot delete their own accounts via this endpoint."
            )

        # 2. Find the target user
        result = await db.execute(select(User).where(User.id == user_id))
        user_to_delete = result.scalar_one_or_none()

        if not user_to_delete:
            log.bind(event_outcome="failure").warning("Target user for deletion not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # 3. Delete the user
        await db.delete(user_to_delete)
        await db.commit()

        log.bind(event_outcome="success").info(f"Admin successfully deleted user {user_id}")

        # Returning None with a 204 status code is the standard RESTful way
        # to indicate a successful deletion without returning a body.
        return None

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected error during user deletion")
        raise HTTPException(status_code=500, detail="Internal server error during deletion") from e
