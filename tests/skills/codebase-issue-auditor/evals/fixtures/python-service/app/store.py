from __future__ import annotations

ACCOUNTS: dict[str, str] = {"a-1": "active"}


def delete_account(account_id: str) -> None:
    ACCOUNTS.pop(account_id, None)
