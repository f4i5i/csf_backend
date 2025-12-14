"""Tests for photos API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo, PhotoCategory

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_photo_category(
    db_session: AsyncSession, test_class: dict
) -> PhotoCategory:
    """Create a test photo category."""
    category = PhotoCategory(
        class_id=test_class["id"],
        name="Practice Photos",
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def test_photo(
    db_session: AsyncSession, test_class: dict, test_user, test_photo_category: PhotoCategory
) -> Photo:
    """Create a test photo."""
    photo = Photo(
        class_id=test_class["id"],
        category_id=test_photo_category.id,
        uploaded_by=test_user.id,
        file_name="test_photo.jpg",
        file_path="/uploads/test_photo.jpg",
        file_size=1024000,
        thumbnail_path="/uploads/thumbs/test_photo.jpg",
        width=1920,
        height=1080,
        is_active=True,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)
    return photo


class TestListAllPhotos:
    """Tests for GET /api/v1/photos/ endpoint."""

    async def test_list_photos_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing photos when none exist."""
        response = await client.get(
            "/api/v1/photos/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_photos_success(
        self, client: AsyncClient, auth_headers: dict, test_photo: Photo
    ):
        """Test listing all photos."""
        response = await client.get(
            "/api/v1/photos/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["file_name"] == "test_photo.jpg"

    async def test_list_photos_filter_by_class(
        self, client: AsyncClient, auth_headers: dict, test_photo: Photo, test_class: dict
    ):
        """Test filtering photos by class_id."""
        response = await client.get(
            f"/api/v1/photos/?class_id={test_class['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["class_id"] == test_class["id"]

    async def test_list_photos_filter_by_category(
        self, client: AsyncClient, auth_headers: dict, test_photo: Photo, test_photo_category: PhotoCategory
    ):
        """Test filtering photos by category_id."""
        response = await client.get(
            f"/api/v1/photos/?category_id={test_photo_category.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category_id"] == test_photo_category.id

    async def test_list_photos_pagination(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_class: dict, test_user
    ):
        """Test pagination for photos."""
        # Create multiple photos
        for i in range(5):
            photo = Photo(
                class_id=test_class["id"],
                uploaded_by=test_user.id,
                file_name=f"photo_{i}.jpg",
                file_path=f"/uploads/photo_{i}.jpg",
                file_size=1024000,
                width=1920,
                height=1080,
                is_active=True,
            )
            db_session.add(photo)
        await db_session.commit()

        # Test with limit
        response = await client.get(
            "/api/v1/photos/?limit=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
