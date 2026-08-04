def render_adapter() -> str:
    return "def generated_names(value):\n    return value\n"

def main() -> None:
    with open("src/generated_names.py", "w", encoding="utf-8") as handle:
        handle.write(render_adapter())

if __name__ == "__main__":
    main()
