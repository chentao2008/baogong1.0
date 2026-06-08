import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                create table if not exists admin_accounts (
                    id text primary key,
                    account text not null unique,
                    password text not null,
                    role text not null check (role in ('super_admin', 'admin', 'employee')),
                    name text not null,
                    status text not null check (status in ('active', 'disabled')),
                    manager_id text null,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists processes (
                    id text primary key,
                    name text not null,
                    price numeric(12, 2) not null check (price >= 0),
                    unit text not null,
                    status text not null check (status in ('active', 'disabled')),
                    manager_id text null,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists account_processes (
                    account_id text not null references admin_accounts(id) on delete cascade,
                    process_id text not null references processes(id) on delete cascade,
                    primary key (account_id, process_id)
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists work_reports (
                    id text primary key,
                    account_id text not null references admin_accounts(id) on delete cascade,
                    work_date date not null,
                    process_id text not null references processes(id),
                    quantity numeric(12, 2) not null check (quantity > 0),
                    unit_price numeric(12, 2) not null check (unit_price >= 0),
                    total_price numeric(12, 2) not null check (total_price >= 0),
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists auth_sessions (
                    id text primary key,
                    account_id text not null references admin_accounts(id) on delete cascade,
                    created_at timestamptz not null default now(),
                    expires_at timestamptz not null
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                create table if not exists audit_logs (
                    id text primary key,
                    actor_id text not null,
                    action text not null,
                    target_type text not null,
                    target_id text not null,
                    payload_json jsonb not null,
                    created_at timestamptz not null default now()
                )
                """
            )
        )
        await connection.execute(
            text("create index if not exists idx_auth_sessions_account_id on auth_sessions(account_id)")
        )
        await connection.execute(
            text("create index if not exists idx_auth_sessions_expires_at on auth_sessions(expires_at)")
        )
        await connection.execute(text("create index if not exists idx_audit_logs_actor_id on audit_logs(actor_id)"))
        await connection.execute(text("create index if not exists idx_audit_logs_action on audit_logs(action)"))
        await connection.execute(text("create index if not exists idx_audit_logs_created_at on audit_logs(created_at)"))
        await connection.execute(text("alter table processes add column if not exists manager_id text null"))
        await connection.execute(text("alter table processes drop constraint if exists processes_name_key"))
        await connection.execute(text("create index if not exists idx_processes_manager_id on processes(manager_id)"))
        await connection.execute(
            text("create unique index if not exists idx_processes_manager_name on processes(manager_id, name)")
        )
        await connection.execute(
            text(
                """
                update processes process
                set manager_id = inferred.manager_id
                from (
                    select link.process_id, min(account.manager_id) as manager_id
                    from account_processes link
                    inner join admin_accounts account on account.id = link.account_id
                    where account.manager_id is not null
                    group by link.process_id
                    having count(distinct account.manager_id) = 1
                ) inferred
                where process.id = inferred.process_id
                  and process.manager_id is null
                """
            )
        )

        # Performance indexes for work-report queries and managed-account filters.
        await connection.execute(
            text(
                "create index if not exists idx_work_reports_account_date "
                "on work_reports(account_id, work_date desc)"
            )
        )
        await connection.execute(
            text("create index if not exists idx_work_reports_work_date on work_reports(work_date desc)")
        )
        await connection.execute(
            text("create index if not exists idx_work_reports_process_id on work_reports(process_id)")
        )
        await connection.execute(
            text("create index if not exists idx_admin_accounts_manager_id on admin_accounts(manager_id)")
        )
        await connection.execute(
            text("create index if not exists idx_account_processes_process_id on account_processes(process_id)")
        )

        # Try to add the (account_id, work_date, process_id) unique constraint.
        # Before adding, surface any existing duplicates so they can be merged by
        # a human; never delete user data automatically.
        duplicates = await connection.execute(
            text(
                """
                select account_id, work_date, process_id, count(*) as duplicate_count
                from work_reports
                group by account_id, work_date, process_id
                having count(*) > 1
                limit 5
                """
            )
        )
        duplicate_rows = duplicates.fetchall()
        if duplicate_rows:
            logger.warning(
                "work_reports has %d duplicate (account_id, work_date, process_id) groups; "
                "skipping unique constraint creation. Sample: %s. "
                "Run `python backend/scripts/detect_duplicate_reports.py` and merge manually.",
                len(duplicate_rows),
                [
                    {
                        "account_id": row.account_id,
                        "work_date": row.work_date.isoformat(),
                        "process_id": row.process_id,
                        "duplicate_count": int(row.duplicate_count),
                    }
                    for row in duplicate_rows
                ],
            )
        else:
            await connection.execute(
                text(
                    "create unique index if not exists uniq_work_reports_account_date_process "
                    "on work_reports(account_id, work_date, process_id)"
                )
            )

        # Account, process, and account-process permissions are managed explicitly
        # from the admin pages. Startup only prepares schema and indexes.
