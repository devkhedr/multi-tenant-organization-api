import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAdminOnlyEndpoints:
    async def test_admin_can_invite_users(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        # First register a user to invite
        unique_id = uuid.uuid4().hex[:8]
        email = f"invite_{unique_id}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "password123456",
                "full_name": "Invited User",
            },
        )

        response = await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": email, "role": "member"},
            headers=auth_headers,
        )

        assert response.status_code == 201

    async def test_member_cannot_invite_users(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Member tries to invite another user - should fail
        response = await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": "another@example.com", "role": "member"},
            headers=second_user_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    async def test_admin_can_list_users(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "users" in response.json()

    async def test_member_cannot_list_users(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Member tries to list users - should fail
        response = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers=second_user_headers,
        )

        assert response.status_code == 403

    async def test_admin_can_view_audit_logs(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers=auth_headers,
        )

        assert response.status_code == 200

    async def test_member_cannot_view_audit_logs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Member tries to view audit logs - should fail
        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers=second_user_headers,
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestMemberPermissions:
    async def test_member_can_create_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Member creates an item - should succeed
        response = await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Test Item"}},
            headers=second_user_headers,
        )

        assert response.status_code == 201

    async def test_member_sees_only_own_items(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Admin creates an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Admin Item"}},
            headers=auth_headers,
        )

        # Member creates an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Member Item"}},
            headers=second_user_headers,
        )

        # Member should only see their own item
        response = await client.get(
            f"/api/v1/organizations/{org_id}/item",
            headers=second_user_headers,
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_admin_sees_all_items(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Admin creates an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Admin Item"}},
            headers=auth_headers,
        )

        # Member creates an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Member Item"}},
            headers=second_user_headers,
        )

        # Admin should see all items
        response = await client.get(
            f"/api/v1/organizations/{org_id}/item",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["total"] == 2


@pytest.mark.asyncio
class TestFullTextSearch:
    async def test_admin_can_search_users(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/users/search?q=test",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "users" in response.json()

    async def test_member_cannot_search_users(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Admin invites second user as member
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Member tries to search - should fail
        response = await client.get(
            f"/api/v1/organizations/{org_id}/users/search?q=test",
            headers=second_user_headers,
        )

        assert response.status_code == 403

    async def test_search_returns_valid_response(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
    ):
        org_id = organization["org_id"]

        # Search endpoint should return valid response structure
        # Note: Full-text search requires the trigger from migrations
        response = await client.get(
            f"/api/v1/organizations/{org_id}/users/search?q=test",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)


@pytest.mark.asyncio
class TestPagination:
    async def test_users_pagination(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/users?limit=10&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_items_pagination(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        # Create multiple items
        for i in range(3):
            await client.post(
                f"/api/v1/organizations/{org_id}/item",
                json={"item_details": {"name": f"Item {i}"}},
                headers=auth_headers,
            )

        # Test pagination
        response = await client.get(
            f"/api/v1/organizations/{org_id}/item?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    async def test_audit_logs_pagination(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs?limit=5&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data


@pytest.mark.asyncio
class TestAuditLogContent:
    async def test_create_organization_logged(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        logs = response.json()["logs"]

        # Should have at least create_organization log
        actions = [log["action"] for log in logs]
        assert "create_organization" in actions

    async def test_create_item_logged(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        # Create an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Test Item"}},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        logs = response.json()["logs"]

        actions = [log["action"] for log in logs]
        assert "create_item" in actions

    async def test_invite_user_logged(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
    ):
        org_id = organization["org_id"]

        # Invite user
        await client.post(
            f"/api/v1/organization/{org_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        logs = response.json()["logs"]

        actions = [log["action"] for log in logs]
        assert "invite_user" in actions
