def scan(values: list[str]) -> list[str]:
    result = []
    for value in values:
        length = len(value)
        if length > 3:
            result.append(value)
    return result
