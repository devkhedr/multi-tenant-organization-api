import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_member
from app.db.session import get_db
from app.models import User, Membership
from app.schemas.item import ItemCreate, ItemResponse, ItemDetail, PaginatedItems
from app.services.item import ItemService

router = APIRouter(tags=["items"])


@router.post(
    "/organizations/{org_id}/item",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    org_id: uuid.UUID,
    data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_member),
):
    service = ItemService(db)
    item = await service.create_item(org_id, data.item_details, current_user)
    return ItemResponse(item_id=str(item.id))


@router.get("/organizations/{org_id}/item", response_model=PaginatedItems)
async def get_items(
    org_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_member),
):
    service = ItemService(db)

    # Check if user is admin
    is_admin = await service.is_user_admin(org_id, current_user.id)

    items, total = await service.get_items(
        org_id, current_user, is_admin, limit, offset
    )

    return PaginatedItems(
        items=[
            ItemDetail(
                id=str(item.id),
                data=item.data,
                created_by=str(item.created_by),
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
