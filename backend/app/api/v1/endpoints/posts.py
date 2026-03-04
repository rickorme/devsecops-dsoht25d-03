from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_from_session
from app.core.db import get_db
from app.db.models import Circle, CircleMember, Post, User
from app.schemas.social import PostCreate, PostResponse

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/feed", response_model=list[PostResponse])
async def get_feed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    limit: int = 20,
    offset: int = 0
) -> list[PostResponse]:
    """
    Get recent posts from user's circles (dashboard feed)
    Returns posts from circles where user is a member
    """
    # 1. Get all circles where user is a member
    member_circles = await db.execute(
        select(CircleMember.circle_id).where(CircleMember.user_id == current_user.id)
    )
    circle_ids = [row[0] for row in member_circles.fetchall()]

    if not circle_ids:
        return []  # User has no circles, return empty feed

    # 2. Get posts from those circles with author AND circle info
    posts_result = await db.execute(
        select(Post, User.username, Circle.name)
        .join(User, Post.author_id == User.id)
        .join(Circle, Post.circle_id == Circle.id, isouter=True)
        .where(Post.circle_id.in_(circle_ids))
        .order_by(desc(Post.created_at))
        .offset(offset)
        .limit(limit)
    )

    # 3. Convert to response model with REAL author names and circle names
    feed_posts = []

    for post, author_name, circle_name in posts_result:
        feed_posts.append(
            PostResponse(
                id=post.id,
                title=post.title,
                content=post.content,
                author_id=post.author_id,
                author_name=author_name,
                circle_id=post.circle_id,
                circle_name=circle_name,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
        )

    return feed_posts


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> PostResponse:
    """
    Create a new post (in a circle or public)
    """
    circle_name = None  # Initialize circle_name to None

    # Check if user has permission to post in this circle
    if post_data.circle_id:
        # Verify user is member of the circle
        membership = await db.execute(
            select(CircleMember)
            .where(
                CircleMember.circle_id == post_data.circle_id,
                CircleMember.user_id == current_user.id
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this circle"
            )

        circle = await db.get(Circle, post_data.circle_id)
        circle_name = circle.name if circle else None

    # Create post
    new_post = Post(
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
        circle_id=post_data.circle_id
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    return PostResponse(
        id=new_post.id,
        title=new_post.title,
        content=new_post.content,
        author_id=new_post.author_id,
        author_name=current_user.username,
        circle_id=new_post.circle_id,
        circle_name=circle_name,
        created_at=new_post.created_at,
        updated_at=new_post.updated_at
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> PostResponse:
    """
    Get a specific post by ID
    """

    result = await db.execute(
        select(Post, User.username, Circle.name)
        .join(User, Post.author_id == User.id)
        .join(Circle, Post.circle_id == Circle.id, isouter=True)
        .where(Post.id == post_id)
    )

    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    post, author_name, circle_name = row

    # Check if post is in a circle - verify user is member
    if post.circle_id:
        membership = await db.execute(
            select(CircleMember)
            .where(
                CircleMember.circle_id == post.circle_id,
                CircleMember.user_id == current_user.id
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this post"
            )

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_name=author_name,
        circle_id=post.circle_id,
        circle_name=circle_name,
        created_at=post.created_at,
        updated_at=post.updated_at
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
) -> None:
    """
    Delete a post (author, moderator, or owner only)
    """
    post = await db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check permissions
    can_delete = False

    if post.author_id == current_user.id:
        can_delete = True  # Author can delete
    elif post.circle_id:
        # Check if user is moderator or owner of the circle
        membership = await db.execute(
            select(CircleMember)
            .where(
                CircleMember.circle_id == post.circle_id,
                CircleMember.user_id == current_user.id
            )
        )
        member = membership.scalar_one_or_none()
        if member and member.role in ["owner", "moderator"]:
            can_delete = True

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this post"
        )

    await db.delete(post)
    await db.commit()


@router.get("/circle/{circle_id}", response_model=list[PostResponse])
async def get_circle_posts(
    circle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
    limit: int = 50,
    offset: int = 0
) -> list[PostResponse]:
    """
    Get posts from a specific circle
    User must be a member of the circle
    """
    # Check if user is a member
    membership = await db.execute(
        select(CircleMember)
        .where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == current_user.id
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this circle"
        )

    # Get the circle name (ia o singură dată)
    circle = await db.get(Circle, circle_id)

    # Get posts with author info
    posts_result = await db.execute(
        select(Post, User.username)
        .join(User, Post.author_id == User.id)
        .where(Post.circle_id == circle_id)
        .order_by(desc(Post.created_at))
        .offset(offset)
        .limit(limit)
    )

    # Convert to response model with REAL author names and circle name
    circle_posts = []
    for post, author_name in posts_result:
        circle_posts.append(
            PostResponse(
                id=post.id,
                title=post.title,
                content=post.content,
                author_id=post.author_id,
                author_name=author_name,
                circle_id=post.circle_id,
                circle_name=circle.name if circle else None,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
        )

    return circle_posts
