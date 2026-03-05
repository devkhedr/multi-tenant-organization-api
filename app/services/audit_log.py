import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_logs(
        self,
        org_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        # Count
        count_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.org_id == org_id)
        )
        total = count_result.scalar()

        # Get logs
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.org_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        logs = result.scalars().all()

        return list(logs), total
