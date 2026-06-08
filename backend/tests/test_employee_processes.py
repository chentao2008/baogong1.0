import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from app.main import app
from app.services.auth import hash_password


TEST_PASSWORD = "employee-process-test-password"
TEST_ADMIN_ID = "u-test-employee-process-admin"
TEST_EMPLOYEE_ID = "u-test-employee-process-employee"
TEST_PROCESS_ID = "p-test-employee-process"


async def delete_test_data() -> None:
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                delete from auth_sessions
                where account_id in (:admin_id, :employee_id)
                """
            ),
            {"admin_id": TEST_ADMIN_ID, "employee_id": TEST_EMPLOYEE_ID},
        )
        await connection.execute(
            text("delete from account_processes where account_id = :employee_id or process_id = :process_id"),
            {"employee_id": TEST_EMPLOYEE_ID, "process_id": TEST_PROCESS_ID},
        )
        await connection.execute(
            text("delete from admin_accounts where id in (:admin_id, :employee_id)"),
            {"admin_id": TEST_ADMIN_ID, "employee_id": TEST_EMPLOYEE_ID},
        )
        await connection.execute(text("delete from processes where id = :process_id"), {"process_id": TEST_PROCESS_ID})
    await engine.dispose()


async def prepare_test_data() -> None:
    await delete_test_data()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                insert into admin_accounts (id, account, password, role, name, status, manager_id)
                values
                  (:admin_id, 'employee_process_admin', :password, 'admin', 'Employee Process Admin', 'active', null),
                  (:employee_id, 'employee_process_employee', :password, 'employee', 'Employee Process Employee', 'active', :admin_id)
                """
            ),
            {
                "admin_id": TEST_ADMIN_ID,
                "employee_id": TEST_EMPLOYEE_ID,
                "password": hash_password(TEST_PASSWORD),
            },
        )
        await connection.execute(
            text(
                """
                insert into processes (id, name, price, unit, status, manager_id)
                values (:process_id, 'employee_process_test', 1, '元/个', 'active', :admin_id)
                """
            ),
            {"process_id": TEST_PROCESS_ID, "admin_id": TEST_ADMIN_ID},
        )
        await connection.execute(
            text(
                """
                insert into account_processes (account_id, process_id)
                values (:employee_id, :process_id)
                """
            ),
            {"employee_id": TEST_EMPLOYEE_ID, "process_id": TEST_PROCESS_ID},
        )
    await engine.dispose()


def test_employee_process_list_returns_configured_processes() -> None:
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={"account": "employee_process_employee", "password": TEST_PASSWORD},
            )
            assert login.status_code == 200

            response = client.get(f"/api/accounts/{TEST_EMPLOYEE_ID}/processes")

            assert response.status_code == 200
            assert response.json() == [
                {
                    "id": TEST_PROCESS_ID,
                    "name": "employee_process_test",
                    "price": 1.0,
                    "unit": "元/个",
                    "status": "active",
                    "managerId": TEST_ADMIN_ID,
                }
            ]
    finally:
        asyncio.run(delete_test_data())
