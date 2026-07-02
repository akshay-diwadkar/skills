"""Debug template integrity hash mismatch."""
import hashlib, re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "html-excalidraw-template.html"
OUTPUT = Path(r"C:\Users\Akshay Diwadkar\.agents\skills\plan-with-senior-dev\plan-with-senior-dev-skill-architecture.html")


def strip_data_sections(text):
    result = text
    diag_m = re.search(r'const\s+DIAGRAM_DATA\s*=', result, re.DOTALL)
    if diag_m:
        depth = 0; in_str = False; esc = False
        for i in range(diag_m.end(), len(result)):
            if in_str:
                if esc: esc = False
                elif result[i] == '\\': esc = True
                elif result[i] == '"': in_str = False
                continue
            if result[i] == '"': in_str = True
            elif result[i] == '{':
                if depth == 0: start = i
                depth += 1
            elif result[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    rest = result[end:end + 10]
                    if rest.startswith(';'):
                        end += 1
                    result = result[:diag_m.start()] + 'const DIAGRAM_DATA = {};' + result[end:]
                    break
    meta_m = re.search(r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>', result, re.DOTALL)
    if meta_m:
        result = result[:meta_m.start()] + '<script type="application/json" id="agent-metadata">{}</script>' + result[meta_m.end():]
    return result


tmpl = TEMPLATE.read_text(encoding='utf-8')
out = OUTPUT.read_text(encoding='utf-8')

t_clean = strip_data_sections(tmpl)
o_clean = strip_data_sections(out)

t_hash = hashlib.sha256(t_clean.encode('utf-8')).hexdigest()
o_hash = hashlib.sha256(o_clean.encode('utf-8')).hexdigest()

print('Template hash:', t_hash)
print('Output hash:  ', o_hash)
print('Match:', t_hash == o_hash)

if t_hash != o_hash:
    t_lines = t_clean.split('\n')
    o_lines = o_clean.split('\n')
    for i, (tl, ol) in enumerate(zip(t_lines, o_lines)):
        if tl != ol:
            print(f'First diff at line {i+1}:')
            print(f'  Template len={len(tl)}, Output len={len(ol)}')
            print(f'  Template: {repr(tl[:120])}')
            print(f'  Output:   {repr(ol[:120])}')
            break
    print(f'Template lines: {len(t_lines)}, Output lines: {len(o_lines)}')
    if len(t_lines) != len(o_lines):
        print(f'Line count mismatch at line {min(len(t_lines), len(o_lines))}')
        if len(o_lines) > len(t_lines):
            for j in range(len(t_lines), len(o_lines)):
                print(f'  Extra output: {repr(o_lines[j][:120])}')
        else:
            for j in range(len(o_lines), len(t_lines)):
                print(f'  Missing from output: {repr(t_lines[j][:120])}')
