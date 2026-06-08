import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin

router = APIRouter()


class ProcessCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    unit: str = Field(min_length=1)


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1)
    status: Literal["active", "disabled"] | None = None


def normalize_process(row) -> dict[str, str | float | None]:
    return {
        "id": row.id,
        "name": row.name,
        "price": float(row.price),
        "unit": row.unit,
        "status": row.status,
        "managerId": row.manager_id,
    }


async def ensure_unique_process(
    session: AsyncSession,
    name: str,
    manager_id: str,
    process_id: str | None = None,
) -> None:
    result = await session.execute(
        text(
            """
            select id from processes
            where name = :name
              and manager_id = :manager_id
              and (cast(:process_id as text) is null or id <> :process_id)
            limit 1
            """
        ),
        {"name": name, "manager_id": manager_id, "process_id": process_id},
    )
    if result.first():
        raise HTTPException(status_code=409, detail="process name already exists")


@router.get("/api/admin/processes")
async def list_processes(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> list[dict[str, str | float | None]]:
    where_clause = ""
    params = {}
    if current_user["role"] != "super_admin":
        where_clause = "where manager_id = :manager_id"
        params["manager_id"] = current_user["id"]

    result = await session.execute(
        text(
            """
            select id, name, price, unit, status, manager_id
            from processes
            """
            + where_clause
            + """
            order by created_at, id
            """
        ),
        params,
    )
    return [normalize_process(row) for row in result.fetchall()]


@router.post("/api/admin/processes", status_code=201)
async def create_process(
    payload: ProcessCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, str | float | None]:
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")

    name = payload.name.strip()
    unit = payload.unit.strip()
    await ensure_unique_process(session, name, str(current_user["id"]))

    process_id = f"p-{int(time.time() * 1000)}"
    await session.execute(
        text(
            """
            insert into processes (id, name, price, unit, status, manager_id)
            values (:id, :name, :price, :unit, 'active', :manager_id)
            """
        ),
        {"id": process_id, "name": name, "price": payload.price, "unit": unit, "manager_id": current_user["id"]},
    )
    await session.commit()

    result = await session.execute(
        text("select id, name, price, unit, status, manager_id from processes where id = :id"),
        {"id": process_id},
    )
    return normalize_process(result.one())


@router.patch("/api/admin/processes/{process_id}")
async def update_process(
    process_id: str,
    payload: ProcessUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, str | float | None]:
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")

    result = await session.execute(
        text("select id, name, price, unit, status, manager_id from processes where id = :id"),
        {"id": process_id},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="process not found")
    if current_user["role"] != "super_admin" and row.manager_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")

    next_name = payload.name.strip() if payload.name is not None else row.name
    if payload.name is not None:
        await ensure_unique_process(session, next_name, str(current_user["id"]), process_id)

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
        text("select id, name, price, unit, status, manager_id from processes where id = :id"),
        {"id": process_id},
    )
    return normalize_process(result.one())


@router.delete("/api/admin/processes/{process_id}", status_code=204)
async def delete_process(
    process_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> None:
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=403, detail="forbidden")

    result = await session.execute(
        text("delete from processes where id = :id and manager_id = :manager_id"),
        {"id": process_id, "manager_id": current_user["id"]},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="process not found")
    await session.commit()
