processed: set[str] = set()


def charge(customer_id: str, cents: int) -> None:
    pass


def handle(event: dict[str, object]) -> int:
    event_id = str(event["event_id"])
    charge(str(event["customer_id"]), int(event["cents"]))
    processed.add(event_id)
    return 204
