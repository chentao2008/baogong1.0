import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from app.main import app
from app.services.auth import hash_password


TEST_PASSWORD = "ownership-test-password"
TEST_IDS = {
    "super": "u-test-owner-super",
    "admin_a": "u-test-owner-admin-a",
    "admin_b": "u-test-owner-admin-b",
}
TEST_ACCOUNTS = {
    "super": "owner_test_super",
    "admin_a": "owner_test_admin_a",
    "admin_b": "owner_test_admin_b",
}


async def delete_test_data() -> None:
    await engine.dispose()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                delete from auth_sessions
                where account_id in (
                    select id from admin_accounts
                    where account like 'owner_test_%'
                       or id in ('u-test-owner-super', 'u-test-owner-admin-a', 'u-test-owner-admin-b')
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                delete from account_processes
                where account_id in (select id from admin_accounts where account like 'owner_test_%')
                   or process_id in (select id from processes where name like 'owner_test_%')
                """
            )
        )
        await connection.execute(text("delete from admin_accounts where account like 'owner_test_%' or id in ('u-test-owner-super', 'u-test-owner-admin-a', 'u-test-owner-admin-b')"))
        await connection.execute(text("delete from processes where name like 'owner_test_%'"))
    await engine.dispose()


async def prepare_test_data() -> None:
    await delete_test_data()
    async with engine.begin() as connection:
        for key, role in [("super", "super_admin"), ("admin_a", "admin"), ("admin_b", "admin")]:
            await connection.execute(
                text(
                    """
                    insert into admin_accounts (id, account, password, role, name, status, manager_id)
                    values (:id, :account, :password, :role, :name, 'active', null)
                    """
                ),
                {
                    "id": TEST_IDS[key],
                    "account": TEST_ACCOUNTS[key],
                    "password": hash_password(TEST_PASSWORD),
                    "role": role,
                    "name": TEST_ACCOUNTS[key],
                },
            )
    await engine.dispose()


def login(client: TestClient, account: str) -> None:
    response = client.post("/api/auth/login", json={"account": account, "password": TEST_PASSWORD})
    assert response.status_code == 200


def test_admin_owned_accounts_and_processes_are_isolated() -> None:
    asyncio.run(prepare_test_data())
    try:
        with TestClient(app) as client:
            login(client, TEST_ACCOUNTS["super"])
            forbidden_account = client.post(
                "/api/admin/accounts",
                json={"account": "owner_test_super_created", "password": TEST_PASSWORD, "role": "employee", "process_ids": []},
            )
            assert forbidden_account.status_code == 403
            forbidden_process = client.post(
                "/api/admin/processes",
                json={"name": "owner_test_super_process", "price": 1, "unit": "元/个"},
            )
            assert forbidden_process.status_code == 403
            forbidden_super_account_update = client.patch(
                f"/api/admin/accounts/{TEST_IDS['admin_a']}",
                json={"name": "owner_test_changed_by_super"},
            )
            assert forbidden_super_account_update.status_code == 403
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["admin_a"])
            process_a = client.post(
                "/api/admin/processes",
                json={"name": "owner_test_process_a", "price": 1, "unit": "元/个"},
            )
            assert process_a.status_code == 201
            account_a = client.post(
                "/api/admin/accounts",
                json={
                    "account": "owner_test_employee_a",
                    "password": TEST_PASSWORD,
                    "role": "employee",
                    "process_ids": [process_a.json()["id"]],
                },
            )
            assert account_a.status_code == 201
            assert account_a.json()["managerId"] == TEST_IDS["admin_a"]
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["admin_b"])
            account_names_b = {account["account"] for account in client.get("/api/admin/accounts").json()}
            assert "owner_test_employee_a" not in account_names_b
            process_names_b = {process["name"] for process in client.get("/api/admin/processes").json()}
            assert "owner_test_process_a" not in process_names_b
            same_name_process_b = client.post(
                "/api/admin/processes",
                json={"name": "owner_test_process_a", "price": 2, "unit": "元/个"},
            )
            assert same_name_process_b.status_code == 201
            forbidden_cross_process_account = client.post(
                "/api/admin/accounts",
                json={
                    "account": "owner_test_employee_b_cross",
                    "password": TEST_PASSWORD,
                    "role": "employee",
                    "process_ids": [process_a.json()["id"]],
                },
            )
            assert forbidden_cross_process_account.status_code == 403
            forbidden_update = client.patch(
                f"/api/admin/processes/{process_a.json()['id']}",
                json={"name": "owner_test_process_b_stolen"},
            )
            assert forbidden_update.status_code in {403, 404}
            forbidden_delete = client.delete(f"/api/admin/processes/{process_a.json()['id']}")
            assert forbidden_delete.status_code in {403, 404}
            forbidden_account_delete = client.delete(f"/api/admin/accounts/{account_a.json()['id']}")
            assert forbidden_account_delete.status_code in {403, 404}
            assert client.post("/api/auth/logout").status_code == 200

            login(client, TEST_ACCOUNTS["super"])
            account_names_super = {account["account"] for account in client.get("/api/admin/accounts").json()}
            assert "owner_test_employee_a" in account_names_super
            process_names_super = {process["name"] for process in client.get("/api/admin/processes").json()}
            assert "owner_test_process_a" in process_names_super
            forbidden_super_process_update = client.patch(
                f"/api/admin/processes/{process_a.json()['id']}",
                json={"name": "owner_test_changed_by_super"},
            )
            assert forbidden_super_process_update.status_code == 403
            assert client.delete(f"/api/admin/processes/{process_a.json()['id']}").status_code == 403
    finally:
        asyncio.run(delete_test_data())
