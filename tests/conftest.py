import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role

# Module-level container to reuse across tests
_postgres_container = None
_database_url = None


def get_postgres_container():
    global _postgres_container, _database_url
    if _postgres_container is None:
        _postgres_container = PostgresContainer("postgres:16-alpine")
        _postgres_container.start()
        url = _postgres_container.get_connection_url()
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        _database_url = url
    return _database_url


@pytest.fixture(scope="session", autouse=True)
def cleanup_container():
    yield
    global _postgres_container
    if _postgres_container is not None:
        _postgres_container.stop()
        _postgres_container = None


@pytest_asyncio.fixture
async def engine():
    database_url = get_postgres_container()
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed roles
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(select(Role))
        if not result.scalars().all():
            admin_role = Role(name="admin", description="Organization administrator")
            member_role = Role(name="member", description="Organization member")
            session.add_all([admin_role, member_role])
            await session.commit()

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Helper fixtures for common test scenarios
@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    data["_email"] = email
    data["_password"] = "testpassword123"
    return data


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, registered_user: dict) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["_email"],
            "password": registered_user["_password"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def organization(client: AsyncClient, auth_headers: dict) -> dict:
    response = await client.post(
        "/api/v1/organization",
        json={"org_name": "Test Organization"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def second_user(client: AsyncClient) -> dict:
    unique_id = uuid.uuid4().hex[:8]
    email = f"seconduser_{unique_id}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123456",
            "full_name": "Second User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    data["_email"] = email
    data["_password"] = "password123456"
    return data


@pytest_asyncio.fixture
async def second_user_token(client: AsyncClient, second_user: dict) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user["_email"],
            "password": second_user["_password"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def second_user_headers(second_user_token: str) -> dict:
    return {"Authorization": f"Bearer {second_user_token}"}
