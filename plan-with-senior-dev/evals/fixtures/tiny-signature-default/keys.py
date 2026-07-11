def format_key(namespace: str, name: str) -> str:
    return f"{namespace}:{name}"


def user_key(user_id: str) -> str:
    return format_key("user", user_id)


def team_key(team_id: str) -> str:
    return format_key("team", team_id)
