# app/api/v1/endpoints/circles.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import RequireCirclePermission
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.db.models import Circle, CircleMember, User
from app.schemas.social import (
    CircleCreate,
    CircleMemberResponse,
    CircleResponse,
    CircleRole,
)

router = APIRouter(prefix="/circles", tags=["Circles"])

# --- DRY HELPER FUNCTION ---
async def _build_circle_response(circle: Circle, db: AsyncSession) -> CircleResponse:
    """Helper to consistently format a circle with its members and badges."""
    member_responses = []
    for member in circle.members:
        user_result = await db.get(User, member.user_id)
        if not user_result:
            continue

        role_enum = CircleRole(member.role) if isinstance(member.role, str) else member.role
        badge = {
            CircleRole.OWNER: "👑",
            CircleRole.MODERATOR: "🛡️",
            CircleRole.MEMBER: "👤"
        }.get(role_enum, "👤")

        member_responses.append(
            CircleMemberResponse(
                circle_id=member.circle_id,
                user_id=member.user_id,
                username=user_result.username,
                role=role_enum,
                badge=badge,
                joined_at=member.joined_at
            )
        )

    owner = await db.get(User, circle.owner_id)
    return CircleResponse(
        id=circle.id,
        name=circle.name,
        description=circle.description,
        owner_id=circle.owner_id,
        owner_name=owner.username if owner else None,
        members=member_responses,
        member_count=len(circle.members),
        created_at=circle.created_at
    )
# ---------------------------

@router.get("/my", response_model=list[CircleResponse])
async def get_my_circles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> list[CircleResponse]:
    """Get circles where current user is a member (Admins see all)"""
    if current_user.role and current_user.role.name in ["admin", "superadmin"]:
        query = select(Circle).options(selectinload(Circle.members)).order_by(Circle.created_at.desc())
    else:
        query = (
            select(Circle)
            .join(CircleMember, Circle.id == CircleMember.circle_id)
            .where(CircleMember.user_id == current_user.id)
            .options(selectinload(Circle.members))
            .order_by(Circle.created_at.desc())
        )

    result = await db.execute(query)
    circles = result.scalars().all()

    # Use our helper function for every circle
    return [await _build_circle_response(c, db) for c in circles]


@router.post("/", response_model=CircleResponse, status_code=status.HTTP_201_CREATED)
async def create_circle(
    circle_data: CircleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> CircleResponse:
    """Create a new circle"""
    existing = await db.execute(select(Circle).where(Circle.name == circle_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Circle name already exists")

    new_circle = Circle(name=circle_data.name, description=circle_data.description, owner_id=current_user.id)
    db.add(new_circle)
    await db.flush()

    owner_member = CircleMember(circle_id=new_circle.id, user_id=current_user.id, role=CircleRole.OWNER)
    db.add(owner_member)
    await db.commit()

    # Re-fetch with members loaded to use our helper
    result = await db.execute(select(Circle).options(selectinload(Circle.members)).where(Circle.id == new_circle.id))
    return await _build_circle_response(result.scalar_one(), db)


@router.get("/{circle_id}", response_model=CircleResponse)
async def get_circle(
    db: AsyncSession = Depends(get_db),
    # ANY member (or an admin) can view the circle
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR, CircleRole.MEMBER]))
) -> CircleResponse:
    """Get circle details by ID"""
    return await _build_circle_response(circle, db)


@router.put("/{circle_id}", response_model=CircleResponse)
async def update_circle(
    circle_data: CircleCreate,
    db: AsyncSession = Depends(get_db),
    # ONLY the Owner (or an admin) can update the description
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER]))
) -> CircleResponse:
    """Update circle details (owner only)"""
    circle.name = circle_data.name
    circle.description = circle_data.description
    await db.commit()
    # Re-fetch the circle with its members eagerly loaded
    result = await db.execute(
        select(Circle)
        .options(selectinload(Circle.members))
        .where(Circle.id == circle.id)
    )
    return await _build_circle_response(result.scalar_one(), db)


@router.delete("/{circle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_circle(
    db: AsyncSession = Depends(get_db),
    # ONLY the Owner (or an admin) can delete
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER]))
) -> None:
    """Delete a circle (owner only)"""
    await db.delete(circle)
    await db.commit()


@router.put("/{circle_id}/name", response_model=CircleResponse)
async def update_circle_name(
    request: dict,
    db: AsyncSession = Depends(get_db),
    # ONLY the Owner (or an admin) can rename
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER]))
) -> CircleResponse:
    """Update circle name (owner only)"""
    new_name = request.get("name")
    if not new_name or len(new_name) < 3:
        raise HTTPException(status_code=400, detail="Name must be at least 3 characters")

    existing = await db.execute(select(Circle).where(Circle.name == new_name, Circle.id != circle.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A circle with this name already exists")

    circle.name = new_name
    await db.commit()
    # Re-fetch the circle with its members eagerly loaded
    result = await db.execute(
        select(Circle)
        .options(selectinload(Circle.members))
        .where(Circle.id == circle.id)
    )
    return await _build_circle_response(result.scalar_one(), db)
