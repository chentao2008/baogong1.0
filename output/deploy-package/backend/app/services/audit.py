import json
import logging
import secrets
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def generate_audit_id() -> str:
    return f"audit-{secrets.token_urlsafe(16)}"


def get_request_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


async def write_audit_log(
    session: AsyncSession,
    *,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
    required: bool = False,
) -> None:
    try:
        await session.execute(
            text(
                """
                insert into audit_logs (id, actor_id, action, target_type, target_id, payload_json)
                values (:id, :actor_id, :action, :target_type, :target_id, cast(:payload_json as jsonb))
                """
            ),
            {
                "id": generate_audit_id(),
                "actor_id": actor_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "payload_json": json.dumps(payload, ensure_ascii=False),
            },
        )
    except Exception:
        logger.exception(
            "failed to write audit log action=%s actor_id=%s target_id=%s",
            action,
            actor_id,
            target_id,
        )
        if required:
            raise HTTPException(status_code=500, detail="audit log write failed") from None
