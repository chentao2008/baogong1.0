"""检测 work_reports 中同一员工同一天同一工序的重复记录。

加唯一约束前必须先确认没有重复数据；如果发现重复，请人工合并后再启用约束，
不要直接删除用户数据。
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


async def main() -> int:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                select account_id,
                       work_date,
                       process_id,
                       count(*) as duplicate_count,
                       sum(quantity) as total_quantity,
                       sum(total_price) as total_price,
                       array_agg(id order by created_at) as report_ids
                from work_reports
                group by account_id, work_date, process_id
                having count(*) > 1
                order by work_date desc, account_id, process_id
                """
            )
        )
        rows = result.fetchall()

    if not rows:
        print("no duplicate work_reports rows found.")
        return 0

    print(f"found {len(rows)} duplicate (account_id, work_date, process_id) groups:")
    for row in rows:
        print(
            f"  account_id={row.account_id} "
            f"work_date={row.work_date.isoformat()} "
            f"process_id={row.process_id} "
            f"count={int(row.duplicate_count)} "
            f"total_quantity={row.total_quantity} "
            f"total_price={row.total_price} "
            f"report_ids={list(row.report_ids)}"
        )
    print(
        "\nplease confirm a merge strategy with the data owner before deleting any row; "
        "do not delete user data automatically."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
