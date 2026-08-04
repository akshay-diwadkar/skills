def run(mode: str) -> str:
    if mode != "verbose":
        return "skipped"
    return "running"
