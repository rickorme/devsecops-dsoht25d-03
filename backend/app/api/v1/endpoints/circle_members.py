# app/api/v1/endpoints/circle_members.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireCirclePermission
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
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
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner, Moderator, or Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR]))
) -> MemberActionResponse:
    """Add a user to circle (owner/moderator/admin only)"""

    # 1. Check if user to add exists
    user_to_add = await db.get(User, request.user_id)
    if not user_to_add:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 2. Check if already a member (Evaluated efficiently in memory using the eager-loaded members list)
    if any(m.user_id == request.user_id for m in circle.members):
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

# ======================================================
# 2. REMOVE MEMBER FROM CIRCLE
# ======================================================
@router.delete("/{circle_id}/members/{user_id}", response_model=MemberActionResponse)
async def remove_member(
    user_id: int,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner, Moderator, or Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR]))
) -> MemberActionResponse:
    """Remove member from circle (owner/moderator/admin only)"""

    # 1. Find the target member in memory
    target_member = next((m for m in circle.members if m.user_id == user_id), None)
    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this circle")

    if target_member.role == CircleRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove the circle owner")

    # 2. Advanced ABAC logic: Moderators cannot remove other moderators.
    # We must check if the current user is a global admin to allow them to bypass this rule.
    is_admin = current_user.role and current_user.role.name in ["admin", "superadmin"]

    if not is_admin:
        current_membership = next((m for m in circle.members if m.user_id == current_user.id), None)
        if current_membership and current_membership.role == CircleRole.MODERATOR.value:
            if target_member.role == CircleRole.MODERATOR.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderators cannot remove other moderators")

    # 3. Get username for the response
    user = await db.get(User, user_id)
    username = user.username if user else "Unknown"

    await db.delete(target_member)
    await db.commit()

    return MemberActionResponse(
        success=True,
        message=f"Member {username} removed successfully",
        member=None
    )

# ======================================================
# 3. UPDATE MEMBER ROLE
# ======================================================
@router.put("/{circle_id}/members/{user_id}/role", response_model=MemberActionResponse)
async def update_member_role(
    user_id: int,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    # Dependency guarantees user is an Owner OR Global Admin
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER]))
) -> MemberActionResponse:
    """Change member's role (owner/admin only)"""

    # 1. Find the target member in memory
    target_member = next((m for m in circle.members if m.user_id == user_id), None)
    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this circle")

    if target_member.role == CircleRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change the circle owner's role")

    # 2. Update role
    old_role = target_member.role
    target_member.role = request.role.value
    await db.commit()

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
