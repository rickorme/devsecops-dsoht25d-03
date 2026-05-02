# app/api/v1/endpoints/circle_members.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireCirclePermission
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.core.logger import logger
from app.db.models import Circle, CircleMember, User
from app.schemas.social import (
    AddMemberRequest,
    CircleMemberResponse,
    CircleRole,
    MemberActionResponse,
    UpdateRoleRequest,
)

router = APIRouter(prefix="/circles", tags=["Circle Members"])

# ======================================================
# 1. ADD MEMBER TO CIRCLE
# ======================================================
@router.post("/{circle_id}/members", status_code=201, response_model=MemberActionResponse)
async def add_member(
    request: AddMemberRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner, Moderator, or Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR])),
    current_user: User = Depends(get_current_user_from_session)
) -> MemberActionResponse:
    """Add a user to circle (owner/moderator/admin only)"""

    client_ip = http_request.client.host if http_request.client else "unknown"

    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "add_member",
        "user.id": str(current_user.id),
        "target.user_id": str(request.user_id),
        "circle.id": circle.id,
        "source.ip": client_ip
    })

    try:
        # 1. Check if user to add exists
        user_to_add = await db.get(User, request.user_id)
        if not user_to_add:
            log.bind(event_outcome="failure").warning("Attempted to add non-existent member")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 2. Check if already a member (Evaluated efficiently in memory using the eager-loaded members list)
        if any(m.user_id == request.user_id for m in circle.members):
            log.bind(event_outcome="failure").warning("Attempted to add existing circle member")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member of this circle")

        # 3. Add new member
        new_member = CircleMember(
            circle_id=circle.id,
            user_id=request.user_id,
            role=CircleRole.MEMBER.value,
            joined_at=datetime.now()
        )
        db.add(new_member)
        await db.commit()

        log.bind(event_outcome="success").info(f"Member {user_to_add.username} successfully added to circle")

        return MemberActionResponse(
            success=True,
            message="Member added successfully",
            member=CircleMemberResponse(
                circle_id=new_member.circle_id,
                user_id=new_member.user_id,
                username=user_to_add.username,
                role=CircleRole(new_member.role),
                joined_at=new_member.joined_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected error adding circle member")
        raise HTTPException(status_code=500, detail="Internal server error during member addition") from e

# ======================================================
# 2. REMOVE MEMBER FROM CIRCLE
# ======================================================
@router.delete("/{circle_id}/members/{user_id}", response_model=MemberActionResponse)
async def remove_member(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner, Moderator, or Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR]))
) -> MemberActionResponse:
    """Remove member from circle (owner/moderator/admin only)"""

    client_ip = request.client.host if request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "remove_member",
        "user.id": str(current_user.id),
        "target.user_id": str(user_id),
        "circle.id": circle.id,
        "source.ip": client_ip
    })

    try:

        # 1. Find the target member in memory
        target_member = next((m for m in circle.members if m.user_id == user_id), None)
        if not target_member:
            log.bind(event_outcome="failure").warning("Attempted to remove non-existent member")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this circle")

        if target_member.role == CircleRole.OWNER.value:
            log.bind(event_outcome="failure").warning("Attempted to remove circle owner")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove the circle owner")

        # 2. Advanced ABAC logic: Moderators cannot remove other moderators.
        # We must check if the current user is a global admin to allow them to bypass this rule.
        is_admin = current_user.role and current_user.role.name in ["admin", "superadmin"]

        if not is_admin:
            current_membership = next((m for m in circle.members if m.user_id == current_user.id), None)
            if current_membership and current_membership.role == CircleRole.MODERATOR.value:
                if target_member.role == CircleRole.MODERATOR.value:
                    log.bind(event_outcome="failure").warning("Moderator attempted to remove another moderator")
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderators cannot remove other moderators")

        # 3. Get username for the response
        user = await db.get(User, user_id)
        username = user.username if user else "Unknown"

        await db.delete(target_member)
        await db.commit()

        log.bind(event_outcome="success").info(f"Member {username} successfully removed from circle")

        return MemberActionResponse(
            success=True,
            message=f"Member {username} removed successfully",
            member=None
        )

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected error removing circle member")
        raise HTTPException(status_code=500, detail="Internal server error during member removal") from e

# ======================================================
# 3. UPDATE MEMBER ROLE
# ======================================================
@router.put("/{circle_id}/members/{user_id}/role", response_model=MemberActionResponse)
async def update_member_role(
    user_id: int,
    request: UpdateRoleRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner OR Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER])),
    current_user: User = Depends(get_current_user_from_session)
) -> MemberActionResponse:
    """Change member's role (owner/admin only)"""

    client_ip = http_request.client.host if http_request.client else "unknown"

    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "update_member_role",
        "user.id": str(current_user.id),
        "target.user_id": str(user_id),
        "circle.id": circle.id,
        "source.ip": client_ip
    })

    try:
        # 1. Find the target member in memory
        target_member = next((m for m in circle.members if m.user_id == user_id), None)
        if not target_member:
            log.bind(event_outcome="failure").warning("Attempted to update role for non-existent member")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this circle")

        if target_member.role == CircleRole.OWNER.value:
            log.bind(event_outcome="failure").warning("Attempted to change circle owner's role")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change the circle owner's role")

        # 2. Update role
        old_role = target_member.role
        target_member.role = request.role.value
        await db.commit()

        log.bind(event_outcome="success").info(f"Member {target_member.user_id} role changed from {old_role} to {request.role.value}")

        # 3. Get username for the response
        user = await db.get(User, user_id)
        username = user.username if user else "Unknown"

        return MemberActionResponse(
            success=True,
            message=f"Role changed from {old_role} to {request.role.value}",
            member=CircleMemberResponse(
                circle_id=target_member.circle_id,
                user_id=target_member.user_id,
                username=username,
                role=CircleRole(target_member.role),
                joined_at=target_member.joined_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected error updating circle member role")
        raise HTTPException(status_code=500, detail="Internal server error during member role update") from e
