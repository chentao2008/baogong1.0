"""测试新的服务端查询接口 /api/work-reports/query 及唯一约束。"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from app.main import app
from app.services.auth import hash_password


TEST_PASSWORD = "query-test-password"
TEST_IDS = {
    "super": "u-test-query-super",
    "admin_a": "u-test-query-admin-a",
    "admin_b": "u-test-query-admin-b",
    "employee_a": "u-test-query-employee-a",
    "employee_b": "u-test-query-employee-b",
}
TEST_ACCOUNTS = {
    "super": "query_test_super",
    "admin_a": "query_test_admin_a",
    "admin_b": "query_test_admin_b",
    "employee_a": "query_test_employee_a",
    "employee_b": "query_test_employee_b",
}
TEST_PROCESS_IDS = {
    "proc_a1": "p-test-query-a1",
    "proc_a2": "p-test-query-a2",
    "proc_b1": "p-test-query-b1",
}
ALL_ACCOUNT_IDS = list(TEST_IDS.values())
ALL_PROCESS_IDS = list(TEST_PROCESS_IDS.values())


async def cleanup() -> None:
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text("delete from work_reports where account_id = any(:ids) or process_id = any(:pids)"),
            {"ids": ALL_ACCOUNT_IDS, "pids": ALL_PROCESS_IDS},
        )
        await connection.execute(
            text("delete from auth_sessions where account_id = any(:ids)"),
            {"ids": ALL_ACCOUNT_IDS},
        )
        await connection.execute(
            text("delete from account_processes where account_id = any(:ids) or process_id = any(:pids)"),
            {"ids": ALL_ACCOUNT_IDS, "pids": ALL_PROCESS_IDS},
        )
        await connection.execute(
            text("delete from admin_accounts where id = any(:ids)"),
            {"ids": ALL_ACCOUNT_IDS},
        )
        await connection.execute(
            text("delete from processes where id = any(:pids)"),
            {"pids": ALL_PROCESS_IDS},
        )
    await engine.dispose()


async def seed() -> None:
    await cleanup()
    async with engine.begin() as connection:
        for key, role, manager_id in [
            ("super", "super_admin", None),
            ("admin_a", "admin", None),
            ("admin_b", "admin", None),
            ("employee_a", "employee", TEST_IDS["admin_a"]),
            ("employee_b", "employee", TEST_IDS["admin_b"]),
        ]:
            await connection.execute(
                text(
                    """
                    insert into admin_accounts (id, account, password, role, name, status, manager_id)
                    values (:id, :account, :password, :role, :name, 'active', :manager_id)
                    """
                ),
                {
                    "id": TEST_IDS[key],
                    "account": TEST_ACCOUNTS[key],
                    "password": hash_password(TEST_PASSWORD),
                    "role": role,
                    "name": TEST_ACCOUNTS[key],
                    "manager_id": manager_id,
                },
            )

        for pid, name, manager_id in [
            (TEST_PROCESS_IDS["proc_a1"], "query_test_proc_a1", TEST_IDS["admin_a"]),
            (TEST_PROCESS_IDS["proc_a2"], "query_test_proc_a2", TEST_IDS["admin_a"]),
            (TEST_PROCESS_IDS["proc_b1"], "query_test_proc_b1", TEST_IDS["admin_b"]),
        ]:
            await connection.execute(
                text(
                    """
                    insert into processes (id, name, price, unit, status, manager_id)
                    values (:id, :name, :price, '元/个', 'active', :manager_id)
                    """
                ),
                {"id": pid, "name": name, "price": 10, "manager_id": manager_id},
            )

        # Employee A: 4 reports across 3 days, 2 processes.
        reports = [
            # (id, account_id, work_date, process_id, quantity, unit_price)
            ("wr-test-q-1", TEST_IDS["employee_a"], "2024-01-05", TEST_PROCESS_IDS["proc_a1"], 2, 10),
            ("wr-test-q-2", TEST_IDS["employee_a"], "2024-01-05", TEST_PROCESS_IDS["proc_a2"], 1, 10),
            ("wr-test-q-3", TEST_IDS["employee_a"], "2024-01-10", TEST_PROCESS_IDS["proc_a1"], 3, 10),
            ("wr-test-q-4", TEST_IDS["employee_a"], "2024-02-03", TEST_PROCESS_IDS["proc_a1"], 5, 10),
            # Employee B
            ("wr-test-q-5", TEST_IDS["employee_b"], "2024-01-05", TEST_PROCESS_IDS["proc_b1"], 4, 10),
        ]
        for rid, acc, wdate, pid, qty, unit_price in reports:
            await connection.execute(
                text(
                    """
                    insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                    values (:id, :account_id, to_date(:work_date, 'YYYY-MM-DD'), :pid, :qty, :unit_price, :total)
                    """
                ),
                {
                    "id": rid,
                    "account_id": acc,
                    "work_date": wdate,
                    "pid": pid,
                    "qty": qty,
                    "unit_price": unit_price,
                    "total": qty * unit_price,
                },
            )
    await engine.dispose()


def login(client: TestClient, account: str) -> None:
    response = client.post("/api/auth/login", json={"account": account, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def test_query_permission_and_filters() -> None:
    asyncio.run(seed())
    try:
        with TestClient(app) as client:
            # Employee A self
            login(client, TEST_ACCOUNTS["employee_a"])

            own = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}")
            assert own.status_code == 200
            data = own.json()
            assert data["total"] == 4
            assert data["summary"]["totalWage"] == 110.0
            assert data["summary"]["totalQuantity"] == 11.0
            assert data["summary"]["workDays"] == 3

            forbidden_other = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_b']}")
            assert forbidden_other.status_code == 403

            # Employee may not omit account_id
            forbidden_all = client.get("/api/work-reports/query")
            assert forbidden_all.status_code == 403

            # Month filter
            month_jan = client.get(
                f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}&month=2024-01"
            ).json()
            assert month_jan["total"] == 3
            assert month_jan["summary"]["workDays"] == 2

            # Start/end date boundary
            boundary = client.get(
                f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}"
                "&start_date=2024-01-05&end_date=2024-01-05"
            ).json()
            assert boundary["total"] == 2
            assert boundary["summary"]["workDays"] == 1

            # process_id filter
            by_process = client.get(
                f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}"
                f"&process_id={TEST_PROCESS_IDS['proc_a1']}"
            ).json()
            assert by_process["total"] == 3
            assert by_process["summary"]["totalQuantity"] == 10.0

            # Pagination
            page1 = client.get(
                f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}&page=1&page_size=2"
            ).json()
            page2 = client.get(
                f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}&page=2&page_size=2"
            ).json()
            assert page1["total"] == 4
            assert len(page1["rows"]) == 2
            assert len(page2["rows"]) == 2
            ids_page1 = {row["id"] for row in page1["rows"]}
            ids_page2 = {row["id"] for row in page2["rows"]}
            assert ids_page1.isdisjoint(ids_page2)

            assert client.post("/api/auth/logout").status_code == 200

            # Admin A: sees only own employee
            login(client, TEST_ACCOUNTS["admin_a"])
            admin_ok = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}")
            assert admin_ok.status_code == 200
            admin_forbidden = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_b']}")
            assert admin_forbidden.status_code == 403
            # Admin A scoped to test seed via date range: only seed dates exist in 2024-01..2024-02
            admin_all = client.get(
                "/api/work-reports/query?start_date=2024-01-01&end_date=2024-12-31"
            ).json()
            seen_ids = {row["accountId"] for row in admin_all["rows"]}
            assert seen_ids == {TEST_IDS["employee_a"]}
            assert admin_all["total"] == 4
            assert client.post("/api/auth/logout").status_code == 200

            # Admin B: cannot see employee A, only employee B's 1 row
            login(client, TEST_ACCOUNTS["admin_b"])
            admin_b_forbidden = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}")
            assert admin_b_forbidden.status_code == 403
            admin_b_all = client.get(
                "/api/work-reports/query?start_date=2024-01-01&end_date=2024-12-31"
            ).json()
            seen_ids_b = {row["accountId"] for row in admin_b_all["rows"]}
            assert seen_ids_b == {TEST_IDS["employee_b"]}
            assert admin_b_all["total"] == 1
            assert client.post("/api/auth/logout").status_code == 200

            # Super admin sees everyone (filter to seed window for deterministic count)
            login(client, TEST_ACCOUNTS["super"])
            super_all = client.get(
                "/api/work-reports/query?start_date=2024-01-01&end_date=2024-12-31"
            ).json()
            seen_ids_super = {row["accountId"] for row in super_all["rows"]}
            assert {TEST_IDS["employee_a"], TEST_IDS["employee_b"]} <= seen_ids_super
            assert super_all["total"] == 5
            super_a = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_a']}")
            assert super_a.status_code == 200
            super_b = client.get(f"/api/work-reports/query?account_id={TEST_IDS['employee_b']}")
            assert super_b.status_code == 200
    finally:
        asyncio.run(cleanup())


async def _check_constraint_and_try_duplicate() -> tuple[bool, bool]:
    """Returns (has_preexisting_duplicates, duplicate_was_rejected)."""
    await engine.dispose()
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                select 1 from work_reports
                group by account_id, work_date, process_id
                having count(*) > 1
                limit 1
                """
            )
        )
        has_dupes = result.first() is not None

    if has_dupes:
        return True, False

    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                values ('wr-test-q-dup-1', :acc, to_date('2024-03-01', 'YYYY-MM-DD'), :pid, 1, 10, 10)
                """
            ),
            {"acc": TEST_IDS["employee_a"], "pid": TEST_PROCESS_IDS["proc_a1"]},
        )

    rejected = False
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                    values ('wr-test-q-dup-2', :acc, to_date('2024-03-01', 'YYYY-MM-DD'), :pid, 2, 10, 20)
                    """
                ),
                {"acc": TEST_IDS["employee_a"], "pid": TEST_PROCESS_IDS["proc_a1"]},
            )
    except IntegrityError:
        rejected = True
    return False, rejected


def test_unique_constraint_blocks_duplicate_reports() -> None:
    asyncio.run(seed())
    try:
        # Ensure init_db has run by invoking the app context once.
        with TestClient(app):
            pass
        has_dupes, rejected = asyncio.run(_check_constraint_and_try_duplicate())
        if has_dupes:
            pytest.skip(
                "work_reports contains pre-existing duplicates; unique constraint cannot be installed "
                "automatically. Run scripts/detect_duplicate_reports.py and merge manually."
            )
        assert rejected, "duplicate (account_id, work_date, process_id) was not rejected by DB"
    finally:
        asyncio.run(cleanup())
