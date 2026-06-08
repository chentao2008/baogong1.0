from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import get_current_user, require_admin
from app.services.word_export import build_monthly_work_report_docx
from app.services.work_reports import query_monthly_work_report_details

router = APIRouter()


def _build_export_filename(employee_name: str, month: str) -> str:
    safe_name = "".join(char for char in employee_name if char not in '\\/:*?"<>|').strip() or "员工"
    return f"员工月度报工详情_{safe_name}_{month}.docx"


def _content_disposition(filename: str) -> str:
    ascii_name = filename.encode("ascii", "ignore").decode() or "export.docx"
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


async def _build_monthly_export_response(
    session: AsyncSession,
    current_user: dict[str, object],
    account_id: str,
    month: str,
) -> Response:
    payload = await query_monthly_work_report_details(session, current_user, account_id, month)
    account = payload["account"]
    export_date = date.today()
    content = build_monthly_work_report_docx(
        employee_name=str(account["name"] or account["account"]),
        employee_account=str(account["account"]),
        month=str(payload["month"]),
        export_date=export_date,
        rows=list(payload["rows"]),
        summary=dict(payload["summary"]),
    )
    filename = _build_export_filename(str(account["name"] or account["account"]), str(payload["month"]))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/api/employee/work-reports/monthly-export")
async def export_employee_monthly_work_report(
    month: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> Response:
    if current_user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="forbidden")
    return await _build_monthly_export_response(session, current_user, str(current_user["id"]), month)


@router.get("/api/admin/work-reports/monthly-export")
async def export_admin_monthly_work_report(
    account_id: str = Query(..., min_length=1),
    month: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict[str, object] = Depends(require_admin),
) -> Response:
    return await _build_monthly_export_response(session, current_user, account_id, month)
