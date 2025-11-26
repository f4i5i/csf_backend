"""Tests for children API endpoints."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child, Grade, HowHeardAboutUs, JerseySize
from app.models.user import User


class TestListChildren:
    """Tests for listing children."""

    async def test_list_my_children_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing children when user has none."""
        response = await client.get("/api/v1/children/my", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_my_children_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing children with existing children."""
        # Create a child
        child = Child(
            user_id=test_user.id,
            first_name="John",
            last_name="Doe",
            date_of_birth=date(2015, 5, 10),
            jersey_size=JerseySize.M,
            grade=Grade.GRADE_3,
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()

        response = await client.get("/api/v1/children/my", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["first_name"] == "John"
        assert data["items"][0]["last_name"] == "Doe"


class TestCreateChild:
    """Tests for creating children."""

    async def test_create_child_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a child successfully."""
        payload = {
            "first_name": "Jane",
            "last_name": "Smith",
            "date_of_birth": "2016-03-15",
            "jersey_size": "s",
            "grade": "2",
            "medical_conditions": "Asthma",
            "has_no_medical_conditions": False,
            "how_heard_about_us": "friend",
        }

        response = await client.post(
            "/api/v1/children/", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"
        assert data["jersey_size"] == "s"
        assert data["grade"] == "2"
        assert data["medical_conditions"] == "Asthma"

    async def test_create_child_with_emergency_contacts(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a child with emergency contacts."""
        payload = {
            "first_name": "Tom",
            "last_name": "Jones",
            "date_of_birth": "2017-07-20",
            "emergency_contacts": [
                {
                    "name": "Parent One",
                    "relation": "Father",
                    "phone": "555-1234",
                    "email": "parent@example.com",
                    "is_primary": True,
                }
            ],
        }

        response = await client.post(
            "/api/v1/children/", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Tom"
        assert len(data["emergency_contacts"]) == 1
        assert data["emergency_contacts"][0]["name"] == "Parent One"
        assert data["emergency_contacts"][0]["relation"] == "Father"

    async def test_create_child_invalid_dob(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a child with future date of birth."""
        payload = {
            "first_name": "Future",
            "last_name": "Kid",
            "date_of_birth": "2030-01-01",
        }

        response = await client.post(
            "/api/v1/children/", json=payload, headers=auth_headers
        )

        assert response.status_code == 422

    async def test_create_child_unauthenticated(self, client: AsyncClient):
        """Test creating a child without authentication."""
        payload = {
            "first_name": "Test",
            "last_name": "Child",
            "date_of_birth": "2015-01-01",
        }

        response = await client.post("/api/v1/children/", json=payload)

        assert response.status_code == 401


class TestGetChild:
    """Tests for getting child details."""

    async def test_get_child_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a child by ID."""
        child = Child(
            user_id=test_user.id,
            first_name="Alex",
            last_name="Brown",
            date_of_birth=date(2014, 9, 1),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        response = await client.get(
            f"/api/v1/children/{child.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Alex"
        assert data["id"] == child.id

    async def test_get_child_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a non-existent child."""
        response = await client.get(
            "/api/v1/children/nonexistent-id", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_child_forbidden(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        admin_user: User,
    ):
        """Test that parent cannot access another user's child."""
        # Create child belonging to admin user
        child = Child(
            user_id=admin_user.id,
            first_name="Other",
            last_name="Child",
            date_of_birth=date(2015, 1, 1),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        # Try to access with test user's auth
        response = await client.get(
            f"/api/v1/children/{child.id}", headers=auth_headers
        )

        assert response.status_code == 403


class TestUpdateChild:
    """Tests for updating children."""

    async def test_update_child_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a child."""
        child = Child(
            user_id=test_user.id,
            first_name="Update",
            last_name="Me",
            date_of_birth=date(2015, 6, 15),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        payload = {
            "first_name": "Updated",
            "jersey_size": "l",
        }

        response = await client.put(
            f"/api/v1/children/{child.id}", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["jersey_size"] == "l"

    async def test_update_child_medical_conditions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating encrypted medical conditions."""
        child = Child(
            user_id=test_user.id,
            first_name="Medical",
            last_name="Test",
            date_of_birth=date(2016, 2, 20),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        payload = {
            "medical_conditions": "Peanut allergy",
        }

        response = await client.put(
            f"/api/v1/children/{child.id}", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["medical_conditions"] == "Peanut allergy"


class TestDeleteChild:
    """Tests for deleting children."""

    async def test_delete_child_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test soft deleting a child."""
        child = Child(
            user_id=test_user.id,
            first_name="Delete",
            last_name="Me",
            date_of_birth=date(2015, 8, 8),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        response = await client.delete(
            f"/api/v1/children/{child.id}", headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Child deleted successfully"

        # Verify child is not returned in list
        list_response = await client.get("/api/v1/children/my", headers=auth_headers)
        assert list_response.json()["total"] == 0


class TestEmergencyContacts:
    """Tests for emergency contact endpoints."""

    async def test_add_emergency_contact(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test adding an emergency contact to a child."""
        child = Child(
            user_id=test_user.id,
            first_name="Contact",
            last_name="Test",
            date_of_birth=date(2016, 4, 4),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        payload = {
            "name": "Emergency Person",
            "relation": "Uncle",
            "phone": "555-9999",
            "is_primary": False,
        }

        response = await client.post(
            f"/api/v1/children/{child.id}/emergency-contacts",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Emergency Person"
        assert data["relation"] == "Uncle"

    async def test_list_emergency_contacts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing emergency contacts for a child."""
        child = Child(
            user_id=test_user.id,
            first_name="List",
            last_name="Contacts",
            date_of_birth=date(2017, 1, 1),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        # Add contacts via API
        contact_payload = {
            "name": "Contact Person",
            "relation": "Aunt",
            "phone": "555-1111",
        }
        await client.post(
            f"/api/v1/children/{child.id}/emergency-contacts",
            json=contact_payload,
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/children/{child.id}/emergency-contacts",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Contact Person"

    async def test_delete_emergency_contact(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an emergency contact."""
        child = Child(
            user_id=test_user.id,
            first_name="Delete",
            last_name="Contact",
            date_of_birth=date(2016, 6, 6),
            is_active=True,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        # Create contact
        create_response = await client.post(
            f"/api/v1/children/{child.id}/emergency-contacts",
            json={
                "name": "To Delete",
                "relation": "Friend",
                "phone": "555-0000",
            },
            headers=auth_headers,
        )
        contact_id = create_response.json()["id"]

        # Delete contact
        response = await client.delete(
            f"/api/v1/children/emergency-contacts/{contact_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Emergency contact deleted successfully"
