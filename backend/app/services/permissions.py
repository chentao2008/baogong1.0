from typing import Literal


Role = Literal["super_admin", "admin", "employee"]


def is_super_admin(role: str) -> bool:
    return role == "super_admin"


def is_admin(role: str) -> bool:
    return role in {"super_admin", "admin"}


def can_manage_account(actor: dict[str, object], target: dict[str, object]) -> bool:
    if is_super_admin(str(actor.get("role"))):
        return True
    return is_admin(str(actor.get("role"))) and target.get("managerId") == actor.get("id")


def can_view_employee_reports(actor: dict[str, object], account_id: str) -> bool:
    if is_admin(str(actor.get("role"))):
        return True
    return actor.get("id") == account_id
