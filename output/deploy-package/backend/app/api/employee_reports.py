from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.processes import normalize_process
from app.db.session import get_db_session
from app.services.auth import get_current_user
from app.services.work_reports import (
    get_work_report as get_work_report_service,
    list_work_report_history as list_work_report_history_service,
    query_work_reports as query_work_reports_service,
    save_work_report as save_work_report_service,
)

router = APIRouter()


class WorkReportRow(BaseModel):
    process_id: str = Field(min_length=1)
    quantity: float = Field(gt=0)


class WorkReportSave(BaseModel):
    work_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    rows: list[WorkReportRow] = Field(default_factory=list)


async def ensure_can_access_account(
    account_id: str,
    current_user: dict[str, object],
    session: AsyncSession,
) -> None:
    if account_id == current_user["id"]:
        return
    if current_user["role"] == "super_admin":
        return
    if current_user["role"] == "admin":
        result = await session.execute(
            text("select 1 from admin_accounts where id = :id and manager_id = :manager_id limit 1"),
            {"id": account_id, "manager_id": current_user["id"]},
        )
        if result.first():
            return
    raise HTTPException(status_code=403, detail="forbidden")


@router.get("/api/accounts/{account_id}/processes")
async def list_account_processes(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> list[dict[str, str | float]]:
    await ensure_can_access_account(account_id, current_user, session)
    result = await session.execute(
        text(
            """
            select process.id,
                   process.name,
                   process.price,
                   process.unit,
                   process.status,
                   process.manager_id
            from processes process
            inner join account_processes link on link.process_id = process.id
            where link.account_id = :account_id and process.status = 'active'
            order by process.created_at, process.id
            """
        ),
        {"account_id": account_id},
    )
    return [normalize_process(row) for row in result.fetchall()]


@router.get("/api/work-reports/{account_id}/{work_date}")
async def get_work_report(
    account_id: str,
    work_date: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> dict[str, object]:
    await ensure_can_access_account(account_id, current_user, session)
    return await get_work_report_service(account_id, work_date, session)


@router.get("/api/work-reports/query")
async def query_work_reports(
    account_id: str | None = Query(default=None),
    month: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    process_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> dict[str, object]:
    return await query_work_reports_service(
        session,
        current_user,
        account_id=account_id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        process_id=process_id,
        page=page,
        page_size=page_size,
    )


@router.get("/api/work-report-history/{account_id}")
async def list_work_report_history(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> dict[str, object]:
    await ensure_can_access_account(account_id, current_user, session)
    return await list_work_report_history_service(account_id, session)


@router.put("/api/work-reports/{account_id}")
async def save_work_report(
    account_id: str,
    payload: WorkReportSave,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> dict[str, object]:
    if account_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")
    return await save_work_report_service(account_id, payload, session)
