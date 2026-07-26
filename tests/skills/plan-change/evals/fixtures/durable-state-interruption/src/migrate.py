def migrate(rows: list[dict[str, str]]) -> None:
    for row in rows:
        row["version"] = "2"
