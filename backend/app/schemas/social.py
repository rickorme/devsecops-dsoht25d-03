"""
Social feature schemas
Request and response models for Posts, Circles, and Circle Members
"""
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ======================================================
# POST SCHEMAS
# ======================================================

class PostBase(BaseModel):
    """Base schema for posts with common fields"""
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)


class PostCreate(PostBase):
    """Schema for creating a new post"""
    circle_id: int | None = Field( None,
                                  description="Optional Circle ID if posting to a circle")


class PostResponse(PostBase):
    """Schema for post data in API responses"""
    id: int
    author_id: int
    author_name: str | None = Field(None,
                                    description="Username of author")
    circle_id: int | None
    circle_name: str | None = Field(None,
                                   description="Name of the circle if post is in a circle")
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# CIRCLE SCHEMAS
# ======================================================

class CircleBase(BaseModel):
    """Base schema for circles with common fields"""
    name: str = Field(..., min_length=3, max_length=50)
    description: str | None = Field(None, max_length=255)


class CircleCreate(CircleBase):
    """Schema for creating a new circle"""
    pass

class UpdateCircleNameRequest(BaseModel):
    """Request schema for updating circle name"""
    name: str = Field(..., min_length=3, max_length=50)


class CircleRole(StrEnum):
    """Enum for circle member roles"""
    OWNER = "owner"
    MODERATOR = "moderator"
    MEMBER = "member"


class CircleMemberResponse(BaseModel):
    circle_id: int
    user_id: int
    username: str | None = Field(None, description="Username of member")
    role: CircleRole
    badge: str | None = Field(None, description="👑, 🛡️, 👤 - calculated from role")
    joined_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )

    def __init__(self, **data: Any) -> None:
        # Extract fields needed for badge calculation
        circle_id = data.get('circle_id')
        user_id = data.get('user_id')
        username = data.get('username')
        role = data.get('role')
        joined_at = data.get('joined_at')

        # Build init data for BaseModel initialization
        init_data = {
            'circle_id': circle_id,
            'user_id': user_id,
            'username': username,
            'role': role,
            'joined_at': joined_at
        }

        # Initialize BaseModel
        super().__init__(**init_data)

        # Calculate badge based on role
        badge_map = {
            CircleRole.OWNER: "👑",
            CircleRole.MODERATOR: "🛡️",
            CircleRole.MEMBER: "👤"
        }
        self.badge = badge_map.get(self.role, "👤")

class CircleResponse(CircleBase):
    """Schema for circle data in API responses"""
    id: int
    owner_id: int
    owner_name: str | None = Field(None, description="Username of owner")
    members: list[CircleMemberResponse] | None = Field(None, description="Circle members")
    member_count: int | None = Field(None, description="Total number of members")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# CIRCLE MEMBER MANAGEMENT SCHEMAS
# ======================================================

class CircleMemberUpdate(BaseModel):
    """Schema for updating a member's role (owner/moderator only)"""
    role: CircleRole


class UserSearchResponse(BaseModel):
    """Schema for user search results when adding members to a circle"""
    id: int
    username: str
    email: str
    is_already_member: bool = Field(False,
                                    description="Whether user is already in the circle")


class AddMemberRequest(BaseModel):
    """Request schema for adding a new member to a circle"""
    user_id: int


class UpdateRoleRequest(BaseModel):
    """Request schema for updating a member's role"""
    role: CircleRole  # Can be 'moderator' or 'member' (owner cannot be assigned)


class MemberActionResponse(BaseModel):
    """Response schema for member management actions (add/remove/update)"""
    success: bool
    message: str
    member: CircleMemberResponse | None = None


# ======================================================
# ADDITIONAL CIRCLE SCHEMAS (for future features)
# ======================================================

class CirclePrivacyUpdate(BaseModel):
    """Schema for updating circle privacy settings (owner only)"""
    is_private: bool


class CircleJoinRequest(BaseModel):
    """Schema for requesting to join a private circle"""
    message: str | None = Field(None, max_length=200)


class CircleJoinResponse(BaseModel):
    """Schema for circle join request response"""
    request_id: int
    user_id: int
    username: str
    status: str  # 'pending', 'approved', 'rejected'
    created_at: datetime
