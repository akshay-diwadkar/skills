from pathlib import Path

Path("generated/schema.json").write_text('{"public_field": "display_name"}\n', encoding="utf-8")
