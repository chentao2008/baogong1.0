import asyncio
import os
import time

from sqlalchemy import text

from app.db.init_db import initialize_database
from app.db.session import AsyncSessionLocal
from app.services.auth import hash_password
from app.services.password_view import encrypt_viewable_password


async def main() -> None:
    account = os.getenv("INITIAL_ADMIN_ACCOUNT", "admin").strip()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "").strip()
    name = os.getenv("INITIAL_ADMIN_NAME", "管理员").strip() or account
    role = os.getenv("INITIAL_ADMIN_ROLE", "admin").strip()

    if not account:
        raise SystemExit("INITIAL_ADMIN_ACCOUNT is required")
    if len(password) < 8:
        raise SystemExit("INITIAL_ADMIN_PASSWORD must be at least 8 characters")
    if role not in {"admin", "super_admin"}:
        raise SystemExit("INITIAL_ADMIN_ROLE must be admin or super_admin")

    await initialize_database()

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            text("select id from admin_accounts where account = :account limit 1"),
            {"account": account},
        )
        if existing.first():
            print(f"initial admin account already exists: {account}")
            return

        account_id = f"admin-{int(time.time() * 1000)}"
        password_ciphertext = encrypt_viewable_password(password)
        await session.execute(
            text(
                """
                insert into admin_accounts (
                    id, account, password, role, name, status, manager_id,
                    password_view_ciphertext, password_view_updated_at
                )
                values (
                    :id, :account, :password, :role, :name, 'active', null,
                    :password_view_ciphertext,
                    case when cast(:password_view_ciphertext as text) is null then null else now() end
                )
                """
            ),
            {
                "id": account_id,
                "account": account,
                "password": hash_password(password),
                "role": role,
                "name": name,
                "password_view_ciphertext": password_ciphertext,
            },
        )
        await session.commit()
        print(f"created initial admin account: {account}")


if __name__ == "__main__":
    asyncio.run(main())
