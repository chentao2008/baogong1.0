from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.auth import (
    clear_session_cookie,
    create_session,
    delete_session,
    get_account_by_account,
    get_current_user,
    public_user,
    set_session_cookie,
    upgrade_plaintext_password_if_needed,
    verify_password,
)
from app.services.login_rate_limit import check_locked, clear_failures, record_failure

router = APIRouter()


class LoginRequest(BaseModel):
    account: str = Field(min_length=1)
    password: str = Field(min_length=1)


async def authenticate(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession,
) -> dict[str, object]:
    settings = get_settings()
    account = payload.account.strip()
    locked_message = check_locked(account, settings.login_lockout_seconds)
    if locked_message:
        raise HTTPException(status_code=429, detail=locked_message)

    row = await get_account_by_account(session, account)
    if not row or row.status != "active" or not verify_password(payload.password, row.password):
        record_failure(account, settings.login_max_failures, settings.login_lockout_seconds)
        raise HTTPException(status_code=401, detail="invalid account or password")

    clear_failures(account)
    await upgrade_plaintext_password_if_needed(session, row.id, row.password, payload.password)
    token = await create_session(session, row.id)
    await session.commit()
    set_session_cookie(response, token)
    return public_user(row)


@router.post("/api/auth/login")
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return await authenticate(payload, response, session)


@router.post("/api/login")
async def legacy_login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return await authenticate(payload, response, session)


@router.post("/api/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    await delete_session(session, request.cookies.get(get_settings().session_cookie_name))
    await session.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/api/logout")
async def legacy_logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    return await logout(request, response, session)


@router.get("/api/me")
async def current_user(current_user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    return current_user
