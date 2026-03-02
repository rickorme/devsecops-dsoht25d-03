"""
Unit tests for backend/app/db/models.py
Tests model attributes, defaults, and constraints (without database)
"""
from sqlalchemy import inspect

from app.db.models import Base, Circle, CircleMember, Post, Role, User, UserSession


class TestUserModel:
    """Test User model attributes and configuration"""

    def test_user_model_has_correct_tablename(self):
        """Test that User model has correct table name"""
        assert User.__tablename__ == "users"

    def test_user_model_columns(self):
        """Test that User model has all required columns"""
        # Get column names
        mapper = inspect(User)
        column_names = [col.key for col in mapper.columns]

        required_columns = [
            "id", "username", "email", "hashed_password",
            "full_name", "is_active", "created_at", "updated_at"
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_user_username_is_unique(self):
        """Test that username has unique constraint"""
        mapper = inspect(User)
        username_col = mapper.columns["username"]
        assert username_col.unique is True

    def test_user_email_is_unique(self):
        """Test that email has unique constraint"""
        mapper = inspect(User)
        email_col = mapper.columns["email"]
        assert email_col.unique is True

    def test_user_is_active_default(self):
        """Test that is_active defaults to True"""
        mapper = inspect(User)
        is_active_col = mapper.columns["is_active"]
        # Check if default is set (will be callable or value)
        assert is_active_col.default is not None or is_active_col.server_default is not None

    def test_user_has_relationships(self):
        """Test that User has expected relationships"""
        mapper = inspect(User)
        relationship_names = [rel.key for rel in mapper.relationships]

        expected_relationships = ["owned_circles", "circle_memberships", "posts"]
        for rel in expected_relationships:
            assert rel in relationship_names, f"Missing relationship: {rel}"

    def test_user_model_inherits_from_base(self):
        """Test that User model inherits from Base"""
        assert issubclass(User, Base)

    def test_user_nullable_fields(self):
        """Test that optional fields are nullable"""
        mapper = inspect(User)
        # full_name should be nullable
        full_name_col = mapper.columns["full_name"]
        assert full_name_col.nullable is True

        # updated_at should be nullable
        updated_at_col = mapper.columns["updated_at"]
        assert updated_at_col.nullable is True

    def test_user_non_nullable_fields(self):
        """Test that required fields are not nullable"""
        mapper = inspect(User)

        non_nullable = ["id", "username", "email", "hashed_password"]
        for col_name in non_nullable:
            col = mapper.columns[col_name]
            # Primary key and explicitly non-nullable fields
            if col_name == "id" or col_name in ["username", "email", "hashed_password"]:
                assert col.nullable is False, f"{col_name} should not be nullable"


class TestCircleModel:
    """Test Circle model attributes and configuration"""

    def test_circle_model_has_correct_tablename(self):
        """Test that Circle model has correct table name"""
        assert Circle.__tablename__ == "circles"

    def test_circle_model_columns(self):
        """Test that Circle model has all required columns"""
        mapper = inspect(Circle)
        column_names = [col.key for col in mapper.columns]

        required_columns = ["id", "name", "description", "owner_id", "created_at"]
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_circle_has_owner_foreign_key(self):
        """Test that Circle has foreign key to User"""
        mapper = inspect(Circle)
        owner_id_col = mapper.columns["owner_id"]

        # Check if column has foreign key
        assert len(owner_id_col.foreign_keys) > 0
        # Check it references users.id
        fk = list(owner_id_col.foreign_keys)[0]
        assert "users.id" in str(fk.target_fullname)

    def test_circle_has_relationships(self):
        """Test that Circle has expected relationships"""
        mapper = inspect(Circle)
        relationship_names = [rel.key for rel in mapper.relationships]

        expected_relationships = ["owner", "members", "posts"]
        for rel in expected_relationships:
            assert rel in relationship_names, f"Missing relationship: {rel}"

    def test_circle_model_inherits_from_base(self):
        """Test that Circle model inherits from Base"""
        assert issubclass(Circle, Base)

    def test_circle_description_nullable(self):
        """Test that description is nullable"""
        mapper = inspect(Circle)
        description_col = mapper.columns["description"]
        assert description_col.nullable is True


class TestCircleMemberModel:
    """Test CircleMember association model"""

    def test_circle_member_has_correct_tablename(self):
        """Test that CircleMember has correct table name"""
        assert CircleMember.__tablename__ == "circle_members"

    def test_circle_member_composite_primary_key(self):
        """Test that CircleMember has composite primary key"""
        mapper = inspect(CircleMember)
        primary_key_columns = [col.name for col in mapper.primary_key]

        assert "circle_id" in primary_key_columns
        assert "user_id" in primary_key_columns
        assert len(primary_key_columns) == 2

    def test_circle_member_has_foreign_keys(self):
        """Test that CircleMember has foreign keys to Circle and User"""
        mapper = inspect(CircleMember)

        # Check circle_id foreign key
        circle_id_col = mapper.columns["circle_id"]
        assert len(circle_id_col.foreign_keys) > 0
        fk = list(circle_id_col.foreign_keys)[0]
        assert "circles.id" in str(fk.target_fullname)

        # Check user_id foreign key
        user_id_col = mapper.columns["user_id"]
        assert len(user_id_col.foreign_keys) > 0
        fk = list(user_id_col.foreign_keys)[0]
        assert "users.id" in str(fk.target_fullname)

    def test_circle_member_role_default(self):
        """Test that role has default value"""
        mapper = inspect(CircleMember)
        role_col = mapper.columns["role"]
        # Should have a default value
        assert role_col.default is not None or role_col.server_default is not None

    def test_circle_member_has_relationships(self):
        """Test that CircleMember has expected relationships"""
        mapper = inspect(CircleMember)
        relationship_names = [rel.key for rel in mapper.relationships]

        assert "circle" in relationship_names
        assert "user" in relationship_names

    def test_circle_member_model_inherits_from_base(self):
        """Test that CircleMember model inherits from Base"""
        assert issubclass(CircleMember, Base)


class TestPostModel:
    """Test Post model attributes and configuration"""

    def test_post_model_has_correct_tablename(self):
        """Test that Post model has correct table name"""
        assert Post.__tablename__ == "posts"

    def test_post_model_columns(self):
        """Test that Post model has all required columns"""
        mapper = inspect(Post)
        column_names = [col.key for col in mapper.columns]

        required_columns = [
            "id", "title", "content", "author_id",
            "circle_id", "created_at", "updated_at"
        ]
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_post_has_author_foreign_key(self):
        """Test that Post has foreign key to User"""
        mapper = inspect(Post)
        author_id_col = mapper.columns["author_id"]

        assert len(author_id_col.foreign_keys) > 0
        fk = list(author_id_col.foreign_keys)[0]
        assert "users.id" in str(fk.target_fullname)

    def test_post_has_circle_foreign_key(self):
        """Test that Post has optional foreign key to Circle"""
        mapper = inspect(Post)
        circle_id_col = mapper.columns["circle_id"]

        # Should have foreign key
        assert len(circle_id_col.foreign_keys) > 0
        fk = list(circle_id_col.foreign_keys)[0]
        assert "circles.id" in str(fk.target_fullname)

        # Should be nullable (posts can be public)
        assert circle_id_col.nullable is True

    def test_post_has_relationships(self):
        """Test that Post has expected relationships"""
        mapper = inspect(Post)
        relationship_names = [rel.key for rel in mapper.relationships]

        assert "author" in relationship_names
        assert "circle" in relationship_names

    def test_post_model_inherits_from_base(self):
        """Test that Post model inherits from Base"""
        assert issubclass(Post, Base)

    def test_post_content_not_nullable(self):
        """Test that post content is required"""
        mapper = inspect(Post)
        content_col = mapper.columns["content"]
        assert content_col.nullable is False

    def test_post_title_not_nullable(self):
        """Test that post title is required"""
        mapper = inspect(Post)
        title_col = mapper.columns["title"]
        assert title_col.nullable is False


class TestRoleModel:
    """Test Role model attributes and configuration"""

    def test_role_model_has_correct_tablename(self):
        """Test that Role model has correct table name"""
        assert Role.__tablename__ == "roles"

    def test_role_model_columns(self):
        """Test that Role model has all required columns"""
        mapper = inspect(Role)
        column_names = [col.key for col in mapper.columns]

        required_columns = ["id", "name", "description"]
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_role_name_is_unique(self):
        """Test that role name has unique constraint"""
        mapper = inspect(Role)
        name_col = mapper.columns["name"]
        assert name_col.unique is True

    def test_role_name_has_index(self):
        """Test that role name is indexed"""
        mapper = inspect(Role)
        name_col = mapper.columns["name"]
        assert name_col.index is True

    def test_role_model_inherits_from_base(self):
        """Test that Role model inherits from Base"""
        assert issubclass(Role, Base)


class TestUserSessionModel:
    """Test UserSession model attributes and configuration"""

    def test_user_session_has_correct_tablename(self):
        """Test that UserSession has correct table name"""
        assert UserSession.__tablename__ == "user_sessions"

    def test_user_session_model_columns(self):
        """Test that UserSession has all required columns"""
        mapper = inspect(UserSession)
        column_names = [col.key for col in mapper.columns]

        required_columns = [
            "id", "session_token", "user_id", "created_at",
            "expires_at", "ip_address", "user_agent"
        ]
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_session_token_is_unique(self):
        """Test that session_token has unique constraint"""
        mapper = inspect(UserSession)
        token_col = mapper.columns["session_token"]
        assert token_col.unique is True

    def test_session_token_has_index(self):
        """Test that session_token is indexed"""
        mapper = inspect(UserSession)
        token_col = mapper.columns["session_token"]
        assert token_col.index is True

    def test_user_session_repr(self):
        """Test UserSession __repr__ method"""
        # Create a mock session object
        session = UserSession()
        session.id = 1
        session.user_id = 123

        repr_str = repr(session)
        assert "UserSession" in repr_str
        assert "id=1" in repr_str
        assert "user_id=123" in repr_str

    def test_user_session_optional_fields(self):
        """Test that ip_address and user_agent are nullable"""
        mapper = inspect(UserSession)

        ip_col = mapper.columns["ip_address"]
        assert ip_col.nullable is True

        ua_col = mapper.columns["user_agent"]
        assert ua_col.nullable is True

    def test_user_session_required_fields(self):
        """Test that core session fields are not nullable"""
        mapper = inspect(UserSession)

        required_fields = ["session_token", "user_id", "created_at", "expires_at"]
        for field_name in required_fields:
            col = mapper.columns[field_name]
            assert col.nullable is False, f"{field_name} should not be nullable"


class TestModelRelationships:
    """Test relationships between models"""

    def test_user_to_circles_relationship(self):
        """Test User -> Circle relationship (owned_circles)"""
        mapper = inspect(User)
        owned_circles_rel = mapper.relationships["owned_circles"]

        # Should back-populate to owner
        assert owned_circles_rel.back_populates == "owner"

    def test_user_to_posts_relationship(self):
        """Test User -> Post relationship"""
        mapper = inspect(User)
        posts_rel = mapper.relationships["posts"]

        # Should back-populate to author
        assert posts_rel.back_populates == "author"

    def test_circle_to_owner_relationship(self):
        """Test Circle -> User relationship (owner)"""
        mapper = inspect(Circle)
        owner_rel = mapper.relationships["owner"]

        # Should back-populate to owned_circles
        assert owner_rel.back_populates == "owned_circles"

    def test_circle_to_members_relationship(self):
        """Test Circle -> CircleMember relationship"""
        mapper = inspect(Circle)
        members_rel = mapper.relationships["members"]

        # Should back-populate to circle
        assert members_rel.back_populates == "circle"

    def test_circle_to_posts_relationship(self):
        """Test Circle -> Post relationship"""
        mapper = inspect(Circle)
        posts_rel = mapper.relationships["posts"]

        # Should back-populate to circle
        assert posts_rel.back_populates == "circle"

    def test_post_to_author_relationship(self):
        """Test Post -> User relationship (author)"""
        mapper = inspect(Post)
        author_rel = mapper.relationships["author"]

        # Should back-populate to posts
        assert author_rel.back_populates == "posts"

    def test_post_to_circle_relationship(self):
        """Test Post -> Circle relationship"""
        mapper = inspect(Post)
        circle_rel = mapper.relationships["circle"]

        # Should back-populate to posts
        assert circle_rel.back_populates == "posts"


class TestModelConstraints:
    """Test model constraints and field specifications"""

    def test_user_username_max_length(self):
        """Test User username has max length constraint"""
        mapper = inspect(User)
        username_col = mapper.columns["username"]
        assert username_col.type.length == 50

    def test_user_email_max_length(self):
        """Test User email has max length constraint"""
        mapper = inspect(User)
        email_col = mapper.columns["email"]
        assert email_col.type.length == 255

    def test_circle_name_max_length(self):
        """Test Circle name has max length constraint"""
        mapper = inspect(Circle)
        name_col = mapper.columns["name"]
        assert name_col.type.length == 50

    def test_post_title_max_length(self):
        """Test Post title has max length constraint"""
        mapper = inspect(Post)
        title_col = mapper.columns["title"]
        assert title_col.type.length == 100

    def test_role_name_max_length(self):
        """Test Role name has max length constraint"""
        mapper = inspect(Role)
        name_col = mapper.columns["name"]
        assert name_col.type.length == 20

    def test_circle_member_role_max_length(self):
        """Test CircleMember role has max length constraint"""
        mapper = inspect(CircleMember)
        role_col = mapper.columns["role"]
        assert role_col.type.length == 20

    def test_session_token_max_length(self):
        """Test UserSession token has max length constraint"""
        mapper = inspect(UserSession)
        token_col = mapper.columns["session_token"]
        assert token_col.type.length == 255


class TestModelInheritance:
    """Test that all models inherit from Base correctly"""

    def test_all_models_inherit_from_base(self):
        """Test that all models inherit from Base"""
        models = [User, Circle, CircleMember, Post, Role, UserSession]

        for model in models:
            assert issubclass(model, Base), f"{model.__name__} should inherit from Base"

    def test_base_is_declarative_base(self):
        """Test that Base is a valid DeclarativeBase"""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


class TestTimestampFields:
    """Test timestamp fields configuration"""

    def test_user_has_created_at(self):
        """Test User has created_at with server default"""
        mapper = inspect(User)
        created_col = mapper.columns["created_at"]
        assert created_col.server_default is not None

    def test_user_has_updated_at(self):
        """Test User has updated_at with onupdate"""
        mapper = inspect(User)
        updated_col = mapper.columns["updated_at"]
        # Check if onupdate is configured
        assert updated_col.onupdate is not None or updated_col.server_onupdate is not None

    def test_circle_has_created_at(self):
        """Test Circle has created_at with server default"""
        mapper = inspect(Circle)
        created_col = mapper.columns["created_at"]
        assert created_col.server_default is not None

    def test_post_has_timestamps(self):
        """Test Post has both created_at and updated_at"""
        mapper = inspect(Post)

        created_col = mapper.columns["created_at"]
        assert created_col.server_default is not None

        updated_col = mapper.columns["updated_at"]
        assert updated_col.onupdate is not None or updated_col.server_onupdate is not None

    def test_circle_member_has_joined_at(self):
        """Test CircleMember has joined_at timestamp"""
        mapper = inspect(CircleMember)
        joined_col = mapper.columns["joined_at"]
        assert joined_col.server_default is not None
