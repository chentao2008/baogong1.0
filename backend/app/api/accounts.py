import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.audit import get_request_ip, write_audit_log
from app.services.auth import get_account_by_id, hash_password, public_user, require_admin
from app.services.password_view import build_password_display, encrypt_viewable_password

router = APIRouter()


class AccountCreate(BaseModel):
    account: str = Field(min_length=1)
    password: str = Field(min_length=1)
    role: Literal["super_admin", "admin", "employee"]
    name: str | None = None
    status: Literal["active", "disabled"] = "active"
    manager_id: str | None = None
    process_ids: list[str] = Field(default_factory=list)


class AccountUpdate(BaseModel):
    account: str | None = Field(default=None, min_length=1)
    password: str | None = Field(default=None, min_length=1)
    role: Literal["super_admin", "admin", "employee"] | None = None
    name: str | None = Field(default=None, min_length=1)
    status: Literal["active", "disabled"] | None = None
    manager_id: str | None = None
    process_ids: list[str] | None = None


class AccountPasswordReset(BaseModel):
    password: str = Field(min_length=6)


def normalize_account(row, include_password_display: bool = False) -> dict[str, object]:
    account = public_user(row)
    if include_password_display:
        account["passwordDisplay"] = build_password_display(row.password_view_ciphertext)[0]
    return account


def account_with_password_display(row) -> tuple[dict[str, object], bool]:
    account = public_user(row)
    password_display, was_viewable = build_password_display(row.password_view_ciphertext)
    account["passwordDisplay"] = password_display
    return account, was_viewable


def can_reset_password(current_user: dict[str, object], target_row) -> bool:
    if current_user["role"] == "super_admin":
        return True
    return (
        current_user["role"] == "admin"
        and target_row.role == "employee"
        and target_row.manager_id == current_user["id"]
    )


async def ensure_unique_account(session: AsyncSession, account: str, account_id: str | None = None) -> None:
    result = await session.execute(
        text(
            """
            select id from admin_accounts
            where account = :account and (cast(:account_id as text) is null or id <> :account_id)
            limit 1
            """
        ),
        {"account": account, "account_id": account_id},
    )
    if result.first():
        raise HTTPException(status_code=409, detail="account already exists")


async def ensure_processes_belong_to_manager(
    session: AsyncSession,
    process_ids: list[str],
    manager_id: str,
) -> None:
    unique_process_ids = set(process_ids)
    if not unique_process_ids:
        return

    result = await session.execute(
        text(
            """
            select count(*) from processes
            where id = any(:process_ids)
              and manager_id = :manager_id
            """
        ),
        {"process_ids": list(unique_process_ids), "manager_id": manager_id},
    )
    if result.scalar_one() != len(unique_process_ids):
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/api/admin/accounts")
async def list_accounts(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> list[dict[str, object]]:
    where_clause = ""
    params = {}
    if current_user["role"] != "super_admin":
        where_clause = "where account.id = :current_user_id or account.manager_id = :current_user_id"
        params["current_user_id"] = current_user["id"]

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
                   account.password_view_ciphertext,
                   coalesce(array_agg(link.process_id) filter (where link.process_id is not null), '{}') as process_ids
            from admin_accounts account
            left join account_processes link on link.account_id = account.id
            """
            + where_clause
            + """
            group by account.id
            order by account.created_at, account.id
            """
        ),
        params,
    )
    include_password_display = current_user["role"] == "super_admin"
    rows = result.fetchall()
    viewable_by_id: dict[str, bool] = {}
    accounts = []
    for row in rows:
        if include_password_display:
            account, was_viewable = account_with_password_display(row)
            viewable_by_id[str(row.id)] = was_viewable
            accounts.append(account)
        else:
            accounts.append(normalize_account(row))

    if include_password_display:
        request_ip = get_request_ip(request)
        for row in rows:
            if not viewable_by_id.get(str(row.id)):
                continue
            await write_audit_log(
                session,
                actor_id=str(current_user["id"]),
                action="password_view_list",
                target_type="account",
                target_id=str(row.id),
                payload={
                    "target_account": row.account,
                    "target_role": row.role,
                    "whether_password_was_viewable": True,
                    "request_ip": request_ip,
                },
                required=True,
            )
        await session.commit()

    return accounts


@router.post("/api/admin/accounts", status_code=201)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, object]:
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")
    if payload.role != "employee":
        raise HTTPException(status_code=403, detail="forbidden")

    account = payload.account.strip()
    name = (payload.name or account).strip()
    await ensure_unique_account(session, account)
    await ensure_processes_belong_to_manager(session, payload.process_ids, str(current_user["id"]))

    account_id = f"u-{int(time.time() * 1000)}"
    manager_id = str(current_user["id"])
    await session.execute(
        text(
            """
            insert into admin_accounts (
                id, account, password, role, name, status, manager_id,
                password_view_ciphertext, password_view_updated_at
            )
            values (
                :id, :account, :password, :role, :name, :status, :manager_id,
                :password_view_ciphertext,
                case when cast(:password_view_ciphertext as text) is null then null else now() end
            )
            """
        ),
        {
            "id": account_id,
            "account": account,
            "password": hash_password(payload.password.strip()),
            "role": payload.role,
            "name": name,
            "status": payload.status,
            "manager_id": manager_id,
            "password_view_ciphertext": encrypt_viewable_password(payload.password.strip()),
        },
    )
    for process_id in payload.process_ids:
        await session.execute(
            text(
                """
                insert into account_processes (account_id, process_id)
                values (:account_id, :process_id)
                on conflict do nothing
                """
            ),
            {"account_id": account_id, "process_id": process_id},
        )
    await session.commit()

    row = await get_account_by_id(session, account_id)
    return normalize_account(row)


@router.post("/api/admin/accounts/{account_id}/reset-password")
async def reset_account_password(
    account_id: str,
    payload: AccountPasswordReset,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, object]:
    row = await get_account_by_id(session, account_id)
    if not row:
        raise HTTPException(status_code=404, detail="account not found")
    if not can_reset_password(current_user, row):
        raise HTTPException(status_code=403, detail="forbidden")

    next_password = payload.password.strip()
    if len(next_password) < 6:
        raise HTTPException(status_code=422, detail="password must be at least 6 characters")
    password_view_ciphertext = encrypt_viewable_password(next_password)
    await session.execute(
        text(
            """
            update admin_accounts
            set password = :password,
                password_view_ciphertext = :password_view_ciphertext,
                password_view_updated_at = case
                    when cast(:password_view_ciphertext as text) is null then null
                    else now()
                end,
                updated_at = now()
            where id = :id
            """
        ),
        {
            "id": account_id,
            "password": hash_password(next_password),
            "password_view_ciphertext": password_view_ciphertext,
        },
    )
    await write_audit_log(
        session,
        actor_id=str(current_user["id"]),
        action="password_reset",
        target_type="account",
        target_id=str(row.id),
        payload={
            "target_account": row.account,
            "target_role": row.role,
            "whether_password_was_viewable": password_view_ciphertext is not None,
            "request_ip": get_request_ip(request),
        },
        required=True,
    )
    await session.commit()

    row = await get_account_by_id(session, account_id)
    return normalize_account(row, include_password_display=current_user["role"] == "super_admin")


@router.patch("/api/admin/accounts/{account_id}")
async def update_account(
    account_id: str,
    payload: AccountUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, object]:
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")

    row = await get_account_by_id(session, account_id)
    if not row:
        raise HTTPException(status_code=404, detail="account not found")
    if row.manager_id != current_user["id"] and row.id != current_user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")
    if payload.role is not None and payload.role != row.role:
        raise HTTPException(status_code=403, detail="forbidden")
    if payload.password is not None:
        raise HTTPException(status_code=400, detail="use reset password endpoint")
    if row.id == current_user["id"] and payload.status == "disabled":
        raise HTTPException(status_code=403, detail="forbidden")
    if payload.process_ids is not None:
        await ensure_processes_belong_to_manager(session, payload.process_ids, str(current_user["id"]))

    next_account = payload.account.strip() if payload.account is not None else row.account
    if payload.account is not None:
        await ensure_unique_account(session, next_account, account_id)
    next_manager_id = row.manager_id

    await session.execute(
        text(
            """
            update admin_accounts
            set account = :account,
                role = :role,
                name = :name,
                status = :status,
                manager_id = :manager_id,
                updated_at = now()
            where id = :id
            """
        ),
        {
            "id": account_id,
            "account": next_account,
            "role": payload.role or row.role,
            "name": payload.name.strip() if payload.name is not None else (next_account if payload.account is not None else row.name),
            "status": payload.status or row.status,
            "manager_id": next_manager_id,
        },
    )
    if payload.process_ids is not None:
        await session.execute(text("delete from account_processes where account_id = :id"), {"id": account_id})
        for process_id in payload.process_ids:
            await session.execute(
                text(
                    """
                    insert into account_processes (account_id, process_id)
                    values (:account_id, :process_id)
                    on conflict do nothing
                    """
                ),
                {"account_id": account_id, "process_id": process_id},
            )
    await session.commit()

    row = await get_account_by_id(session, account_id)
    return normalize_account(row)


@router.delete("/api/admin/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> None:
    if current_user["role"] == "super_admin" or account_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")
    result = await session.execute(
        text("delete from admin_accounts where id = :id and manager_id = :manager_id and role = 'employee'"),
        {"id": account_id, "manager_id": current_user["id"]},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="account not found")
    await session.commit()
