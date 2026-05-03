# app/api/v1/endpoints/posts.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import RequireCirclePermission, RequirePostPermission
from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.core.logger import logger
from app.db.models import Circle, CircleMember, Post, User
from app.schemas.social import CircleRole, PostCreate, PostResponse

router = APIRouter(prefix="/posts", tags=["Posts"])

# --- DRY HELPER FUNCTION ---
def _build_post_response(post: Post) -> PostResponse:
    """Helper to consistently format a post using eager-loaded relationships."""
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_name=post.author.username if post.author else "Unknown",
        circle_id=post.circle_id,
        circle_name=post.circle.name if post.circle else None,
        created_at=post.created_at,
        updated_at=post.updated_at
    )
# ---------------------------


@router.get("/feed", response_model=list[PostResponse])
async def get_feed(
    http_request: Request,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> list[PostResponse]:
    """Get recent posts (Admins see all, users see their circles)"""

    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "content_management"],
        "event.action": "get_feed",
        "user.id": str(current_user.id),
        "source.ip": client_ip
    })

    # Check for Admin God Mode
    if current_user.role and current_user.role.name in ["admin", "superadmin"]:
        query = (
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.circle))
            .order_by(desc(Post.created_at))
            .offset(offset).limit(limit)
        )
    else:
        query = (
            select(Post)
            .join(CircleMember, Post.circle_id == CircleMember.circle_id)
            .where(CircleMember.user_id == current_user.id)
            .options(selectinload(Post.author), selectinload(Post.circle))
            .order_by(desc(Post.created_at))
            .offset(offset).limit(limit)
        )

    try:
        result = await db.execute(query)
        posts = result.scalars().all()

        return [_build_post_response(post) for post in posts]

    except Exception as e:
        # Log unexpected 500 crashes
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error while fetching circle posts")

        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> PostResponse:
    """Create a new post"""

    # 1. Initialize ECS Context
    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "content_management"],
        "event.action": "create_post",
        "user.id": str(current_user.id),
        "target.circle_id": str(post_data.circle_id) if post_data.circle_id else "none",
        "source.ip": client_ip
    })

    try:

        # Check permission from JSON body (can't use URL dependency here)
        if post_data.circle_id:
            membership = await db.execute(
                select(CircleMember)
                .where(CircleMember.circle_id == post_data.circle_id, CircleMember.user_id == current_user.id)
            )
            is_admin = current_user.role and current_user.role.name in ["admin", "superadmin"]

            if not membership.scalar_one_or_none() and not is_admin:
                # Log the unauthorized attempt before blocking it
                log.bind(event_outcome="failure").warning("Denied post creation: User not in target circle")
                raise HTTPException(status_code=403, detail="You are not a member of this circle")

        new_post = Post(
            title=post_data.title,
            content=post_data.content,
            author_id=current_user.id,
            circle_id=post_data.circle_id
        )
        db.add(new_post)
        await db.commit()

        # Re-fetch with relationships eager-loaded
        result = await db.execute(
            select(Post).options(selectinload(Post.author), selectinload(Post.circle)).where(Post.id == new_post.id)
        )
        return _build_post_response(result.scalar_one())

    except HTTPException:
        # Re-raise HTTPExceptions (like our 403) so they return cleanly to the client
        raise
    except Exception as e:
        # Catch and log unexpected 500 crashes
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error while creating post")

        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    # Only Author, Circle Member, or Admin can read
    post: Post = Depends(RequirePostPermission(action="read"))
) -> PostResponse:
    """Get a specific post"""
    return _build_post_response(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    # Only Author, Circle Mod/Owner, or Admin can delete
    post: Post = Depends(RequirePostPermission(action="delete")),
    current_user: User = Depends(get_current_user_from_session)
) -> None:

    # We only reach this line if authorization PASSED.
    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "content_management"],
        "event.action": "delete_post",
        "user.id": str(current_user.id),
        "target.post_id": str(post.id),
        "source.ip": client_ip
    })

    try:
        """Delete a post"""
        await db.delete(post)
        await db.commit()

        log.bind(event_outcome="success").info("Post successfully deleted")
        return None

    except Exception as e:
        # Log unexpected 500 crashes
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error while deleting post")

        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/circle/{circle_id}", response_model=list[PostResponse])
async def get_circle_posts(
    http_request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    # We reuse our Circle dependency here! Only circle members (or admins) can fetch the list.
    circle: Circle = Depends(RequireCirclePermission([CircleRole.OWNER, CircleRole.MODERATOR, CircleRole.MEMBER])),
    current_user: User = Depends(get_current_user_from_session)
) -> list[PostResponse]:
    """Get posts from a specific circle"""

    # We only reach this line if authorization PASSED.
    client_ip = http_request.client.host if http_request.client else "unknown"
    log = logger.bind(**{
        "event.category": ["social", "content_management"],
        "event.action": "get_circle_posts",
        "user.id": str(current_user.id),
        "target.circle_id": str(circle.id),
        "source.ip": client_ip
    })

    try:
        query = (
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.circle))
            .where(Post.circle_id == circle.id)
            .order_by(desc(Post.created_at))
            .offset(offset).limit(limit)
        )

        result = await db.execute(query)
        posts = result.scalars().all()

        return [_build_post_response(post) for post in posts]

    except Exception as e:
        # Log unexpected 500 crashes
        log.bind(**{
            "event.outcome": "failure",
            "error.type": type(e).__name__,
            "error.message": str(e)
        }).exception("Unexpected database error while fetching circle posts")

        raise HTTPException(status_code=500, detail="Internal server error") from e
