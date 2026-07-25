def current(provider, payload: dict[str, str]) -> str:
    return provider.send({"external_name": payload["name"]})["external_id"]


def secondary(provider, payload: dict[str, str]) -> str:
    return provider.send({"external_name": payload["name"]})["external_id"]
