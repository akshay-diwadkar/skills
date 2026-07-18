from .schema import UserEvent


def build_event(user_id: str) -> UserEvent:
    return {"user_id": user_id}
