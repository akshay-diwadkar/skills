def current(database, order: dict[str, str]) -> str:
    with database.transaction():
        database.reserve(order["sku"])
        database.authorize(order["payment"])
        return database.create_order(order)
