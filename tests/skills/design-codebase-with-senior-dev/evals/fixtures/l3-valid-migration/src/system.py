def current(database, event: dict[str, str]) -> None:
    with database.transaction():
        database.update_account(event["account_id"])
        database.append_audit_event(event)
