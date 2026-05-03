# app/api/v1/endpoints/circles.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import RequireCirclePermission
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.core.logger import logger
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
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> list[CircleResponse]:
    """Get circles where current user is a member (Admins see all)"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "get_my_circles",
        "user.id": str(current_user.id),
        "source.ip": client_ip
    })

    try:
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

        responses = [await _build_circle_response(c, db) for c in circles]

        log.bind(event_outcome="success").info(f"Retrieved {len(responses)} circles for user")
        return responses

    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error fetching user circles")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/", response_model=CircleResponse, status_code=status.HTTP_201_CREATED)
async def create_circle(
    circle_data: CircleCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> CircleResponse:
    """Create a new circle"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "create_circle",
        "user.id": str(current_user.id),
        "source.ip": client_ip
    })

    try:
        existing = await db.execute(select(Circle).where(Circle.name == circle_data.name))
        if existing.scalar_one_or_none():
            log.bind(event_outcome="failure").warning("Circle creation failed: Name already exists")
            raise HTTPException(status_code=400, detail="Circle name already exists")

        new_circle = Circle(name=circle_data.name, description=circle_data.description, owner_id=current_user.id)
        db.add(new_circle)
        await db.flush()

        owner_member = CircleMember(circle_id=new_circle.id, user_id=current_user.id, role=CircleRole.OWNER.value)
        db.add(owner_member)
        await db.commit()

        result = await db.execute(select(Circle).options(selectinload(Circle.members)).where(Circle.id == new_circle.id))
        response = await _build_circle_response(result.scalar_one(), db)

        log.bind(**{"event.outcome": "success", "target.circle_id": str(response.id)}).info("Circle successfully created")
        return response

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error creating circle")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{circle_id}", response_model=CircleResponse)
async def get_circle(
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    # UPDATED: Explicitly set action="read"
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR, CircleRole.MEMBER], action="read"))
) -> CircleResponse:
    """Get circle details by ID"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "get_circle",
        "user.id": str(current_user.id),
        "target.circle_id": str(circle.id),
        "source.ip": client_ip
    })

    try:
        response = await _build_circle_response(circle, db)
        return response
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error retrieving circle details")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put("/{circle_id}", response_model=CircleResponse)
async def update_circle(
    circle_data: CircleCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    # UPDATED: Explicitly set action="update"
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER], action="update"))
) -> CircleResponse:
    """Update circle details (owner only)"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "update_circle",
        "user.id": str(current_user.id),
        "target.circle_id": str(circle.id),
        "source.ip": client_ip
    })

    try:
        circle.name = circle_data.name
        circle.description = circle_data.description
        await db.commit()

        result = await db.execute(
            select(Circle)
            .options(selectinload(Circle.members))
            .where(Circle.id == circle.id)
        )
        response = await _build_circle_response(result.scalar_one(), db)

        log.bind(event_outcome="success").info("Circle details successfully updated")
        return response

    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error updating circle")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{circle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_circle(
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    # UPDATED: Explicitly set action="delete"
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER], action="delete"))
) -> None:
    """Delete a circle (owner only)"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "delete_circle",
        "user.id": str(current_user.id),
        "target.circle_id": str(circle.id),
        "source.ip": client_ip
    })

    try:
        await db.delete(circle)
        await db.commit()

        log.bind(event_outcome="success").info("Circle successfully deleted")
        return None

    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error deleting circle")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put("/{circle_id}/name", response_model=CircleResponse)
async def update_circle_name(
    request_data: dict,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    # UPDATED: Explicitly set action="update"
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER], action="update"))
) -> CircleResponse:
    """Update circle name (owner only)"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "circle_management"],
        "event.action": "update_circle_name",
        "user.id": str(current_user.id),
        "target.circle_id": str(circle.id),
        "source.ip": client_ip
    })

    try:
        new_name = request_data.get("name")
        if not new_name or len(new_name) < 3:
            log.bind(event_outcome="failure").warning("Circle rename failed: Name too short")
            raise HTTPException(status_code=400, detail="Name must be at least 3 characters")

        existing = await db.execute(select(Circle).where(Circle.name == new_name, Circle.id != circle.id))
        if existing.scalar_one_or_none():
            log.bind(event_outcome="failure").warning("Circle rename failed: Name already exists")
            raise HTTPException(status_code=400, detail="A circle with this name already exists")

        circle.name = new_name
        await db.commit()

        result = await db.execute(
            select(Circle)
            .options(selectinload(Circle.members))
            .where(Circle.id == circle.id)
        )
        response = await _build_circle_response(result.scalar_one(), db)

        log.bind(event_outcome="success").info("Circle name successfully updated")
        return response

    except HTTPException:
        raise
    except Exception as e:
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error updating circle name")
        raise HTTPException(status_code=500, detail="Internal server error") from e
