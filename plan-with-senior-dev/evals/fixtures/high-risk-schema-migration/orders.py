def read_status(row: dict[str, str | None]) -> str:
    return row["status"] or "pending"


def create_order(order_id: str) -> dict[str, str | None]:
    return {"id": order_id, "status": None}
