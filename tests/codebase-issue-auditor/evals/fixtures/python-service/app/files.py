from pathlib import Path


def load_text(path: Path) -> str:
    with path.open(encoding="utf-8") as handle:
        return handle.read()
