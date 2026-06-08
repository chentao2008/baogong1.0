import time
from datetime import date

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def calculate_total_price(unit_price: float, quantity: float) -> float:
    return unit_price * quantity


async def get_work_report(
    account_id: str,
    work_date: str,
    session: AsyncSession,
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


async def _assert_can_read_account(
    session: AsyncSession,
    current_user: dict[str, object],
    account_id: str,
) -> None:
    if account_id == current_user["id"]:
        return
    role = current_user.get("role")
    if role == "super_admin":
        return
    if role == "admin":
        result = await session.execute(
            text("select 1 from admin_accounts where id = :id and manager_id = :manager_id limit 1"),
            {"id": account_id, "manager_id": current_user["id"]},
        )
        if result.first():
            return
    raise HTTPException(status_code=403, detail="forbidden")


def _validate_month(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) != 7 or value[4] != "-" or not value[:4].isdigit() or not value[5:].isdigit():
        raise HTTPException(status_code=400, detail="invalid month")
    try:
        date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid month") from exc
    return value


def _validate_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date") from exc
    return value


async def query_work_reports(
    session: AsyncSession,
    current_user: dict[str, object],
    *,
    account_id: str | None = None,
    month: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    process_id: str | None = None,
    page: int = 1,
    page_size: int = 15,
) -> dict[str, object]:
    """按参数在服务端查询/分页/汇总 work_reports。

    权限：
      - account_id 指定时，必须是本人，或本人是 super_admin / 该员工的上级 admin。
      - account_id 省略时，仅允许 admin / super_admin；admin 只看自己管理的员工。
    """
    role = current_user.get("role")
    user_id = str(current_user["id"])

    if account_id:
        await _assert_can_read_account(session, current_user, account_id)
    else:
        if role not in {"admin", "super_admin"}:
            raise HTTPException(status_code=403, detail="forbidden")

    month = _validate_month(month)
    start_date = _validate_date(start_date)
    end_date = _validate_date(end_date)

    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 15), 1000))

    where_parts: list[str] = []
    params: dict[str, object] = {}

    if account_id:
        where_parts.append("report.account_id = :account_id")
        params["account_id"] = account_id
    elif role == "admin":
        where_parts.append("account.manager_id = :manager_id")
        params["manager_id"] = user_id

    if month:
        where_parts.append("to_char(report.work_date, 'YYYY-MM') = :month")
        params["month"] = month
    if start_date:
        where_parts.append("report.work_date >= to_date(:start_date, 'YYYY-MM-DD')")
        params["start_date"] = start_date
    if end_date:
        where_parts.append("report.work_date <= to_date(:end_date, 'YYYY-MM-DD')")
        params["end_date"] = end_date
    if process_id:
        where_parts.append("report.process_id = :process_id")
        params["process_id"] = process_id

    where_clause = ("where " + " and ".join(where_parts)) if where_parts else ""

    summary_sql = f"""
        select coalesce(sum(report.total_price), 0) as total_wage,
               coalesce(sum(report.quantity), 0) as total_quantity,
               count(distinct report.work_date) as work_days,
               count(*) as total_rows
        from work_reports report
        inner join admin_accounts account on account.id = report.account_id
        {where_clause}
    """
    summary_row = (await session.execute(text(summary_sql), params)).first()
    total = int(summary_row.total_rows or 0) if summary_row else 0
    summary = {
        "totalWage": float(summary_row.total_wage or 0) if summary_row else 0.0,
        "totalQuantity": float(summary_row.total_quantity or 0) if summary_row else 0.0,
        "workDays": int(summary_row.work_days or 0) if summary_row else 0,
    }

    offset = (page - 1) * page_size
    rows_sql = f"""
        select report.id,
               report.account_id,
               account.account as account_login,
               account.name as account_name,
               report.work_date,
               report.process_id,
               process.name as process_name,
               report.quantity,
               report.unit_price,
               report.total_price,
               sum(report.total_price) over (partition by report.work_date) as date_total_price
        from work_reports report
        inner join admin_accounts account on account.id = report.account_id
        inner join processes process on process.id = report.process_id
        {where_clause}
        order by report.work_date desc, report.created_at desc, report.id desc
        limit :__limit offset :__offset
    """
    rows_result = await session.execute(
        text(rows_sql),
        {**params, "__limit": page_size, "__offset": offset},
    )
    rows = [
        {
            "id": row.id,
            "accountId": row.account_id,
            "accountLogin": row.account_login,
            "accountName": row.account_name,
            "workDate": row.work_date.isoformat(),
            "processId": row.process_id,
            "processName": row.process_name,
            "quantity": float(row.quantity),
            "unitPrice": float(row.unit_price),
            "totalPrice": float(row.total_price),
            "dateTotalPrice": float(row.date_total_price or 0),
            "confirmStatus": "未确认",
        }
        for row in rows_result.fetchall()
    ]

    return {
        "rows": rows,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "summary": summary,
    }


async def query_monthly_work_report_details(
    session: AsyncSession,
    current_user: dict[str, object],
    account_id: str,
    month: str,
) -> dict[str, object]:
    """查询指定员工某月全部报工明细，供 Word 导出使用。"""
    month = _validate_month(month)
    if not month:
        raise HTTPException(status_code=400, detail="invalid month")

    await _assert_can_read_account(session, current_user, account_id)

    account_result = await session.execute(
        text(
            """
            select account.id,
                   account.account,
                   account.name
            from admin_accounts account
            where account.id = :account_id
            limit 1
            """
        ),
        {"account_id": account_id},
    )
    account_row = account_result.first()
    if not account_row:
        raise HTTPException(status_code=404, detail="account not found")

    params = {"account_id": account_id, "month": month}
    summary_row = (
        await session.execute(
            text(
                """
                select coalesce(sum(report.total_price), 0) as total_wage,
                       coalesce(sum(report.quantity), 0) as total_quantity,
                       count(distinct report.work_date) as work_days,
                       count(*) as total_rows
                from work_reports report
                where report.account_id = :account_id
                  and to_char(report.work_date, 'YYYY-MM') = :month
                """
            ),
            params,
        )
    ).first()
    summary = {
        "totalWage": float(summary_row.total_wage or 0) if summary_row else 0.0,
        "totalQuantity": float(summary_row.total_quantity or 0) if summary_row else 0.0,
        "workDays": int(summary_row.work_days or 0) if summary_row else 0,
    }

    rows_result = await session.execute(
        text(
            """
            select report.id,
                   report.work_date,
                   report.process_id,
                   process.name as process_name,
                   report.quantity,
                   report.unit_price,
                   report.total_price,
                   sum(report.total_price) over (partition by report.work_date) as date_total_price
            from work_reports report
            inner join processes process on process.id = report.process_id
            where report.account_id = :account_id
              and to_char(report.work_date, 'YYYY-MM') = :month
            order by report.work_date desc, report.created_at desc, report.id desc
            """
        ),
        params,
    )
    rows = [
        {
            "id": row.id,
            "workDate": row.work_date.isoformat(),
            "processId": row.process_id,
            "processName": row.process_name,
            "quantity": float(row.quantity),
            "unitPrice": float(row.unit_price),
            "totalPrice": float(row.total_price),
            "dateTotalPrice": float(row.date_total_price or 0),
            "confirmStatus": "未确认",
        }
        for row in rows_result.fetchall()
    ]

    return {
        "account": {
            "id": account_row.id,
            "account": account_row.account,
            "name": account_row.name,
        },
        "month": month,
        "rows": rows,
        "summary": summary,
    }


async def list_work_report_history(
    account_id: str,
    session: AsyncSession,
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


async def save_work_report(
    account_id: str,
    payload,
    session: AsyncSession,
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
                "total_price": calculate_total_price(unit_price, quantity),
            },
        )

    await session.commit()
    return await get_work_report(account_id, payload.work_date, session)


async def void_work_reports(account_id: str, work_date: str, session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            delete from work_reports
            where account_id = :account_id and work_date = to_date(:work_date, 'YYYY-MM-DD')
            """
        ),
        {"account_id": account_id, "work_date": work_date},
    )
    await session.commit()
