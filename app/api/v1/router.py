from fastapi import APIRouter

from app.api.v1.endpoints import auth, organizations, items, audit_logs

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(items.router)
api_router.include_router(audit_logs.router)
