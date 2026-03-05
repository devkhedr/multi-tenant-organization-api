from typing import Any
from pydantic import BaseModel


class ItemCreate(BaseModel):
    item_details: dict[str, Any]


class ItemResponse(BaseModel):
    item_id: str


class ItemDetail(BaseModel):
    id: str
    data: dict[str, Any]
    created_by: str
    created_at: str

    class Config:
        from_attributes = True


class PaginatedItems(BaseModel):
    items: list[ItemDetail]
    total: int
    limit: int
    offset: int
