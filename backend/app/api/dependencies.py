# app/api/dependencies.py
from fastapi import Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_user_from_session
from app.db.models import User


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

# --- Future ABAC Example (For Circles/Posts) ---
# async def require_post_owner(post_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_from_session)):
#     post = await db.execute(...)
#     if post.author_id != current_user.id:
#         raise HTTPException(status_code=403, detail="You do not own this post")
#     return post
