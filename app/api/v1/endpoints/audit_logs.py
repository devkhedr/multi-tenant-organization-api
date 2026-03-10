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

    if not data.stream:
        try:
            answer = await service.ask(org_id, data.question)
            return ChatbotResponse(answer=answer)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    stream_gen = service.ask_stream(org_id, data.question)
    try:
        first_chunk = await stream_gen.__anext__()
        has_first = True
    except StopAsyncIteration:
        first_chunk = None
        has_first = False
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def generate():
        if has_first and first_chunk is not None:
            yield first_chunk
        try:
            async for chunk in stream_gen:
                yield chunk
        except RuntimeError as e:
            yield f"[Error: {str(e)}]"

    return StreamingResponse(generate(), media_type="text/plain")
