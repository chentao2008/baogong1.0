import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

settings = get_settings()
SESSION_COOKIE_SAMESITE = "lax"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_password_hash(value: str | None) -> bool:
    return bool(value and value.startswith(("$2a$", "$2b$", "$2y$")))


def verify_password(password: str, stored_password: str | None) -> bool:
    if not stored_password:
        return False
    if not is_password_hash(stored_password):
        return secrets.compare_digest(stored_password, password)
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8"))
    except ValueError:
        return False


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def public_user(row) -> dict[str, object]:
    return {
        "id": row.id,
        "account": row.account,
        "role": row.role,
        "name": row.name,
        "status": row.status,
        "managerId": row.manager_id,
        "processIds": list(row.process_ids or []),
    }


async def get_account_by_account(session: AsyncSession, account: str):
    result = await session.execute(
        text(
            """
            select account.id,
                   account.account,
                   account.password,
                   account.role,
                   account.name,
                   account.status,
                   account.manager_id,
                   coalesce(array_agg(link.process_id) filter (where link.process_id is not null), '{}') as process_ids
            from admin_accounts account
            left join account_processes link on link.account_id = account.id
            where account.account = :account
            group by account.id
            """
        ),
        {"account": account},
    )
    return result.first()


async def get_account_by_id(session: AsyncSession, account_id: str):
    result = await session.execute(
        text(
            """
            select account.id,
                   account.account,
                   account.password,
                   account.role,
                   account.name,
                   account.status,
                   account.manager_id,
                   coalesce(array_agg(link.process_id) filter (where link.process_id is not null), '{}') as process_ids
            from admin_accounts account
            left join account_processes link on link.account_id = account.id
            where account.id = :id
            group by account.id
            """
        ),
        {"id": account_id},
    )
    return result.first()


async def upgrade_plaintext_password_if_needed(session: AsyncSession, account_id: str, stored_password: str, password: str) -> None:
    if is_password_hash(stored_password):
        return
    await session.execute(
        text("update admin_accounts set password = :password, updated_at = now() where id = :id"),
        {"id": account_id, "password": hash_password(password)},
    )


async def create_session(session: AsyncSession, account_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds)
    await session.execute(
        text(
            """
            insert into auth_sessions (id, account_id, expires_at)
            values (:id, :account_id, :expires_at)
            """
        ),
        {"id": hash_session_token(token), "account_id": account_id, "expires_at": expires_at},
    )
    return token


async def delete_session(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    await session.execute(text("delete from auth_sessions where id = :id"), {"id": hash_session_token(token)})


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.use_secure_session_cookie,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.use_secure_session_cookie,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")

    result = await session.execute(
        text(
            """
            select account.id,
                   account.account,
                   account.password,
                   account.role,
                   account.name,
                   account.status,
                   account.manager_id,
                   coalesce(array_agg(link.process_id) filter (where link.process_id is not null), '{}') as process_ids
            from auth_sessions auth_session
            inner join admin_accounts account on account.id = auth_session.account_id
            left join account_processes link on link.account_id = account.id
            where auth_session.id = :id
              and auth_session.expires_at > now()
              and account.status = 'active'
            group by account.id
            """
        ),
        {"id": hash_session_token(token)},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=401, detail="not authenticated")

    return public_user(row)


def require_admin(current_user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    if current_user.get("role") not in {"super_admin", "admin"}:
        raise HTTPException(status_code=403, detail="forbidden")
    return current_user


def require_super_admin(current_user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return current_user
