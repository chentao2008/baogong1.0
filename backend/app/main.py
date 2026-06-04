import time
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import engine, get_db_session

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_ACCOUNTS = [
    {
        "id": "u-super",
        "account": "admin",
        "password": "admin123",
        "role": "super_admin",
        "name": "超级管理员",
        "status": "active",
        "manager_id": None,
    },
    {
        "id": "u-manager",
        "account": "manager",
        "password": "manager123",
        "role": "admin",
        "name": "车间管理员",
        "status": "active",
        "manager_id": "u-super",
    },
    {
        "id": "u-employee",
        "account": "employee",
        "password": "employee123",
        "role": "employee",
        "name": "张师傅",
        "status": "active",
        "manager_id": "u-manager",
    },
]

DEFAULT_PROCESSES = [
    {"id": "p-cut", "name": "裁剪", "price": 1.2, "unit": "元/米", "status": "active"},
    {"id": "p-sew", "name": "缝制", "price": 2.6, "unit": "元/条", "status": "active"},
    {"id": "p-pack", "name": "包装", "price": 0.8, "unit": "元/包", "status": "disabled"},
]


class LoginRequest(BaseModel):
    account: str = Field(min_length=1)
    password: str = Field(min_length=1)


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


class ProcessCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    unit: str = Field(min_length=1)


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1)
    status: Literal["active", "disabled"] | None = None


class WorkReportRow(BaseModel):
    process_id: str = Field(min_length=1)
    quantity: float = Field(gt=0)


class WorkReportSave(BaseModel):
    work_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    rows: list[WorkReportRow] = Field(default_factory=list)


def normalize_account(row) -> dict[str, object]:
    return {
        "id": row.id,
        "account": row.account,
        "password": row.password,
        "role": row.role,
        "name": row.name,
        "status": row.status,
        "managerId": row.manager_id,
        "processIds": list(row.process_ids or []),
    }


def normalize_process(row) -> dict[str, str | float]:
    return {
        "id": row.id,
        "name": row.name,
        "price": float(row.price),
        "unit": row.unit,
        "status": row.status,
    }


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


async def ensure_unique_process(session: AsyncSession, name: str, process_id: str | None = None) -> None:
    result = await session.execute(
        text(
            """
            select id from processes
            where name = :name and (cast(:process_id as text) is null or id <> :process_id)
            limit 1
            """
        ),
        {"name": name, "process_id": process_id},
    )
    if result.first():
        raise HTTPException(status_code=409, detail="process name already exists")


@app.on_event("startup")
async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                create table if not exists admin_accounts (
                    id text primary key,
                    account text not null unique,
                    password text not null,
                    role text not null check (role in ('super_admin', 'admin', 'employee')),
                    name text not null,
                    status text not null check (status in ('active', 'disabled')),
                    manager_id text null,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists processes (
                    id text primary key,
                    name text not null unique,
                    price numeric(12, 2) not null check (price >= 0),
                    unit text not null,
                    status text not null check (status in ('active', 'disabled')),
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists account_processes (
                    account_id text not null references admin_accounts(id) on delete cascade,
                    process_id text not null references processes(id) on delete cascade,
                    primary key (account_id, process_id)
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists work_reports (
                    id text primary key,
                    account_id text not null references admin_accounts(id) on delete cascade,
                    work_date date not null,
                    process_id text not null references processes(id),
                    quantity numeric(12, 2) not null check (quantity > 0),
                    unit_price numeric(12, 2) not null check (unit_price >= 0),
                    total_price numeric(12, 2) not null check (total_price >= 0),
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )

        for account in DEFAULT_ACCOUNTS:
            await connection.execute(
                text(
                    """
                    insert into admin_accounts (id, account, password, role, name, status, manager_id)
                    values (:id, :account, :password, :role, :name, :status, :manager_id)
                    on conflict do nothing
                    """
                ),
                account,
            )

        for process in DEFAULT_PROCESSES:
            await connection.execute(
                text(
                    """
                    insert into processes (id, name, price, unit, status)
                    values (:id, :name, :price, :unit, :status)
                    on conflict do nothing
                    """
                ),
                process,
            )

        # Account-process permissions are managed explicitly from the account page.
        # Do not import legacy demo processes or auto-grant every process here.


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/health/db")
async def database_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | int]:
    result = await session.execute(text("select 1"))
    return {"status": "ok", "database": result.scalar_one()}


@app.post("/api/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
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
        {"account": payload.account.strip()},
    )
    row = result.first()
    if not row or row.password != payload.password or row.status != "active":
        raise HTTPException(status_code=401, detail="invalid account or password")

    return normalize_account(row)


@app.get("/api/admin/accounts")
async def list_accounts(session: AsyncSession = Depends(get_db_session)) -> list[dict[str, object]]:
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
            group by account.id
            order by account.created_at, account.id
            """
        )
    )
    return [normalize_account(row) for row in result.fetchall()]


@app.post("/api/admin/accounts", status_code=201)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    account = payload.account.strip()
    name = (payload.name or account).strip()
    await ensure_unique_account(session, account)

    account_id = f"u-{int(time.time() * 1000)}"
    await session.execute(
        text(
            """
            insert into admin_accounts (id, account, password, role, name, status, manager_id)
            values (:id, :account, :password, :role, :name, :status, :manager_id)
            """
        ),
        {
            "id": account_id,
            "account": account,
            "password": payload.password.strip(),
            "role": payload.role,
            "name": name,
            "status": payload.status,
            "manager_id": payload.manager_id,
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
    return normalize_account(result.one())


@app.patch("/api/admin/accounts/{account_id}")
async def update_account(
    account_id: str,
    payload: AccountUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
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
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="account not found")

    next_account = payload.account.strip() if payload.account is not None else row.account
    if payload.account is not None:
        await ensure_unique_account(session, next_account, account_id)

    await session.execute(
        text(
            """
            update admin_accounts
            set account = :account,
                password = :password,
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
            "password": payload.password.strip() if payload.password is not None else row.password,
            "role": payload.role or row.role,
            "name": payload.name.strip() if payload.name is not None else (next_account if payload.account is not None else row.name),
            "status": payload.status or row.status,
            "manager_id": payload.manager_id if payload.manager_id is not None else row.manager_id,
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
    return normalize_account(result.one())


@app.delete("/api/admin/accounts/{account_id}", status_code=204)
async def delete_account(account_id: str, session: AsyncSession = Depends(get_db_session)) -> None:
    result = await session.execute(text("delete from admin_accounts where id = :id"), {"id": account_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="account not found")
    await session.commit()


@app.get("/api/admin/processes")
async def list_processes(session: AsyncSession = Depends(get_db_session)) -> list[dict[str, str | float]]:
    result = await session.execute(
        text(
            """
            select id, name, price, unit, status
            from processes
            order by created_at, id
            """
        )
    )
    return [normalize_process(row) for row in result.fetchall()]


@app.post("/api/admin/processes", status_code=201)
async def create_process(
    payload: ProcessCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | float]:
    name = payload.name.strip()
    unit = payload.unit.strip()
    await ensure_unique_process(session, name)

    process_id = f"p-{int(time.time() * 1000)}"
    await session.execute(
        text(
            """
            insert into processes (id, name, price, unit, status)
            values (:id, :name, :price, :unit, 'active')
            """
        ),
        {"id": process_id, "name": name, "price": payload.price, "unit": unit},
    )
    await session.commit()

    result = await session.execute(
        text("select id, name, price, unit, status from processes where id = :id"),
        {"id": process_id},
    )
    return normalize_process(result.one())


@app.patch("/api/admin/processes/{process_id}")
async def update_process(
    process_id: str,
    payload: ProcessUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | float]:
    result = await session.execute(
        text("select id, name, price, unit, status from processes where id = :id"),
        {"id": process_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="process not found")

    next_name = payload.name.strip() if payload.name is not None else row.name
    if payload.name is not None:
        await ensure_unique_process(session, next_name, process_id)

    await session.execute(
        text(
            """
            update processes
            set name = :name,
                price = :price,
                unit = :unit,
                status = :status,
                updated_at = now()
            where id = :id
            """
        ),
        {
            "id": process_id,
            "name": next_name,
            "price": payload.price if payload.price is not None else row.price,
            "unit": payload.unit.strip() if payload.unit is not None else row.unit,
            "status": payload.status or row.status,
        },
    )
    await session.commit()

    result = await session.execute(
        text("select id, name, price, unit, status from processes where id = :id"),
        {"id": process_id},
    )
    return normalize_process(result.one())


@app.delete("/api/admin/processes/{process_id}", status_code=204)
async def delete_process(process_id: str, session: AsyncSession = Depends(get_db_session)) -> None:
    result = await session.execute(text("delete from processes where id = :id"), {"id": process_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="process not found")
    await session.commit()


@app.get("/api/accounts/{account_id}/processes")
async def list_account_processes(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, str | float]]:
    result = await session.execute(
        text(
            """
            select process.id, process.name, process.price, process.unit, process.status
            from processes process
            inner join account_processes link on link.process_id = process.id
            where link.account_id = :account_id and process.status = 'active'
            order by process.created_at, process.id
            """
        ),
        {"account_id": account_id},
    )
    return [normalize_process(row) for row in result.fetchall()]


@app.get("/api/work-reports/{account_id}/{work_date}")
async def get_work_report(
    account_id: str,
    work_date: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    result = await session.execute(
        text(
            """
            select report.id,
                   report.process_id,
                   process.name as process_name,
                   report.quantity,
                   report.unit_price,
                   report.total_price
            from work_reports report
            inner join processes process on process.id = report.process_id
            where report.account_id = :account_id and report.work_date = to_date(:work_date, 'YYYY-MM-DD')
            order by report.created_at, report.id
            """
        ),
        {"account_id": account_id, "work_date": work_date},
    )
    rows = [
        {
            "id": row.id,
            "processId": row.process_id,
            "processName": row.process_name,
            "quantity": float(row.quantity),
            "unitPrice": float(row.unit_price),
            "totalPrice": float(row.total_price),
        }
        for row in result.fetchall()
    ]
    return {"workDate": work_date, "rows": rows, "dailyWage": sum(row["totalPrice"] for row in rows)}


@app.get("/api/work-report-history/{account_id}")
async def list_work_report_history(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    result = await session.execute(
        text(
            """
            select report.work_date,
                   report.process_id,
                   process.name as process_name,
                   report.quantity,
                   report.unit_price,
                   report.total_price
            from work_reports report
            inner join processes process on process.id = report.process_id
            where report.account_id = :account_id
            order by report.work_date desc, report.created_at desc, report.id desc
            """
        ),
        {"account_id": account_id},
    )
    rows = [
        {
            "workDate": row.work_date.isoformat(),
            "processId": row.process_id,
            "processName": row.process_name,
            "quantity": float(row.quantity),
            "unitPrice": float(row.unit_price),
            "totalPrice": float(row.total_price),
            "confirmStatus": "未确认",
        }
        for row in result.fetchall()
    ]
    return {"rows": rows, "totalWage": sum(row["totalPrice"] for row in rows)}


@app.put("/api/work-reports/{account_id}")
async def save_work_report(
    account_id: str,
    payload: WorkReportSave,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    work_date = date.fromisoformat(payload.work_date)
    if work_date > date.today():
        raise HTTPException(status_code=400, detail="不能提前报工")

    if not payload.rows:
        raise HTTPException(status_code=400, detail="请至少提交一条报工记录")

    process_ids = [row.process_id for row in payload.rows]
    if len(process_ids) != len(set(process_ids)):
        raise HTTPException(status_code=400, detail="同一天同一个工序只能报一次")

    existing_result = await session.execute(
        text(
            """
            select 1
            from work_reports
            where account_id = :account_id and work_date = to_date(:work_date, 'YYYY-MM-DD')
            limit 1
            """
        ),
        {"account_id": account_id, "work_date": payload.work_date},
    )
    if existing_result.first():
        raise HTTPException(status_code=409, detail="该日期已报工，记录不能再次提交或修改")

    for index, row in enumerate(payload.rows):
        process_result = await session.execute(
            text(
                """
                select price
                from processes
                where id = :process_id
                """
            ),
            {"process_id": row.process_id},
        )
        process = process_result.first()
        if not process:
            raise HTTPException(status_code=404, detail="process not found")

        unit_price = float(process.price)
        quantity = float(row.quantity)
        await session.execute(
            text(
                """
                insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                values (:id, :account_id, to_date(:work_date, 'YYYY-MM-DD'), :process_id, :quantity, :unit_price, :total_price)
                """
            ),
            {
                "id": f"wr-{int(time.time() * 1000)}-{index}",
                "account_id": account_id,
                "work_date": payload.work_date,
                "process_id": row.process_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": unit_price * quantity,
            },
        )

    await session.commit()
    return await get_work_report(account_id, payload.work_date, session)
