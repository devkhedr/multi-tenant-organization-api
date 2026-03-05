import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog


class ChatbotService:
    def __init__(self, db: AsyncSession):
        self.db = db
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.model_name = "gemini-2.0-flash"
        else:
            self.client = None
            self.model_name = None

    async def get_today_logs(self, org_id: uuid.UUID) -> list[dict]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.org_id == org_id,
                AuditLog.created_at >= today_start,
            )
            .order_by(AuditLog.created_at.desc())
        )

        logs = []
        for log in result.scalars().all():
            logs.append({
                "action": log.action,
                "entity_type": log.entity_type,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            })
        return logs

    def build_prompt(self, question: str, logs: list[dict]) -> str:
        logs_text = "\n".join([
            f"- {log['created_at']}: {log['action']} on {log['entity_type']} - {log['details']}"
            for log in logs
        ])

        return f"""You analyze organization activity logs. Answer questions based on the logs below.

Note: "invite_user" = user created/added, "create_item" = item created.

Logs:
{logs_text if logs else "No logs for today."}

Question: {question}

Answer in plain text only. No markdown, no bullets, no special formatting."""

    async def ask(self, org_id: uuid.UUID, question: str) -> str:
        if not self.client:
            return "Chatbot is not configured. Please set GEMINI_API_KEY."

        logs = await self.get_today_logs(org_id)
        prompt = self.build_prompt(question, logs)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

    async def ask_stream(
        self, org_id: uuid.UUID, question: str
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            yield "Chatbot is not configured. Please set GEMINI_API_KEY."
            return

        logs = await self.get_today_logs(org_id)
        prompt = self.build_prompt(question, logs)

        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
        ):
            if chunk.text:
                yield chunk.text
