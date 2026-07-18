from .schema import UserEvent


def display_tenant(event: UserEvent) -> str:
    return event.get("tenant_id", "unknown")
