from __future__ import annotations

from .auth import require_admin
from .jobs import attempts_for
from .store import delete_account


def submit_job(payload: dict[str, object]) -> dict[str, int]:
    retries = payload.get("retries")
    if retries is not None and not isinstance(retries, int):
        raise ValueError("retries must be an integer")
    return {"attempts": attempts_for(retries)}


def list_accounts(current_user: dict[str, object]) -> list[str]:
    require_admin(current_user)
    return ["a-1"]


def remove_account(current_user: dict[str, object], account_id: str) -> None:
    del current_user
    delete_account(account_id)
