from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.work_reports import list_work_report_history

router = APIRouter()


@router.get("/api/admin/reports/{account_id}")
async def list_admin_reports(
    account_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> dict[str, object]:
    if current_user["role"] != "super_admin":
        result = await session.execute(
            text("select 1 from admin_accounts where id = :id and manager_id = :manager_id limit 1"),
            {"id": account_id, "manager_id": current_user["id"]},
        )
        if not result.first():
            raise HTTPException(status_code=403, detail="forbidden")
    return await list_work_report_history(account_id, session)
