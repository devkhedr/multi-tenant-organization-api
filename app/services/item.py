import uuid
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item, AuditLog, User, Membership, Role


class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_item(
        self,
        org_id: uuid.UUID,
        item_details: dict[str, Any],
        creator: User,
    ) -> Item:
        item = Item(
            org_id=org_id,
            created_by=creator.id,
            data=item_details,
        )
        self.db.add(item)
        await self.db.flush()

        # Audit log
        audit = AuditLog(
            org_id=org_id,
            user_id=creator.id,
            action="create_item",
            entity_type="item",
            entity_id=item.id,
            details={"item_data": item_details},
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_items(
        self,
        org_id: uuid.UUID,
        user: User,
        is_admin: bool,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Item], int]:
        # Base query
        base_query = select(Item).where(Item.org_id == org_id)

        # Members see only their items, admins see all
        if not is_admin:
            base_query = base_query.where(Item.created_by == user.id)

        # Count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get items
        items_query = base_query.offset(offset).limit(limit)
        result = await self.db.execute(items_query)
        items = result.scalars().all()

        # Audit log for viewing
        audit = AuditLog(
            org_id=org_id,
            user_id=user.id,
            action="view_items",
            entity_type="item",
            details={"limit": limit, "offset": offset, "is_admin": is_admin},
        )
        self.db.add(audit)
        await self.db.commit()

        return list(items), total

    async def is_user_admin(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(Membership, Role)
            .join(Role, Membership.role_id == Role.id)
            .where(
                Membership.org_id == org_id,
                Membership.user_id == user_id,
            )
        )
        row = result.first()
        if not row:
            return False
        _, role = row
        return role.name == "admin"
