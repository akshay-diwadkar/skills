def send(client: object, payload: dict[str, str]) -> object:
    return client.post(payload)
