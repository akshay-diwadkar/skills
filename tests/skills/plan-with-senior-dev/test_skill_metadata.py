from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev"


def parse_simple_frontmatter(text: str) -> dict[str, str | dict[str, str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")

    result: dict[str, str | dict[str, str]] = {}
    current_key: str | None = None
    nested_dict: dict[str, str] = {}

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  ") and current_key is not None:
            if ":" in line:
                k, v = line.split(":", 1)
                nested_dict[k.strip()] = v.strip().strip('"').strip("'")
        elif ":" in line:
            if current_key is not None and nested_dict:
                result[current_key] = nested_dict
                nested_dict = {}
                current_key = None
            k, v = line.split(":", 1)
            key_str = k.strip()
            val_str = v.strip().strip('"').strip("'")
            if not val_str:
                current_key = key_str
            else:
                result[key_str] = val_str

    if current_key is not None and nested_dict:
        result[current_key] = nested_dict

    return result


def test_frontmatter_declares_existing_required_finalizer() -> None:
    content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = parse_simple_frontmatter(content)
    metadata = frontmatter["metadata"]
    assert metadata == {
        "plan-contract": "3",
        "finalizer": "scripts/finalize_plan.py",
        "validation-required": "true",
    }
    assert isinstance(metadata, dict)
    assert (SKILL / str(metadata["finalizer"])).is_file()
