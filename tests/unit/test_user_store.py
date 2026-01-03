"""
Unit tests for User Store.

Tests user CRUD operations and persistence.
"""

import pytest
from pathlib import Path

from src.auth import UserStore, User


class TestUserStore:
    """Tests for UserStore class."""

    @pytest.mark.unit
    def test_create_user(self, user_store, test_config):
        """Test creating a new user."""
        user = user_store.create_user(
            phone=test_config["test_phone"],
            password=test_config["test_password"],
            name=test_config["test_user_name"]
        )

        assert user is not None
        assert user.phone == test_config["test_phone"]
        assert user.name == test_config["test_user_name"]
        assert user.is_active is True
        assert user.user_id is not None

    @pytest.mark.unit
    def test_create_user_without_password(self, user_store, test_config):
        """Test creating user without password (phone-only auth)."""
        user = user_store.create_user(
            phone=test_config["test_phone"],
            name=test_config["test_user_name"]
        )

        assert user is not None
        assert user.password_hash is None

    @pytest.mark.unit
    def test_create_duplicate_user_fails(self, user_store, sample_user, test_config):
        """Test that duplicate phone numbers are rejected."""
        with pytest.raises(ValueError, match="already exists"):
            user_store.create_user(
                phone=test_config["test_phone"],
                password="AnotherPassword",
                name="Another User"
            )

    @pytest.mark.unit
    def test_get_by_phone(self, user_store, sample_user, test_config):
        """Test retrieving user by phone."""
        user = user_store.get_by_phone(test_config["test_phone"])

        assert user is not None
        assert user.phone == test_config["test_phone"]
        assert user.name == sample_user.name

    @pytest.mark.unit
    def test_get_by_phone_not_found(self, user_store):
        """Test retrieving non-existent user."""
        user = user_store.get_by_phone("+5511000000000")
        assert user is None

    @pytest.mark.unit
    def test_get_by_id(self, user_store, sample_user):
        """Test retrieving user by ID."""
        user = user_store.get_by_id(sample_user.user_id)

        assert user is not None
        assert user.user_id == sample_user.user_id

    @pytest.mark.unit
    def test_get_by_id_not_found(self, user_store):
        """Test retrieving non-existent user by ID."""
        user = user_store.get_by_id("non-existent-id")
        assert user is None

    @pytest.mark.unit
    def test_persistence(self, temp_user_file, test_config):
        """Test that data persists to file."""
        # Create user with first store instance
        store1 = UserStore(file_path=temp_user_file)
        user = store1.create_user(
            phone=test_config["test_phone"],
            password=test_config["test_password"],
            name=test_config["test_user_name"]
        )

        # Create new store instance and verify data
        store2 = UserStore(file_path=temp_user_file)
        loaded_user = store2.get_by_phone(test_config["test_phone"])

        assert loaded_user is not None
        assert loaded_user.user_id == user.user_id
        assert loaded_user.name == user.name

    @pytest.mark.unit
    def test_phone_normalization_on_create(self, user_store):
        """Test phone is normalized on user creation."""
        user = user_store.create_user(
            phone="(11) 99999-9999",  # Non-normalized format
            name="Test User"
        )

        assert user.phone == "+5511999999999"

    @pytest.mark.unit
    def test_phone_normalization_on_lookup(self, user_store, test_config):
        """Test phone is normalized on lookup."""
        user_store.create_user(
            phone=test_config["test_phone"],
            name="Test User"
        )

        # Lookup with different format
        user = user_store.get_by_phone("11999999999")
        assert user is not None

    @pytest.mark.unit
    def test_user_to_dict(self, sample_user):
        """Test user serialization to dict."""
        data = sample_user.to_dict()

        assert "user_id" in data
        assert "phone" in data
        assert "name" in data
        assert "is_active" in data
        assert "created_at" in data

    @pytest.mark.unit
    def test_list_users(self, user_store, test_config):
        """Test listing all users."""
        # Create multiple users
        user_store.create_user(phone="+5511111111111", name="User 1")
        user_store.create_user(phone="+5511222222222", name="User 2")
        user_store.create_user(phone="+5511333333333", name="User 3")

        users = user_store.list_users()
        assert len(users) == 3

    @pytest.mark.unit
    def test_user_with_member_ids(self, user_store, test_config):
        """Test creating user with member IDs."""
        user = user_store.create_user(
            phone=test_config["test_phone"],
            name="Test User",
            member_ids=[12345, 12346]
        )

        assert 12345 in user.member_ids
        assert 12346 in user.member_ids

    @pytest.mark.unit
    def test_invalid_phone_raises_error(self, user_store):
        """Test that invalid phone number raises error."""
        with pytest.raises(ValueError, match="Invalid phone"):
            user_store.create_user(
                phone="invalid",
                name="Test User"
            )
