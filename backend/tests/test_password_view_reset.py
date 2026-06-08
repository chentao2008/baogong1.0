import asyncio
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.db.session import engine
from app.main import app
from app.services.auth import hash_password, is_password_hash


TEST_PASSWORD = "password-view-old"
RESET_PASSWORD = "password-view-new"
TEST_IDS = {
    "super": "u-test-password-view-super",
    "admin_a": "u-test-password-view-admin-a",
    "admin_b": "u-test-password-view-admin-b",
    "employee_a": "u-test-password-view-employee-a",
    "employee_b": "u-test-password-view-employee-b",
}
TEST_ACCOUNTS = {
    "super": "password_view_super",
    "admin_a": "password_view_admin_a",
    "admin_b": "password_view_admin_b",
    "employee_a": "password_view_employee_a",
    "employee_b": "password_view_employee_b",
}
SENSITIVE_FIELDS = {"password", "passwordHash", "salt", "token", "password_view_ciphertext"}


def set_password_view_secret(value: str | None) -> None:
    if value is None:
        os.environ["PASSWORD_VIEW_SECRET"] = ""
    else:
        os.environ["PASSWORD_VIEW_SECRET"] = value
    get_settings.cache_clear()


async def delete_test_data() -> None:
    await engine.dispose()
    await initialize_database()
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                delete from audit_logs
                where actor_id = any(:ids)
                   or target_id = any(:ids)
                """
            ),
            {"ids": list(TEST_IDS.values())},
        )
        await connection.execute(
            text(
                """
                delete from auth_sessions
                where account_id in (
                    select id from admin_accounts
                    where id = any(:ids)
                       or account = any(:accounts)
                )
                """
            ),
            {"ids": list(TEST_IDS.values()), "accounts": list(TEST_ACCOUNTS.values())},
        )
        await connection.execute(
            text(
                """
                delete from admin_accounts
                where id = any(:ids)
                   or account = any(:accounts)
                """
            ),
            {"ids": list(TEST_IDS.values()), "accounts": list(TEST_ACCOUNTS.values())},
        )
    await engine.dispose()


async def prepare_test_data() -> None:
    await delete_test_data()
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
    await engine.dispose()


def login(client: TestClient, account_key: str, password: str = TEST_PASSWORD) -> None:
    response = client.post("/api/auth/login", json={"account": TEST_ACCOUNTS[account_key], "password": password})
    assert response.status_code == 200


async def fetch_account(account_id: str):
    await engine.dispose()
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                select password, password_view_ciphertext, password_view_updated_at
                from admin_accounts
                where id = :id
                """
            ),
            {"id": account_id},
        )
        row = result.first()
    await engine.dispose()
    return row


async def fetch_audit_logs(action: str) -> list:
    await engine.dispose()
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                select action, actor_id, target_id, payload_json
                from audit_logs
                where action = :action
                  and (actor_id = any(:ids) or target_id = any(:ids))
                order by created_at, target_id
                """
            ),
            {"action": action, "ids": list(TEST_IDS.values())},
        )
        rows = result.fetchall()
    await engine.dispose()
    return rows


def test_super_admin_sees_reset_required_for_old_bcrypt_passwords() -> None:
    set_password_view_secret("test-password-view-secret")
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login(client, "super")
            response = client.get("/api/admin/accounts")

            assert response.status_code == 200
            account = {item["id"]: item for item in response.json()}[TEST_IDS["employee_a"]]
            assert account["passwordDisplay"] == "需重置后可查看"
            assert not (SENSITIVE_FIELDS & set(account))
    finally:
        asyncio.run(delete_test_data())


def test_reset_password_stores_bcrypt_and_encrypted_view_copy_and_allows_login() -> None:
    set_password_view_secret("test-password-view-secret")
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login(client, "super")
            reset = client.post(
                f"/api/admin/accounts/{TEST_IDS['employee_a']}/reset-password",
                json={"password": RESET_PASSWORD},
            )

            assert reset.status_code == 200
            assert reset.json()["passwordDisplay"] == RESET_PASSWORD
            assert not (SENSITIVE_FIELDS & set(reset.json()))

            listed = client.get("/api/admin/accounts")
            assert listed.status_code == 200
            listed_account = {item["id"]: item for item in listed.json()}[TEST_IDS["employee_a"]]
            assert listed_account["passwordDisplay"] == RESET_PASSWORD

            logout = client.post("/api/auth/logout")
            assert logout.status_code == 200
            login(client, "employee_a", RESET_PASSWORD)

        row = asyncio.run(fetch_account(TEST_IDS["employee_a"]))
        assert is_password_hash(row.password)
        assert row.password_view_ciphertext
        assert row.password_view_ciphertext != RESET_PASSWORD
        assert row.password_view_updated_at is not None

        reset_logs = asyncio.run(fetch_audit_logs("password_reset"))
        assert len(reset_logs) == 1
        assert reset_logs[0].actor_id == TEST_IDS["super"]
        assert reset_logs[0].target_id == TEST_IDS["employee_a"]
        assert RESET_PASSWORD not in str(reset_logs[0].payload_json)

        view_logs = asyncio.run(fetch_audit_logs("password_view_list"))
        assert len(view_logs) >= 1
        assert any(row.target_id == TEST_IDS["employee_a"] for row in view_logs)
        assert all(RESET_PASSWORD not in str(row.payload_json) for row in view_logs)
    finally:
        asyncio.run(delete_test_data())


def test_password_reset_permissions_and_password_display_visibility() -> None:
    set_password_view_secret("test-password-view-secret")
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login(client, "admin_a")
            own_employee = client.post(
                f"/api/admin/accounts/{TEST_IDS['employee_a']}/reset-password",
                json={"password": RESET_PASSWORD},
            )
            assert own_employee.status_code == 200
            assert "passwordDisplay" not in own_employee.json()

            cross_employee = client.post(
                f"/api/admin/accounts/{TEST_IDS['employee_b']}/reset-password",
                json={"password": RESET_PASSWORD},
            )
            assert cross_employee.status_code == 403

            accounts = client.get("/api/admin/accounts")
            assert accounts.status_code == 200
            assert all("passwordDisplay" not in account for account in accounts.json())

            assert client.post("/api/auth/logout").status_code == 200
            login(client, "employee_a", RESET_PASSWORD)
            forbidden = client.post(
                f"/api/admin/accounts/{TEST_IDS['employee_b']}/reset-password",
                json={"password": RESET_PASSWORD},
            )
            assert forbidden.status_code == 403
    finally:
        asyncio.run(delete_test_data())


def test_missing_password_view_secret_never_saves_or_returns_viewable_password() -> None:
    set_password_view_secret(None)
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login(client, "super")
            reset = client.post(
                f"/api/admin/accounts/{TEST_IDS['employee_a']}/reset-password",
                json={"password": RESET_PASSWORD},
            )
            assert reset.status_code == 200
            assert reset.json()["passwordDisplay"] == "密码查看功能未配置"

            listed = client.get("/api/admin/accounts")
            assert listed.status_code == 200
            account = {item["id"]: item for item in listed.json()}[TEST_IDS["employee_a"]]
            assert account["passwordDisplay"] == "密码查看功能未配置"

        row = asyncio.run(fetch_account(TEST_IDS["employee_a"]))
        assert is_password_hash(row.password)
        assert row.password_view_ciphertext is None
        assert row.password_view_updated_at is None
    finally:
        asyncio.run(delete_test_data())
        set_password_view_secret("test-password-view-secret")
