"""Debug template integrity hash mismatch."""
import argparse
import hashlib
import re
import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
TEMPLATE = REPO_ROOT / "skills" / "engineering" / "create-diagram" / "assets" / "html-diagram-template.html"


def strip_data_sections(text: str) -> str:
    result = text
    diag_m = re.search(r'const\s+DIAGRAM_DATA\s*=', result, re.DOTALL)
    if diag_m:
        depth = 0
        in_str = False
        esc = False
        for i in range(diag_m.end(), len(result)):
            if in_str:
                if esc:
                    esc = False
                elif result[i] == "\\":
                    esc = True
                elif result[i] == '"':
                    in_str = False
                continue
            if result[i] == '"':
                in_str = True
            elif result[i] == '{':
                depth += 1
            elif result[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    rest = result[end:end + 10]
                    if rest.startswith(";"):
                        end += 1
                    result = result[: diag_m.start()] + "const DIAGRAM_DATA = {};" + result[end:]
                    break
    meta_m = re.search(r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>', result, re.DOTALL)
    if meta_m:
        result = (
            result[: meta_m.start()]
            + '<script type="application/json" id="agent-metadata">{}</script>'
            + result[meta_m.end() :]
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug template integrity hash mismatch.")
    parser.add_argument("output_path", help="Path to the generated HTML output file to compare against template.")
    args = parser.parse_args()

    output = Path(args.output_path)
    if not output.exists():
        print(f"ERROR: Output file not found: {output}", file=sys.stderr)
        return 1

    tmpl = TEMPLATE.read_text(encoding="utf-8")
    out = output.read_text(encoding="utf-8")

    t_clean = strip_data_sections(tmpl)
    o_clean = strip_data_sections(out)

    t_hash = hashlib.sha256(t_clean.encode("utf-8")).hexdigest()
    o_hash = hashlib.sha256(o_clean.encode("utf-8")).hexdigest()

    print("Template hash:", t_hash)
    print("Output hash:  ", o_hash)
    print("Match:", t_hash == o_hash)

    if t_hash != o_hash:
        t_lines = t_clean.split("\n")
        o_lines = o_clean.split("\n")
        for i, (tl, ol) in enumerate(zip(t_lines, o_lines)):
            if tl != ol:
                print(f"First diff at line {i + 1}:")
                print(f"  Template len={len(tl)}, Output len={len(ol)}")
                print(f"  Template: {tl[:120]!r}")
                print(f"  Output:   {ol[:120]!r}")
                break
        print(f"Template lines: {len(t_lines)}, Output lines: {len(o_lines)}")
        if len(t_lines) != len(o_lines):
            print(f"Line count mismatch at line {min(len(t_lines), len(o_lines))}")
            if len(o_lines) > len(t_lines):
                for j in range(len(t_lines), len(o_lines)):
                    print(f"  Extra output: {o_lines[j][:120]!r}")
            else:
                for j in range(len(o_lines), len(t_lines)):
                    print(f"  Missing from output: {t_lines[j][:120]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
