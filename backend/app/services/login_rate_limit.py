from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

_lock = Lock()
_records: dict[str, "_FailureRecord"] = {}


@dataclass
class _FailureRecord:
    failures: int = 0
    locked_until: datetime | None = None


def _normalize_account(account: str) -> str:
    return account.strip().lower()


def check_locked(account: str, lockout_seconds: int) -> str | None:
    key = _normalize_account(account)
    now = datetime.now(UTC)
    with _lock:
        record = _records.get(key)
        if not record or not record.locked_until:
            return None
        if record.locked_until <= now:
            record.locked_until = None
            record.failures = 0
            return None
        return "登录尝试过多，请稍后再试"


def record_failure(account: str, max_failures: int, lockout_seconds: int) -> None:
    key = _normalize_account(account)
    now = datetime.now(UTC)
    with _lock:
        record = _records.setdefault(key, _FailureRecord())
        if record.locked_until and record.locked_until > now:
            return
        record.failures += 1
        if record.failures >= max_failures:
            record.locked_until = now + timedelta(seconds=lockout_seconds)


def clear_failures(account: str) -> None:
    key = _normalize_account(account)
    with _lock:
        _records.pop(key, None)


def clear_all_failures() -> None:
    with _lock:
        _records.clear()
