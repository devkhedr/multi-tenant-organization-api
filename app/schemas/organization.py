import uuid
from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    org_name: str = Field(min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    org_id: str


class InviteUser(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(admin|member)$")


class UserInOrg(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class PaginatedUsers(BaseModel):
    users: list[UserInOrg]
    total: int
    limit: int
    offset: int
