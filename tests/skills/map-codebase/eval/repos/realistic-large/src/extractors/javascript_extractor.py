def extract_arrow_function_exports(source: str) -> list[str]:
    """Return exported JavaScript arrow-function declarations."""
    return [line for line in source.splitlines() if "export " in line and "=>" in line]
