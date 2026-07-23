from __future__ import annotations


def require_admin(user: dict[str, object]) -> None:
    if user.get("role") != "admin":
        raise PermissionError("administrator role required")
