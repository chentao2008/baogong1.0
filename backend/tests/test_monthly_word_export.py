"""测试月度 Word 导出接口权限与内容。"""

import asyncio
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from app.main import app
from app.services.auth import hash_password


TEST_PASSWORD = "export-test-password"
TEST_IDS = {
    "super": "u-test-export-super",
    "admin_a": "u-test-export-admin-a",
    "admin_b": "u-test-export-admin-b",
    "employee_a": "u-test-export-employee-a",
    "employee_b": "u-test-export-employee-b",
}
TEST_ACCOUNTS = {
    "super": "export_test_super",
    "admin_a": "export_test_admin_a",
    "admin_b": "export_test_admin_b",
    "employee_a": "export_test_employee_a",
    "employee_b": "export_test_employee_b",
}
TEST_PROCESS_IDS = {
    "proc_a1": "p-test-export-a1",
    "proc_b1": "p-test-export-b1",
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
                    "name": f"测试{TEST_ACCOUNTS[key]}",
                    "manager_id": manager_id,
                },
            )

        for pid, name, manager in [
            (TEST_PROCESS_IDS["proc_a1"], "导出工序A", TEST_IDS["admin_a"]),
            (TEST_PROCESS_IDS["proc_b1"], "导出工序B", TEST_IDS["admin_b"]),
        ]:
            await connection.execute(
                text(
                    """
                    insert into processes (id, name, price, unit, status, manager_id)
                    values (:id, :name, 10, '元/个', 'active', :manager_id)
                    """
                ),
                {"id": pid, "name": name, "manager_id": manager},
            )

        await connection.execute(
            text(
                """
                insert into account_processes (account_id, process_id)
                values (:account_id, :process_id)
                """
            ),
            {"account_id": TEST_IDS["employee_a"], "process_id": TEST_PROCESS_IDS["proc_a1"]},
        )
        await connection.execute(
            text(
                """
                insert into account_processes (account_id, process_id)
                values (:account_id, :process_id)
                """
            ),
            {"account_id": TEST_IDS["employee_b"], "process_id": TEST_PROCESS_IDS["proc_b1"]},
        )

        await connection.execute(
            text(
                """
                insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                values
                    ('wr-test-export-a1', :acc, to_date('2024-01-05', 'YYYY-MM-DD'), :pid, 2, 10, 20),
                    ('wr-test-export-a2', :acc, to_date('2024-01-06', 'YYYY-MM-DD'), :pid, 1, 10, 10)
                """
            ),
            {"acc": TEST_IDS["employee_a"], "pid": TEST_PROCESS_IDS["proc_a1"]},
        )
        await connection.execute(
            text(
                """
                insert into work_reports (id, account_id, work_date, process_id, quantity, unit_price, total_price)
                values ('wr-test-export-b1', :acc, to_date('2024-02-01', 'YYYY-MM-DD'), :pid, 3, 10, 30)
                """
            ),
            {"acc": TEST_IDS["employee_b"], "pid": TEST_PROCESS_IDS["proc_b1"]},
        )
    await engine.dispose()


def login(client: TestClient, account: str) -> None:
    response = client.post("/api/auth/login", json={"account": account, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def read_docx_text(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    document = Document(BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs) + "\n" + xml


def test_monthly_export_permissions_and_content() -> None:
    asyncio.run(seed())
    try:
        with TestClient(app) as client:
            login(client, TEST_ACCOUNTS["employee_a"])
            own = client.get("/api/employee/work-reports/monthly-export?month=2024-01")
            assert own.status_code == 200
            assert own.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            assert "attachment" in own.headers.get("content-disposition", "")
            own_text = read_docx_text(own.content)
            assert "员工月度报工详情" in own_text
            assert TEST_ACCOUNTS["employee_a"] in own_text
            assert "2024-01" in own_text
            assert "导出工序A" in own_text

            admin_forbidden = client.get("/api/admin/work-reports/monthly-export?account_id=x&month=2024-01")
            assert admin_forbidden.status_code == 403
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["admin_a"])
            admin_ok = client.get(
                f"/api/admin/work-reports/monthly-export?account_id={TEST_IDS['employee_a']}&month=2024-01"
            )
            assert admin_ok.status_code == 200
            admin_forbidden = client.get(
                f"/api/admin/work-reports/monthly-export?account_id={TEST_IDS['employee_b']}&month=2024-02"
            )
            assert admin_forbidden.status_code == 403
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["super"])
            super_ok = client.get(
                f"/api/admin/work-reports/monthly-export?account_id={TEST_IDS['employee_b']}&month=2024-02"
            )
            assert super_ok.status_code == 200
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["employee_b"])
            invalid_month = client.get("/api/employee/work-reports/monthly-export?month=2024-13")
            assert invalid_month.status_code == 400
    finally:
        asyncio.run(cleanup())
