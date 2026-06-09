import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import engine
from app.main import create_app
from app.services.auth import hash_password
from app.services.login_rate_limit import clear_all_failures


TEST_SUPER_ID = "u-test-hardening-super"
TEST_EMPLOYEE_ID = "u-test-hardening-employee"
TEST_SUPER_ACCOUNT = "hardening_test_admin"
TEST_EMPLOYEE_ACCOUNT = "hardening_test_employee"
TEST_PASSWORD = "hardening-test-password"


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
                  (:super_id, :super_account, :password, 'super_admin', 'Hardening Test Admin', 'active', null),
                  (:employee_id, :employee_account, :password, 'employee', 'Hardening Test Employee', 'active', :super_id)
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


def _login_payload(account: str = TEST_SUPER_ACCOUNT, password: str = "wrong") -> dict[str, str]:
    return {"account": account, "password": password}


def test_production_docs_disabled(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    production_app = create_app()
    try:
        with TestClient(production_app) as client:
            assert client.get("/docs").status_code == 404
            assert client.get("/redoc").status_code == 404
            assert client.get("/openapi.json").status_code == 404
    finally:
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()


def test_production_health_db_requires_admin(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    production_app = create_app()
    asyncio.run(prepare_test_accounts())
    try:
        with TestClient(production_app) as client:
            assert client.get("/health/db").status_code == 404

            login = client.post(
                "/api/auth/login",
                json={"account": TEST_SUPER_ACCOUNT, "password": TEST_PASSWORD},
            )
            assert login.status_code == 200
            assert client.get("/health/db").status_code == 200
    finally:
        clear_all_failures()
        asyncio.run(delete_test_accounts())
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()


def test_login_rate_limit_locks_after_max_failures() -> None:
    asyncio.run(prepare_test_accounts())
    clear_all_failures()
    try:
        with TestClient(create_app()) as client:
            for _ in range(5):
                response = client.post("/api/auth/login", json=_login_payload())
                assert response.status_code == 401

            locked = client.post("/api/auth/login", json=_login_payload())
            assert locked.status_code == 429
            assert locked.json()["detail"] == "登录尝试过多，请稍后再试"

            legacy_locked = client.post("/api/login", json=_login_payload())
            assert legacy_locked.status_code == 429
    finally:
        clear_all_failures()
        asyncio.run(delete_test_accounts())


def test_login_success_clears_failure_count() -> None:
    asyncio.run(prepare_test_accounts())
    clear_all_failures()
    try:
        with TestClient(create_app()) as client:
            for _ in range(4):
                response = client.post("/api/auth/login", json=_login_payload())
                assert response.status_code == 401

            success = client.post(
                "/api/auth/login",
                json={"account": TEST_SUPER_ACCOUNT, "password": TEST_PASSWORD},
            )
            assert success.status_code == 200

            for _ in range(4):
                response = client.post("/api/auth/login", json=_login_payload())
                assert response.status_code == 401

            still_allowed = client.post("/api/auth/login", json=_login_payload())
            assert still_allowed.status_code == 401
    finally:
        clear_all_failures()
        asyncio.run(delete_test_accounts())
