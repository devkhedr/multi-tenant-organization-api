from typing import Any
from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: str
    user_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: str

    class Config:
        from_attributes = True


class PaginatedAuditLogs(BaseModel):
    logs: list[AuditLogEntry]
    total: int
    limit: int
    offset: int
