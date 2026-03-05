import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models import User, Membership
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    InviteUser,
    PaginatedUsers,
    UserInOrg,
)
from app.services.organization import OrganizationService

router = APIRouter(tags=["organizations"])


@router.post("/organization", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrganizationService(db)
    org = await service.create_organization(data.org_name, current_user)
    return OrganizationResponse(org_id=str(org.id))


@router.post("/organization/{org_id}/user", status_code=status.HTTP_201_CREATED)
async def invite_user(
    org_id: uuid.UUID,
    data: InviteUser,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_admin),
):
    service = OrganizationService(db)

    try:
        await service.invite_user(org_id, data.email, data.role, current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"message": "User invited successfully"}


@router.get("/organizations/{org_id}/users", response_model=PaginatedUsers)
async def get_organization_users(
    org_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_admin),
):
    service = OrganizationService(db)
    users, total = await service.get_users(org_id, limit, offset)

    return PaginatedUsers(
        users=[UserInOrg(**u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/organizations/{org_id}/users/search")
async def search_users(
    org_id: uuid.UUID,
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_admin),
):
    service = OrganizationService(db)
    users = await service.search_users(org_id, q)
    return {"users": [UserInOrg(**u) for u in users]}
