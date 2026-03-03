import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.security import get_password_hash
from app.db.models import Circle, CircleMember, Post, User


async def create_test_data() -> None:
    """Create test users, circles, and posts for E2E tests"""
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        email = "test@example.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"Creating test user: {email}")

            # 1. Create test user
            new_user = User(
                username="testuser",
                email=email,
                full_name="Test User",
                hashed_password=get_password_hash("Password123!"),
                is_active=True,
            )
            session.add(new_user)
            await session.flush()  # Get user ID without commit

            # 2. Create some circles
            circles = [
                {
                    "name": "Family",
                    "description": "My family circle",
                    "owner_id": new_user.id
                },
                {
                    "name": "Friends",
                    "description": "Best friends forever",
                    "owner_id": new_user.id
                },
                {
                    "name": "Work",
                    "description": "Work colleagues",
                    "owner_id": new_user.id
                }
            ]

            for circle_data in circles:
                circle = Circle(**circle_data)
                session.add(circle)
                await session.flush()

                # Add owner as member with role "owner"
                circle_member = CircleMember(
                    circle_id=circle.id,
                    user_id=new_user.id,
                    role="owner"
                )
                session.add(circle_member)

                # Add some posts in circles
                post = Post(
                    title=f"Welcome to {circle.name}",
                    content=f"This is the first post in {circle.name} circle",
                    author_id=new_user.id,
                    circle_id=circle.id
                )
                session.add(post)

            # 3. Create a public post (not in circle)
            public_post = Post(
                title="Hello World",
                content="This is my first public post",
                author_id=new_user.id,
                circle_id=None
            )
            session.add(public_post)

            # 4. Create a second test user with memberships
            email2 = "john@test.com"
            result2 = await session.execute(select(User).where(User.email == email2))
            user2 = result2.scalar_one_or_none()

            if not user2:
                user2 = User(
                    username="john_doe",
                    email=email2,
                    full_name="John Doe",
                    hashed_password=get_password_hash("SecurePass123!"),
                    is_active=True,
                )
                session.add(user2)
                await session.flush()

                # Add as member to existing circles with different roles
                circles_result = await session.execute(select(Circle))
                all_circles = circles_result.scalars().all()

                for i, circle in enumerate(all_circles):
                    if i == 0:  # First circle: member
                        role = "member"
                    elif i == 1:  # Second circle: moderator
                        role = "moderator"
                    else:  # Third circle: member
                        role = "member"

                    circle_member = CircleMember(
                        circle_id=circle.id,
                        user_id=user2.id,
                        role=role
                    )
                    session.add(circle_member)

            # Final commit
            await session.commit()
            print("Test data created successfully!")

        else:
            print("Test user already exists, checking if we need to add circles...")

            # Check if user has any circles
            circles_result = await session.execute(
                select(Circle).where(Circle.owner_id == user.id)
            )
            existing_circles = circles_result.scalars().all()

            if not existing_circles:
                print("Adding circles for existing user...")
                # Add circles for existing user (similar logic as above)
                # ... (put the circle creation logic here if needed)
                pass
            else:
                print(f"User already has {len(existing_circles)} circles")


if __name__ == "__main__":
    asyncio.run(create_test_data())
