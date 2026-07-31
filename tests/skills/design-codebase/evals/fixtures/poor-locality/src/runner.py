def run(timeout: int) -> str:
    if timeout > 300:
        raise ValueError("timeout too large")
    return f"running for {timeout}"
