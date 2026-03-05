import uuid
import re
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, Membership, Role, User, AuditLog


def generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def create_organization(self, name: str, creator: User) -> Organization:
        # Generate unique slug
        base_slug = generate_slug(name)
        slug = base_slug
        counter = 1

        while True:
            existing = await self.db.execute(
                select(Organization).where(Organization.slug == slug)
            )
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create organization
        org = Organization(name=name, slug=slug)
        self.db.add(org)
        await self.db.flush()

        # Get admin role
        admin_role = await self.get_role_by_name("admin")
        if not admin_role:
            raise ValueError("Admin role not found")

        # Create membership for creator as admin
        membership = Membership(
            user_id=creator.id,
            org_id=org.id,
            role_id=admin_role.id,
        )
        self.db.add(membership)

        # Create audit log
        audit = AuditLog(
            org_id=org.id,
            user_id=creator.id,
            action="create_organization",
            entity_type="organization",
            entity_id=org.id,
            details={"name": name},
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def invite_user(
        self,
        org_id: uuid.UUID,
        email: str,
        role_name: str,
        inviter: User,
    ) -> Membership:
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Check if already a member
        existing = await self.db.execute(
            select(Membership).where(
                Membership.org_id == org_id,
                Membership.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User is already a member")

        # Get role
        role = await self.get_role_by_name(role_name)
        if not role:
            raise ValueError("Role not found")

        # Create membership
        membership = Membership(
            user_id=user.id,
            org_id=org_id,
            role_id=role.id,
        )
        self.db.add(membership)

        # Audit log
        audit = AuditLog(
            org_id=org_id,
            user_id=inviter.id,
            action="invite_user",
            entity_type="membership",
            entity_id=user.id,
            details={"email": email, "role": role_name},
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def get_users(
        self,
        org_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Membership.id)).where(Membership.org_id == org_id)
        )
        total = count_result.scalar()

        # Get users with roles
        result = await self.db.execute(
            select(User, Membership, Role)
            .join(Membership, User.id == Membership.user_id)
            .join(Role, Membership.role_id == Role.id)
            .where(Membership.org_id == org_id)
            .offset(offset)
            .limit(limit)
        )

        users = []
        for user, membership, role in result.all():
            users.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": role.name,
                "is_active": membership.is_active,
            })

        return users, total
