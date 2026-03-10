import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models import User, Membership
from app.schemas.audit_log import AuditLogEntry, PaginatedAuditLogs
from app.schemas.chatbot import ChatbotQuestion, ChatbotResponse
from app.services.audit_log import AuditLogService
from app.services.chatbot import ChatbotService

router = APIRouter(tags=["audit-logs"])


@router.get("/organizations/{org_id}/audit-logs", response_model=PaginatedAuditLogs)
async def get_audit_logs(
    org_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_admin),
):
    service = AuditLogService(db)
    logs, total = await service.get_logs(org_id, limit, offset)

    return PaginatedAuditLogs(
        logs=[
            AuditLogEntry(
                id=str(log.id),
                user_id=str(log.user_id) if log.user_id else None,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=str(log.entity_id) if log.entity_id else None,
                details=log.details,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/organizations/{org_id}/audit-logs/ask")
async def ask_chatbot(
    org_id: uuid.UUID,
    data: ChatbotQuestion,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_admin),
):
    service = ChatbotService(db)

    # Check if chatbot is configured before starting
    if not service.client:
        raise HTTPException(
            status_code=503,
            detail="Chatbot is not configured. Please set GEMINI_API_KEY."
        )

    try:
        if data.stream:
            async def generate():
                async for chunk in service.ask_stream(org_id, data.question):
                    yield chunk

            return StreamingResponse(generate(), media_type="text/plain")
        else:
            answer = await service.ask(org_id, data.question)
            return ChatbotResponse(answer=answer)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
