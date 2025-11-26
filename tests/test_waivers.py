"""Tests for waiver API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.waiver import WaiverAcceptance, WaiverTemplate, WaiverType


class TestWaiverTemplatesAdmin:
    """Tests for admin waiver template management."""

    async def test_create_waiver_template_success(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        """Test creating a waiver template as admin."""
        payload = {
            "name": "Test Medical Release",
            "waiver_type": "medical_release",
            "content": "<h1>Medical Release</h1><p>Content here...</p>",
            "is_required": True,
        }

        response = await client.post(
            "/api/v1/waivers/templates", json=payload, headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Medical Release"
        assert data["waiver_type"] == "medical_release"
        assert data["version"] == 1
        assert data["is_active"] is True

    async def test_create_waiver_template_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that regular users cannot create waiver templates."""
        payload = {
            "name": "Unauthorized Waiver",
            "waiver_type": "liability",
            "content": "Content",
        }

        response = await client.post(
            "/api/v1/waivers/templates", json=payload, headers=auth_headers
        )

        assert response.status_code == 403

    async def test_list_waiver_templates(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test listing waiver templates."""
        # Create a template
        template = WaiverTemplate(
            name="Liability Waiver",
            waiver_type=WaiverType.LIABILITY,
            content="<p>Liability content</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()

        response = await client.get(
            "/api/v1/waivers/templates", headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(w["waiver_type"] == "liability" for w in data["items"])

    async def test_get_waiver_template(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting a specific waiver template."""
        template = WaiverTemplate(
            name="Photo Release",
            waiver_type=WaiverType.PHOTO_RELEASE,
            content="<p>Photo release content</p>",
            version=1,
            is_active=True,
            is_required=False,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        response = await client.get(
            f"/api/v1/waivers/templates/{template.id}", headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Photo Release"
        assert data["is_required"] is False

    async def test_update_waiver_template(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test updating a waiver template."""
        template = WaiverTemplate(
            name="Update Test",
            waiver_type=WaiverType.CANCELLATION_POLICY,
            content="<p>Original content</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        payload = {
            "content": "<p>Updated content</p>",
        }

        response = await client.put(
            f"/api/v1/waivers/templates/{template.id}",
            json=payload,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "<p>Updated content</p>"
        assert data["version"] == 2  # Version should increment

    async def test_delete_waiver_template(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test soft deleting a waiver template."""
        template = WaiverTemplate(
            name="Delete Test",
            waiver_type=WaiverType.MEDICAL_RELEASE,
            content="<p>To delete</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        response = await client.delete(
            f"/api/v1/waivers/templates/{template.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Waiver template deleted successfully"


class TestWaiverAcceptance:
    """Tests for waiver acceptance by users."""

    async def test_get_required_waivers(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test getting required waivers for a user."""
        # Create required waivers
        template = WaiverTemplate(
            name="Required Waiver",
            waiver_type=WaiverType.LIABILITY,
            content="<p>Required liability</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()

        response = await client.get(
            "/api/v1/waivers/required", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["pending_count"] >= 1
        # Check that at least one waiver needs consent
        assert any(w["needs_reconsent"] is True for w in data["items"])

    async def test_accept_waiver(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test accepting a waiver."""
        template = WaiverTemplate(
            name="Accept Test",
            waiver_type=WaiverType.MEDICAL_RELEASE,
            content="<p>Accept this</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        payload = {
            "waiver_template_id": template.id,
            "signer_name": "Test User",
        }

        response = await client.post(
            "/api/v1/waivers/accept", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["waiver_template_id"] == template.id
        assert data["signer_name"] == "Test User"
        assert data["waiver_version"] == 1

    async def test_accept_waiver_already_accepted(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that accepting an already accepted waiver fails."""
        template = WaiverTemplate(
            name="Already Accepted",
            waiver_type=WaiverType.PHOTO_RELEASE,
            content="<p>Photo release</p>",
            version=1,
            is_active=True,
            is_required=False,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Accept the waiver first
        acceptance = WaiverAcceptance(
            user_id=test_user.id,
            waiver_template_id=template.id,
            waiver_version=1,
            signer_name="Test User",
            signer_ip="127.0.0.1",
            signer_user_agent="Test Agent",
        )
        db_session.add(acceptance)
        await db_session.commit()

        # Try to accept again
        payload = {
            "waiver_template_id": template.id,
            "signer_name": "Test User",
        }

        response = await client.post(
            "/api/v1/waivers/accept", json=payload, headers=auth_headers
        )

        assert response.status_code == 400

    async def test_accept_waiver_needs_reconsent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test accepting a waiver that needs re-consent due to version update."""
        template = WaiverTemplate(
            name="Reconsent Test",
            waiver_type=WaiverType.LIABILITY,
            content="<p>Updated liability</p>",
            version=2,  # Version 2
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Create acceptance for version 1
        acceptance = WaiverAcceptance(
            user_id=test_user.id,
            waiver_template_id=template.id,
            waiver_version=1,  # Accepted version 1
            signer_name="Test User",
            signer_ip="127.0.0.1",
            signer_user_agent="Test Agent",
        )
        db_session.add(acceptance)
        await db_session.commit()

        # Should be able to accept version 2
        payload = {
            "waiver_template_id": template.id,
            "signer_name": "Test User",
        }

        response = await client.post(
            "/api/v1/waivers/accept", json=payload, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["waiver_version"] == 2

    async def test_get_my_acceptances(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting user's waiver acceptances."""
        template = WaiverTemplate(
            name="My Acceptance",
            waiver_type=WaiverType.CANCELLATION_POLICY,
            content="<p>Cancellation</p>",
            version=1,
            is_active=True,
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        acceptance = WaiverAcceptance(
            user_id=test_user.id,
            waiver_template_id=template.id,
            waiver_version=1,
            signer_name="Test User",
            signer_ip="127.0.0.1",
            signer_user_agent="Test Agent",
        )
        db_session.add(acceptance)
        await db_session.commit()

        response = await client.get(
            "/api/v1/waivers/my-acceptances", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(a["signer_name"] == "Test User" for a in data["items"])

    async def test_accept_inactive_waiver_fails(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that accepting an inactive waiver fails."""
        template = WaiverTemplate(
            name="Inactive Waiver",
            waiver_type=WaiverType.LIABILITY,
            content="<p>Inactive</p>",
            version=1,
            is_active=False,  # Inactive
            is_required=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        payload = {
            "waiver_template_id": template.id,
            "signer_name": "Test User",
        }

        response = await client.post(
            "/api/v1/waivers/accept", json=payload, headers=auth_headers
        )

        assert response.status_code == 400


class TestWaiverVersioning:
    """Tests for waiver versioning."""

    async def test_waiver_version_auto_increment(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Test that waiver versions auto-increment for same type."""
        # Create first waiver
        payload1 = {
            "name": "Version Test 1",
            "waiver_type": "medical_release",
            "content": "<p>Version 1</p>",
        }
        response1 = await client.post(
            "/api/v1/waivers/templates", json=payload1, headers=admin_auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["version"] == 1

        # Create second waiver of same type
        payload2 = {
            "name": "Version Test 2",
            "waiver_type": "medical_release",
            "content": "<p>Version 2</p>",
        }
        response2 = await client.post(
            "/api/v1/waivers/templates", json=payload2, headers=admin_auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["version"] == 2
