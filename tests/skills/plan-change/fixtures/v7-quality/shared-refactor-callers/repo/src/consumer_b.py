from src.lib.core import normalize

def tidy(value: str) -> str:
    return normalize(value).strip()
