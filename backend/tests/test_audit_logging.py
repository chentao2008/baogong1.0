import asyncio
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from app.db.init_db import initialize_database
from app.main import app
from app.core.config import get_settings
from app.services.auth import hash_password
from app.services.password_view import encrypt_viewable_password


TEST_PASSWORD = "audit-test-password"
TEST_SUPER_ID = "u-test-audit-super"
TEST_EMPLOYEE_IDS = ["u-test-audit-employee-a", "u-test-audit-employee-b"]
TEST_SUPER_ACCOUNT = "audit_test_super"
TEST_EMPLOYEE_ACCOUNTS = ["audit_test_employee_a", "audit_test_employee_b"]


async def delete_test_data() -> None:
    await engine.dispose()
    await initialize_database()
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                delete from audit_logs
                where actor_id = :super_id
                   or target_id = any(:employee_ids)
                """
            ),
            {"super_id": TEST_SUPER_ID, "employee_ids": TEST_EMPLOYEE_IDS},
        )
        await connection.execute(
            text(
                """
                delete from auth_sessions
                where account_id in (
                    select id from admin_accounts
                    where id = :super_id
                       or id = any(:employee_ids)
                       or account = :super_account
                       or account = any(:employee_accounts)
                )
                """
            ),
            {
                "super_id": TEST_SUPER_ID,
                "employee_ids": TEST_EMPLOYEE_IDS,
                "super_account": TEST_SUPER_ACCOUNT,
                "employee_accounts": TEST_EMPLOYEE_ACCOUNTS,
            },
        )
        await connection.execute(
            text(
                """
                delete from admin_accounts
                where id = :super_id
                   or id = any(:employee_ids)
                   or account = :super_account
                   or account = any(:employee_accounts)
                """
            ),
            {
                "super_id": TEST_SUPER_ID,
                "employee_ids": TEST_EMPLOYEE_IDS,
                "super_account": TEST_SUPER_ACCOUNT,
                "employee_accounts": TEST_EMPLOYEE_ACCOUNTS,
            },
        )
    await engine.dispose()


async def prepare_test_data() -> None:
    os.environ["PASSWORD_VIEW_SECRET"] = "test-audit-password-view-secret"
    get_settings.cache_clear()
    await delete_test_data()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                insert into admin_accounts (id, account, password, role, name, status, manager_id)
                values (:id, :account, :password, 'super_admin', 'Audit Test Super', 'active', null)
                """
            ),
            {
                "id": TEST_SUPER_ID,
                "account": TEST_SUPER_ACCOUNT,
                "password": hash_password(TEST_PASSWORD),
            },
        )
        for account_id, account in zip(TEST_EMPLOYEE_IDS, TEST_EMPLOYEE_ACCOUNTS, strict=True):
            await connection.execute(
                text(
                    """
                    insert into admin_accounts (
                        id, account, password, role, name, status, manager_id,
                        password_view_ciphertext, password_view_updated_at
                    )
                    values (
                        :id, :account, :password, 'employee', :name, 'active', :manager_id,
                        :password_view_ciphertext, now()
                    )
                    """
                ),
                {
                    "id": account_id,
                    "account": account,
                    "password": hash_password(TEST_PASSWORD),
                    "name": account,
                    "manager_id": TEST_SUPER_ID,
                    "password_view_ciphertext": encrypt_viewable_password(TEST_PASSWORD),
                },
            )
    await engine.dispose()


async def fetch_audit_rows() -> list:
    await engine.dispose()
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                select id, actor_id, action, target_id, payload_json
                from audit_logs
                where actor_id = :actor_id
                  and action = 'password_view_list'
                  and target_id = any(:target_ids)
                order by target_id
                """
            ),
            {"actor_id": TEST_SUPER_ID, "target_ids": TEST_EMPLOYEE_IDS},
        )
        rows = result.fetchall()
    await engine.dispose()
    return rows


def test_audit_log_id_generation_is_unique() -> None:
    from app.services.audit import generate_audit_id

    ids = [generate_audit_id() for _ in range(100)]

    assert len(ids) == len(set(ids))
    assert all(audit_id.startswith("audit-") for audit_id in ids)


def test_super_admin_password_list_view_writes_distinct_safe_audit_logs() -> None:
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login = client.post("/api/auth/login", json={"account": TEST_SUPER_ACCOUNT, "password": TEST_PASSWORD})
            assert login.status_code == 200

            response = client.get("/api/admin/accounts")

            assert response.status_code == 200
            returned_accounts = {account["id"]: account for account in response.json()}
            assert returned_accounts[TEST_EMPLOYEE_IDS[0]]["passwordDisplay"] == TEST_PASSWORD
            assert returned_accounts[TEST_EMPLOYEE_IDS[1]]["passwordDisplay"] == TEST_PASSWORD

        rows = asyncio.run(fetch_audit_rows())
        assert len(rows) == 2
        assert len({row.id for row in rows}) == 2
        assert {row.target_id for row in rows} == set(TEST_EMPLOYEE_IDS)
        for row in rows:
            payload = row.payload_json
            assert payload["whether_password_was_viewable"] is True
            assert payload["target_account"] in TEST_EMPLOYEE_ACCOUNTS
            assert "password" not in payload
            assert "passwordDisplay" not in payload
            assert TEST_PASSWORD not in str(payload)
    finally:
        asyncio.run(delete_test_data())
