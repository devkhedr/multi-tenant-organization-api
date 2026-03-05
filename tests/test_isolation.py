import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestOrganizationIsolation:
    async def test_user_cannot_access_other_org(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org_id = organization["org_id"]

        # Second user (not a member) tries to access org items
        response = await client.get(
            f"/api/v1/organizations/{org_id}/item",
            headers=second_user_headers,
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Not a member of this organization"

    async def test_items_isolated_between_orgs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org1_id = organization["org_id"]

        # Admin creates item in org1
        await client.post(
            f"/api/v1/organizations/{org1_id}/item",
            json={"item_details": {"name": "Org1 Item"}},
            headers=auth_headers,
        )

        # Second user creates org2
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Second Organization"},
            headers=second_user_headers,
        )
        org2_id = response.json()["org_id"]

        # Second user creates item in org2
        await client.post(
            f"/api/v1/organizations/{org2_id}/item",
            json={"item_details": {"name": "Org2 Item"}},
            headers=second_user_headers,
        )

        # Each org should only see their items
        response1 = await client.get(
            f"/api/v1/organizations/{org1_id}/item",
            headers=auth_headers,
        )
        response2 = await client.get(
            f"/api/v1/organizations/{org2_id}/item",
            headers=second_user_headers,
        )

        assert response1.json()["total"] == 1
        assert response1.json()["items"][0]["data"]["name"] == "Org1 Item"
        assert response2.json()["total"] == 1
        assert response2.json()["items"][0]["data"]["name"] == "Org2 Item"

    async def test_cannot_invite_to_other_org(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        # Second user creates their own org
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Second Organization"},
            headers=second_user_headers,
        )
        org2_id = response.json()["org_id"]

        # First user tries to invite to org2 (not their org)
        response = await client.post(
            f"/api/v1/organization/{org2_id}/user",
            json={"email": "random@example.com", "role": "member"},
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_audit_logs_isolated(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org1_id = organization["org_id"]

        # Second user creates their own org
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Second Organization"},
            headers=second_user_headers,
        )
        org2_id = response.json()["org_id"]

        # Second user cannot access org1 audit logs
        response = await client.get(
            f"/api/v1/organizations/{org1_id}/audit-logs",
            headers=second_user_headers,
        )

        assert response.status_code == 403

    async def test_user_search_isolated(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        # Second user creates their own org
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Second Organization"},
            headers=second_user_headers,
        )
        org2_id = response.json()["org_id"]

        # First admin cannot search users in org2
        response = await client.get(
            f"/api/v1/organizations/{org2_id}/users/search?q=test",
            headers=auth_headers,
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestMultiOrgMembership:
    async def test_same_user_different_roles(
        self,
        client: AsyncClient,
        auth_headers: dict,
        organization: dict,
        second_user: dict,
        second_user_headers: dict,
    ):
        org1_id = organization["org_id"]

        # Second user creates org2 (becomes admin)
        response = await client.post(
            "/api/v1/organization",
            json={"org_name": "Second Organization"},
            headers=second_user_headers,
        )
        org2_id = response.json()["org_id"]

        # First user invites second user as member to org1
        await client.post(
            f"/api/v1/organization/{org1_id}/user",
            json={"email": second_user["_email"], "role": "member"},
            headers=auth_headers,
        )

        # Second user is member in org1 - cannot see users
        response = await client.get(
            f"/api/v1/organizations/{org1_id}/users",
            headers=second_user_headers,
        )
        assert response.status_code == 403

        # Second user is admin in org2 - can see users
        response = await client.get(
            f"/api/v1/organizations/{org2_id}/users",
            headers=second_user_headers,
        )
        assert response.status_code == 200

    async def test_creator_becomes_admin(
        self, client: AsyncClient, auth_headers: dict, organization: dict
    ):
        org_id = organization["org_id"]

        # Creator should be admin
        response = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers=auth_headers,
        )

        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == 1
        assert users[0]["role"] == "admin"
