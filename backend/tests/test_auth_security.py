import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.db.session import engine
from app.services.auth import hash_password


SENSITIVE_FIELDS = {"password", "passwordHash", "salt", "token"}
TEST_SUPER_ID = "u-test-auth-super"
TEST_EMPLOYEE_ID = "u-test-auth-employee"
TEST_SUPER_ACCOUNT = "auth_test_admin"
TEST_EMPLOYEE_ACCOUNT = "auth_test_employee"
TEST_PASSWORD = "auth-test-password"


async def delete_test_accounts() -> None:
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                delete from auth_sessions
                where account_id in (
                    select id from admin_accounts
                    where id in (:super_id, :employee_id)
                       or account in (:super_account, :employee_account)
                )
                """
            ),
            {
                "super_id": TEST_SUPER_ID,
                "employee_id": TEST_EMPLOYEE_ID,
                "super_account": TEST_SUPER_ACCOUNT,
                "employee_account": TEST_EMPLOYEE_ACCOUNT,
            },
        )
        await connection.execute(
            text(
                """
                delete from admin_accounts
                where id in (:super_id, :employee_id)
                   or account in (:super_account, :employee_account)
                """
            ),
            {
                "super_id": TEST_SUPER_ID,
                "employee_id": TEST_EMPLOYEE_ID,
                "super_account": TEST_SUPER_ACCOUNT,
                "employee_account": TEST_EMPLOYEE_ACCOUNT,
            },
        )
    await engine.dispose()


async def prepare_test_accounts() -> None:
    await delete_test_accounts()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                insert into admin_accounts (id, account, password, role, name, status, manager_id)
                values
                  (:super_id, :super_account, :password, 'super_admin', 'Auth Test Admin', 'active', null),
                  (:employee_id, :employee_account, :password, 'employee', 'Auth Test Employee', 'active', :super_id)
                """
            ),
            {
                "super_id": TEST_SUPER_ID,
                "employee_id": TEST_EMPLOYEE_ID,
                "super_account": TEST_SUPER_ACCOUNT,
                "employee_account": TEST_EMPLOYEE_ACCOUNT,
                "password": hash_password(TEST_PASSWORD),
            },
        )
    await engine.dispose()


def test_auth_security_flow() -> None:
    asyncio.run(prepare_test_accounts())
    try:
        with TestClient(app) as client:
            assert client.get("/api/me").status_code == 401
            assert client.get("/api/admin/accounts").status_code == 401

            failed = client.post("/api/auth/login", json={"account": TEST_SUPER_ACCOUNT, "password": "wrong"})
            assert failed.status_code == 401
            assert failed.json()["detail"] == "invalid account or password"

            login = client.post("/api/auth/login", json={"account": TEST_SUPER_ACCOUNT, "password": TEST_PASSWORD})
            assert login.status_code == 200
            assert "httponly" in login.headers["set-cookie"].lower()
            assert not (SENSITIVE_FIELDS & set(login.json()))

            me = client.get("/api/me")
            assert me.status_code == 200
            assert not (SENSITIVE_FIELDS & set(me.json()))

            accounts = client.get("/api/admin/accounts")
            assert accounts.status_code == 200
            assert accounts.json()
            assert all(not (SENSITIVE_FIELDS & set(account)) for account in accounts.json())

            logout = client.post("/api/auth/logout")
            assert logout.status_code == 200
            assert client.get("/api/me").status_code == 401

            employee_login = client.post("/api/auth/login", json={"account": TEST_EMPLOYEE_ACCOUNT, "password": TEST_PASSWORD})
            assert employee_login.status_code == 200
            employee = client.get("/api/me").json()

            forbidden = client.get(f"/api/work-report-history/{TEST_SUPER_ID}")
            assert forbidden.status_code == 403

            own = client.get(f"/api/work-report-history/{employee['id']}")
            assert own.status_code == 200

            assert client.post("/api/auth/logout").status_code == 200
    finally:
        asyncio.run(delete_test_accounts())
