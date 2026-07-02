"""Validate generated Excalidraw-style diagram HTML.

Usage:
    python validate_diagram.py <path-to-diagram.html>

Exits 0 if the diagram is valid, 1 if errors are found.
Errors are printed to stderr with prefix "ERROR:".
Warnings are printed to stderr with prefix "WARNING:".
"""

import hashlib
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "html-excalidraw-template.html"

CANONICAL_TYPES = frozenset({
    "service", "external-system", "database", "queue", "file", "document",
    "object-store", "actor", "process", "decision", "event", "concept",
    "failure-state",
})

TYPE_ALIASES = {
    "internal-service": "service",
    "data-store": "database",
}

VALID_FIDELITY = frozenset({"narrative-architecture", "exact-code-graph", "executive-concept-map"})
VALID_CONFIDENCE = frozenset({"observed", "inferred", "stated"})
VALID_CLUSTER_LAYOUTS = frozenset({"vertical", "circular"})
DEFAULT_STORAGE_KEY = "arch-overview-v1"


def resolve_type(raw):
    return TYPE_ALIASES.get(raw, raw)


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


# ----- raw extraction -----

def extract_raw_js_block(text, var_name):
    """Extract the raw JS object literal for `const var_name = {...};`.

    Returns the raw text between { and the matching }, or None.
    """
    pattern = re.compile(
        r'const\s+' + re.escape(var_name) + r'\s*=\s*',
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return None

    start = m.end()
    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == '{':
            if depth == 0:
                brace_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[brace_start:i + 1]

    return None


def js_obj_to_json(raw):
    """Convert a JS object literal to valid JSON (quote keys, strip trailing commas)."""
    result = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == '"':
            result.append(ch)
            i += 1
            while i < len(raw):
                if raw[i] == '\\':
                    result.append(raw[i])
                    i += 1
                    if i < len(raw):
                        result.append(raw[i])
                        i += 1
                elif raw[i] == '"':
                    result.append(ch)
                    i += 1
                    break
                else:
                    result.append(raw[i])
                    i += 1
        elif ch == "'":
            result.append('"')
            i += 1
            while i < len(raw):
                if raw[i] == '\\':
                    result.append(raw[i])
                    i += 1
                    if i < len(raw):
                        result.append(raw[i])
                        i += 1
                elif raw[i] == "'":
                    result.append('"')
                    i += 1
                    break
                else:
                    result.append(raw[i])
                    i += 1
        elif ch in '{}[](),':
            result.append(ch)
            i += 1
        elif ch == '/' and i + 1 < len(raw) and raw[i + 1] == '/':
            i += 2
            while i < len(raw) and raw[i] != '\n':
                i += 1
        elif ch == '/' and i + 1 < len(raw) and raw[i + 1] == '*':
            i += 2
            while i + 1 < len(raw) and not (raw[i] == '*' and raw[i + 1] == '/'):
                i += 1
            i += 2
        elif ch in ' \t\n\r':
            result.append(ch)
            i += 1
        elif re.match(r'[\w_$]', ch) and (
            i == 0 or not re.match(r'[\w_$]', raw[i - 1]) and raw[i - 1] not in '."\''
        ):
            key_match = re.match(r'([\w_$]+)\s*:', raw[i:])
            if key_match:
                result.append('"' + key_match.group(1) + '":')
                i += len(key_match.group(0))
            else:
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1

    converted = ''.join(result)
    converted = re.sub(r',(\s*[}\]])', r'\1', converted)
    return converted


def extract_agent_metadata(text):
    pattern = re.compile(
        r'<script\s+type="application/json"\s+id="agent-metadata">(.*?)</script>',
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        warn("No #agent-metadata <script> tag found. Skipping metadata checks.")
        return None
    content = m.group(1).strip()
    if not content:
        warn("Empty #agent-metadata tag. Skipping metadata checks.")
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        warn(f"Could not parse #agent-metadata JSON: {e}")
        return None


# ----- pre-checks on the raw JS block -----

def check_dangerous_js(raw_block):
    """Scan the DIAGRAM_DATA JS object literal for unsupported syntax."""
    found = []
    for i, line in enumerate(raw_block.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('//'):
            continue
        if '`' in stripped:
            found.append((i, "template literal backtick string"))
        if '${' in stripped:
            found.append((i, "template interpolation ${}"))
    return found


def check_braces_in_strings(raw_block):
    """Scan for `{` or `}` inside double-quoted strings in the JS block.

    These would break the brace-depth parser because it can't distinguish
    structural braces from literal braces inside string values.
    """
    in_string = False
    escape = False
    line_num = 1
    for i, ch in enumerate(raw_block):
        if ch == '\n':
            line_num += 1
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            j = i + 1
            escaped = False
            while j < len(raw_block):
                if escaped:
                    escaped = False
                elif raw_block[j] == '\\':
                    escaped = True
                elif raw_block[j] == '"':
                    content = raw_block[i + 1:j]
                    if '\\' in content:
                        pass
                    break
                j += 1
        elif ch == '/' and i + 1 < len(raw_block):
            if raw_block[i + 1] == '/':
                while i < len(raw_block) and raw_block[i] != '\n':
                    i += 1
            elif raw_block[i + 1] == '*':
                i += 2
                while i + 1 < len(raw_block) and not (raw_block[i] == '*' and raw_block[i + 1] == '/'):
                    i += 1

    in_string = False
    escape = False
    line_num = 1
    for i, ch in enumerate(raw_block):
        if ch == '\n':
            line_num += 1
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '/' and i + 1 < len(raw_block):
            if raw_block[i + 1] == '/':
                while i < len(raw_block) and raw_block[i] != '\n':
                    i += 1
            elif raw_block[i + 1] == '*':
                i += 2
                while i + 1 < len(raw_block) and not (raw_block[i] == '*' and raw_block[i + 1] == '/'):
                    i += 1

    in_string = False
    escape = False
    line_num = 1
    for i, ch in enumerate(raw_block):
        if ch == '\n':
            line_num += 1
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            j = i + 1
            escaped = False
            s_line = line_num
            while j < len(raw_block):
                ch2 = raw_block[j]
                if ch2 == '\n':
                    line_num += 1
                if escaped:
                    escaped = False
                elif ch2 == '\\':
                    escaped = True
                elif ch2 == '"':
                    content = raw_block[i + 1:j]
                    if '{' in content or '}' in content:
                        return [(s_line, content)]
                    break
                j += 1
            i = j
    return []


# ----- template integrity -----

def strip_data_sections(text):
    """Replace DIAGRAM_DATA and agent-metadata with sentinels for hashing."""
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
                elif result[i] == '\\':
                    esc = True
                elif result[i] == '"':
                    in_str = False
                continue
            if result[i] == '"':
                in_str = True
            elif result[i] == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif result[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    rest = result[end:].strip()
                    if rest.startswith(';'):
                        end += 1
                    result = result[:diag_m.start()] + 'const DIAGRAM_DATA = {};' + result[end:]
                    break

    meta_m = re.search(
        r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>',
        result, re.DOTALL,
    )
    if meta_m:
        result = result[:meta_m.start()] + '<script type="application/json" id="agent-metadata">{}</script>' + result[meta_m.end():]

    return result


def compute_template_hash(template_path):
    if not template_path.exists():
        return None
    text = template_path.read_text(encoding="utf-8")
    clean = strip_data_sections(text)
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def check_template_integrity(output_path):
    template_hash = compute_template_hash(TEMPLATE_PATH)
    if template_hash is None:
        return ["Template file not found at " + str(TEMPLATE_PATH)]

    output_text = output_path.read_text(encoding="utf-8")
    output_clean = strip_data_sections(output_text)
    output_hash = hashlib.sha256(output_clean.encode("utf-8")).hexdigest()

    if output_hash != template_hash:
        return [
            "Generated file's template structure (HTML, CSS, JS outside DIAGRAM_DATA and"
            " #agent-metadata) does not match the canonical template."
            " The agent must not modify template rendering code."
        ]
    return []


# ----- structural completeness -----

def check_structural_completeness(text):
    issues = []
    if '</html>' not in text:
        issues.append("File is missing closing </html> tag — document may be truncated.")
    if '</body>' not in text:
        issues.append("File is missing closing </body> tag — document may be truncated.")
    if 'init();' not in text or '</script>' not in text:
        issues.append("Missing init(); call or closing </script> — module script may be truncated.")
    return issues


# ----- evidence quality -----

EVIDENCE_FILE_LINE = re.compile(r'^[\w/.+-]+:\d+$')
EVIDENCE_FILE_RANGE = re.compile(r'^[\w/.+-]+:\d+-\d+$')
EVIDENCE_USER_STATED = re.compile(r'^user-stated\b')


def evidence_quality(evidence):
    if not evidence:
        return "missing"
    if EVIDENCE_FILE_LINE.match(evidence):
        return None
    if EVIDENCE_FILE_RANGE.match(evidence):
        return None
    if EVIDENCE_USER_STATED.match(evidence):
        return None
    return "unusual format (expected file:line, file:start-end, or user-stated)"


# ----- validation -----

def check_cluster_edge_skips(data, emit_error):
    """Validate that no edge between nodes in different clusters
    passes through a third cluster's bounding box.
    """
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    clusters = data.get("clusters") or []
    if not nodes or not edges or not clusters:
        return

    node_by_id = {}
    for n in nodes:
        nid = n.get("id")
        if nid and "x" in n:
            node_by_id[nid] = n

    node_to_cluster = {}
    for c in clusters:
        cid = c.get("id") or c.get("label")
        if not cid:
            continue
        for nid in (c.get("nodeIds") or []):
            node_to_cluster[nid] = cid

    def _nw(label, desc):
        lw = len(label) * 18 + 88
        dw = (min(len(desc), 96) * 10.6 + 76) if desc else 0
        return max(340, lw, dw)

    def _nh(n):
        if not n.get("description"):
            return 124
        return 205 + (min((len(n["description"]) + 30) // 31, 3) - 1) * 30

    def _box(n):
        return {"x": n["x"], "y": n["y"], "w": _nw(n.get("label", ""), n.get("description")), "h": _nh(n)}

    def _cbox(c):
        mids = c.get("nodeIds") or []
        mems = [node_by_id.get(mid) for mid in mids if node_by_id.get(mid)]
        if not mems:
            return None
        px, py = 56, 44
        min_x = min(m["x"] for m in mems) - px
        min_y = min(m["y"] for m in mems) - px - py
        max_x = max(m["x"] + _nw(m.get("label", ""), m.get("description")) + 10 for m in mems) + px
        max_y = max(m["y"] + _nh(m) + 10 for m in mems) + px
        return {"x": min_x, "y": min_y, "w": max_x - min_x, "h": max_y - min_y}

    def _pib(px, py, bx):
        return bx and bx["x"] <= px <= bx["x"] + bx["w"] and bx["y"] <= py <= bx["y"] + bx["h"]

    def _ovl(a, b, gap=0):
        if not a or not b:
            return False
        return not (a["x"] + a["w"] + gap <= b["x"] or b["x"] + b["w"] + gap <= a["x"] or
                    a["y"] + a["h"] + gap <= b["y"] or b["y"] + b["h"] + gap <= a["y"])

    def _exp(bx, pad):
        return {"x": bx["x"] - pad, "y": bx["y"] - pad, "w": bx["w"] + pad * 2, "h": bx["h"] + pad * 2}

    def _anchor(f, t):
        a, acx, acy = _box(f), _box(f)["x"] + _box(f)["w"] / 2, _box(f)["y"] + _box(f)["h"] / 2
        bc = _box(t)
        bcx, bcy = bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] / 2
        dx, dy = bcx - acx, bcy - acy
        ep = 8
        if abs(dx) >= abs(dy):
            return {"x": a["x"] + a["w"] + ep, "y": acy} if dx >= 0 else {"x": a["x"] - ep, "y": acy}
        return {"x": acx, "y": a["y"] + a["h"] + ep} if dy >= 0 else {"x": acx, "y": a["y"] - ep}

    def _i32(x):
        x &= 0xFFFFFFFF
        return x - 0x100000000 if x >= 0x80000000 else x

    def _poff(eidx, elist):
        e = elist[eidx]
        sp = [(i, x) for i, x in enumerate(elist) if x.get("sourceId") == e.get("sourceId") and x.get("targetId") == e.get("targetId")]
        pi = next((j for j, (i, _) in enumerate(sp) if i == eidx), 0)
        key = f"{e.get('sourceId')}->{e.get('targetId')}"
        h = 0
        for ch in key:
            h = _i32((h << 5) - h + ord(ch))
        return (pi - (len(sp) - 1) / 2) * 28 + (18 if (h & 1) == 0 else -18)

    def _smp(pts, steps=12):
        if len(pts) < 3:
            return pts
        a, c, b = pts[0], pts[1], pts[2]
        out = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1 - t
            out.append({"x": mt * mt * a["x"] + 2 * mt * t * c["x"] + t * t * b["x"],
                        "y": mt * mt * a["y"] + 2 * mt * t * c["y"] + t * t * b["y"]})
        return out

    def _lbx(label, x, y):
        w = max(64, len(label) * 13.2 + 30)
        return {"x": x - w / 2, "y": y - 12 - 17, "w": w, "h": 34}

    cboxes = {}
    for c in clusters:
        cid = c.get("id") or c.get("label")
        if not cid:
            continue
        bx = _cbox(c)
        if bx:
            cboxes[cid] = bx
    if not cboxes:
        return

    for i, edge in enumerate(edges):
        sid, tid = edge.get("sourceId"), edge.get("targetId")
        if not sid or not tid:
            continue
        sn, tn = node_by_id.get(sid), node_by_id.get(tid)
        if not sn or not tn:
            continue
        sc, tc = node_to_cluster.get(sid), node_to_cluster.get(tid)
        if sid == tid or (sc and sc == tc):
            continue
        if not sc and not tc:
            continue

        start = _anchor(sn, tn)
        end = _anchor(tn, sn)
        dx, dy = end["x"] - start["x"], end["y"] - start["y"]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            continue
        mx, my = (start["x"] + end["x"]) / 2, (start["y"] + end["y"]) / 2
        off = max(-80, min(80, _poff(i, edges) + min(dist * 0.08, 32)))
        ctrl = {"x": mx + dy / dist * off, "y": my - dx / dist * off}
        samples = _smp([start, ctrl, end])
        lbl = _lbx(edge.get("label", ""), ctrl["x"], ctrl["y"])

        for cid, bx in cboxes.items():
            if cid == sc or cid == tc:
                continue
            if any(_pib(sp["x"], sp["y"], _exp(bx, 4)) for sp in samples):
                emit_error(
                    f'Edge "{edge.get("label", "?")}" ({sid} -> {tid}) '
                    f'curve passes through cluster "{cid}".'
                )
            if _ovl(lbl, _exp(bx, 8)):
                emit_error(
                    f'Edge "{edge.get("label", "?")}" ({sid} -> {tid}) '
                    f'label overlaps cluster "{cid}".'
                )


def check_intra_cluster_node_skips(data, emit_error):
    """Validate that no edge between nodes in the same cluster
    passes through another node inside the same cluster.
    """
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    clusters = data.get("clusters") or []
    if not nodes or not edges or not clusters:
        return

    node_by_id = {}
    for n in nodes:
        nid = n.get("id")
        if nid and "x" in n:
            node_by_id[nid] = n

    def _nw(label, desc):
        lw = len(label) * 18 + 88
        dw = (min(len(desc), 96) * 10.6 + 76) if desc else 0
        return max(340, lw, dw)

    def _nh(n):
        if not n.get("description"):
            return 124
        return 205 + (min((len(n["description"]) + 30) // 31, 3) - 1) * 30

    def _box(n):
        return {"x": n["x"], "y": n["y"], "w": _nw(n.get("label", ""), n.get("description")), "h": _nh(n)}

    def _pib(px, py, bx):
        return bx and bx["x"] <= px <= bx["x"] + bx["w"] and bx["y"] <= py <= bx["y"] + bx["h"]

    def _ovl(a, b, gap=0):
        if not a or not b:
            return False
        return not (a["x"] + a["w"] + gap <= b["x"] or b["x"] + b["w"] + gap <= a["x"] or
                    a["y"] + a["h"] + gap <= b["y"] or b["y"] + b["h"] + gap <= a["y"])

    def _exp(bx, pad):
        return {"x": bx["x"] - pad, "y": bx["y"] - pad, "w": bx["w"] + pad * 2, "h": bx["h"] + pad * 2}

    def _anchor(f, t):
        fb = _box(f)
        fx = fb["x"] + fb["w"] / 2
        fy = fb["y"] + fb["h"] / 2
        tb = _box(t)
        dx = tb["x"] + tb["w"] / 2 - fx
        dy = tb["y"] + tb["h"] / 2 - fy
        ep = 8
        if abs(dx) >= abs(dy):
            return {"x": fb["x"] + fb["w"] + ep, "y": fy} if dx >= 0 else {"x": fb["x"] - ep, "y": fy}
        return {"x": fx, "y": fb["y"] + fb["h"] + ep} if dy >= 0 else {"x": fx, "y": fb["y"] - ep}

    def _i32(x):
        x &= 0xFFFFFFFF
        return x - 0x100000000 if x >= 0x80000000 else x

    def _poff(eidx, elist):
        e = elist[eidx]
        sp = [(i, x) for i, x in enumerate(elist)
              if x.get("sourceId") == e.get("sourceId") and x.get("targetId") == e.get("targetId")]
        pi = next((j for j, (i, _) in enumerate(sp) if i == eidx), 0)
        key = f"{e.get('sourceId')}->{e.get('targetId')}"
        h = 0
        for ch in key:
            h = _i32((h << 5) - h + ord(ch))
        return (pi - (len(sp) - 1) / 2) * 28 + (18 if (h & 1) == 0 else -18)

    def _smp(pts, steps=12):
        if len(pts) < 3:
            return pts
        a, c, b = pts[0], pts[1], pts[2]
        out = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1 - t
            out.append({"x": mt * mt * a["x"] + 2 * mt * t * c["x"] + t * t * b["x"],
                        "y": mt * mt * a["y"] + 2 * mt * t * c["y"] + t * t * b["y"]})
        return out

    def _lbx(label, x, y):
        w = max(64, len(label) * 13.2 + 30)
        return {"x": x - w / 2, "y": y - 12 - 17, "w": w, "h": 34}

    for i, edge in enumerate(edges):
        sid, tid = edge.get("sourceId"), edge.get("targetId")
        if not sid or not tid or sid == tid:
            continue
        sn, tn = node_by_id.get(sid), node_by_id.get(tid)
        if not sn or not tn:
            continue

        # Find which cluster this edge belongs to (if any)
        edge_cluster_id = None
        for c in clusters:
            cid = c.get("id") or c.get("label")
            if not cid:
                continue
            mids = c.get("nodeIds") or []
            if sid in mids and tid in mids:
                edge_cluster_id = cid
                break
        if not edge_cluster_id:
            continue

        start = _anchor(sn, tn)
        end = _anchor(tn, sn)
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            continue
        mx = (start["x"] + end["x"]) / 2
        my = (start["y"] + end["y"]) / 2
        off = max(-80, min(80, _poff(i, edges) + min(dist * 0.08, 32)))
        ctrl = {"x": mx + dy / dist * off, "y": my - dx / dist * off}
        samples = _smp([start, ctrl, end])
        lbl = _lbx(edge.get("label", ""), ctrl["x"], ctrl["y"])

        endpoint_ids = {sid, tid}
        for c in clusters:
            cid = c.get("id") or c.get("label")
            if cid != edge_cluster_id:
                continue
            for nid in (c.get("nodeIds") or []):
                if nid in endpoint_ids:
                    continue
                nd = node_by_id.get(nid)
                if not nd:
                    continue
                nb = _box(nd)
                if any(_pib(sp["x"], sp["y"], _exp(nb, 8)) for sp in samples[1:-1]):
                    emit_error(
                        f'Edge "{edge.get("label", "?")}" ({sid} -> {tid}) '
                        f'curve passes through node "{nid}" inside cluster "{cid}".'
                    )
                if _ovl(lbl, _exp(nb, 20)):
                    emit_error(
                        f'Edge "{edge.get("label", "?")}" ({sid} -> {tid}) '
                        f'label overlaps node "{nid}" inside cluster "{cid}".'
                    )


def check_edge_label_overlaps(data, emit_error):
    """Check all edge labels for overlap with each other and with non-incident nodes."""
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    if not nodes or not edges:
        return

    node_by_id = {}
    for n in nodes:
        nid = n.get("id")
        if nid and "x" in n:
            node_by_id[nid] = n
    if not node_by_id:
        return

    def _nw(label, desc):
        lw = len(label) * 18 + 88
        dw = (min(len(desc), 96) * 10.6 + 76) if desc else 0
        return max(340, lw, dw)

    def _nh(n):
        if not n.get("description"):
            return 124
        return 205 + (min((len(n["description"]) + 30) // 31, 3) - 1) * 30

    def _box(n):
        return {"x": n["x"], "y": n["y"], "w": _nw(n.get("label", ""), n.get("description")), "h": _nh(n)}

    def _pib(px, py, bx):
        return bx and bx["x"] <= px <= bx["x"] + bx["w"] and bx["y"] <= py <= bx["y"] + bx["h"]

    def _ovl(a, b, gap=0):
        if not a or not b:
            return False
        return not (a["x"] + a["w"] + gap <= b["x"] or b["x"] + b["w"] + gap <= a["x"] or
                    a["y"] + a["h"] + gap <= b["y"] or b["y"] + b["h"] + gap <= a["y"])

    def _exp(bx, pad):
        return {"x": bx["x"] - pad, "y": bx["y"] - pad, "w": bx["w"] + pad * 2, "h": bx["h"] + pad * 2}

    def _anchor(f, t):
        fb = _box(f)
        fx = fb["x"] + fb["w"] / 2
        fy = fb["y"] + fb["h"] / 2
        tb = _box(t)
        dx = tb["x"] + tb["w"] / 2 - fx
        dy = tb["y"] + tb["h"] / 2 - fy
        ep = 8
        if abs(dx) >= abs(dy):
            return {"x": fb["x"] + fb["w"] + ep, "y": fy} if dx >= 0 else {"x": fb["x"] - ep, "y": fy}
        return {"x": fx, "y": fb["y"] + fb["h"] + ep} if dy >= 0 else {"x": fx, "y": fb["y"] - ep}

    def _i32(x):
        x &= 0xFFFFFFFF
        return x - 0x100000000 if x >= 0x80000000 else x

    def _poff(eidx, elist):
        e = elist[eidx]
        sp = [(i, x) for i, x in enumerate(elist)
              if x.get("sourceId") == e.get("sourceId") and x.get("targetId") == e.get("targetId")]
        pi = next((j for j, (i, _) in enumerate(sp) if i == eidx), 0)
        key = f"{e.get('sourceId')}->{e.get('targetId')}"
        h = 0
        for ch in key:
            h = _i32((h << 5) - h + ord(ch))
        return (pi - (len(sp) - 1) / 2) * 28 + (18 if (h & 1) == 0 else -18)

    def _smp(pts, steps=12):
        if len(pts) < 3:
            return pts
        a, c, b = pts[0], pts[1], pts[2]
        out = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1 - t
            out.append({"x": mt * mt * a["x"] + 2 * mt * t * c["x"] + t * t * b["x"],
                        "y": mt * mt * a["y"] + 2 * mt * t * c["y"] + t * t * b["y"]})
        return out

    def _lbx(label, x, y):
        w = max(64, len(label) * 13.2 + 30)
        return {"x": x - w / 2, "y": y - 12 - 17, "w": w, "h": 34}

    # Compute all edge routes and label boxes
    route_info = []
    for i, edge in enumerate(edges):
        sid, tid = edge.get("sourceId"), edge.get("targetId")
        if not sid or not tid or sid == tid:
            continue
        sn, tn = node_by_id.get(sid), node_by_id.get(tid)
        if not sn or not tn:
            continue

        start = _anchor(sn, tn)
        end = _anchor(tn, sn)
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            continue
        mx = (start["x"] + end["x"]) / 2
        my = (start["y"] + end["y"]) / 2
        off = max(-160, min(160, _poff(i, edges) + min(dist * 0.08, 32)))
        ctrl = {"x": mx + dy / dist * off, "y": my - dx / dist * off}
        samples = _smp([start, ctrl, end])

        elabel = edge.get("label", "")
        label_box = _lbx(elabel, ctrl["x"], ctrl["y"])

        # Compute route length from samples
        rlen = sum(
            ((samples[j]["x"] - samples[j - 1]["x"]) ** 2 + (samples[j]["y"] - samples[j - 1]["y"]) ** 2) ** 0.5
            for j in range(1, len(samples))
        )

        route_info.append({
            "index": i,
            "label": elabel,
            "sourceId": sid,
            "targetId": tid,
            "labelBox": label_box,
            "routeLength": rlen,
        })

    # Check label-label overlap
    for a in route_info:
        for b in route_info:
            if a["index"] >= b["index"]:
                continue
            if _ovl(a["labelBox"], b["labelBox"], 8):
                emit_error(
                    f'Edge label "{a["label"]}" ({a["sourceId"]} -> {a["targetId"]}) '
                    f'overlaps edge label "{b["label"]}" ({b["sourceId"]} -> {b["targetId"]}).'
                )

    # Check label-node overlap (label vs non-incident node)
    for ri in route_info:
        for n in nodes:
            nid = n.get("id")
            if nid in (ri["sourceId"], ri["targetId"]):
                continue
            if "x" not in n:
                continue
            nb = _box(n)
            if _ovl(ri["labelBox"], _exp(nb, 20)):
                emit_error(
                    f'Edge label "{ri["label"]}" ({ri["sourceId"]} -> {ri["targetId"]}) '
                    f'overlaps node "{n.get("label", nid)}".'
                )

    # Check edge length vs label width
    for ri in route_info:
        label_w = max(64, len(ri["label"]) * 13.2 + 30)
        min_edge = max(label_w * 1.3, 160)
        if ri["routeLength"] < min_edge:
            emit_error(
                f'Edge "{ri["label"]}" ({ri["sourceId"]} -> {ri["targetId"]}) '
                f'is too short ({ri["routeLength"]:.0f}px) for its label '
                f'(minimum {min_edge:.0f}px).'
            )


def validate(data, metadata):
    errors = 0
    warnings = 0
    node_ids = set()
    node_labels = {}
    node_types_map = {}

    def emit_error(msg):
        nonlocal errors
        errors += 1
        fail(msg)

    def emit_warning(msg):
        nonlocal warnings
        warnings += 1
        warn(msg)

    if not isinstance(data, dict):
        emit_error("DIAGRAM_DATA is not a valid JSON object.")
        return errors, warnings

    # title
    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        emit_error("DIAGRAM_DATA.title is missing or empty.")

    # storageKey default check
    storage_key = data.get("storageKey")
    if storage_key == DEFAULT_STORAGE_KEY:
        emit_warning(f'storageKey is "{DEFAULT_STORAGE_KEY}" (the template default).'
                     f' Set a unique key or omit it to avoid localStorage collisions.')

    # fidelity
    fidelity = data.get("fidelity")
    if fidelity and fidelity not in VALID_FIDELITY:
        emit_error(f'Unknown fidelity "{fidelity}".'
                   f' Valid values: {", ".join(sorted(VALID_FIDELITY))}.')

    # takeaways
    takeaways = data.get("takeaways")
    if takeaways and len(takeaways) > 3:
        emit_warning("takeaways has more than 3 items; brief panel may be hard to scan.")

    # nodes
    nodes = data.get("nodes")
    incident_edge_count = {}
    if not isinstance(nodes, list):
        emit_error("DIAGRAM_DATA.nodes is missing or not an array.")
        nodes = []
    else:
        if len(nodes) == 0:
            emit_error("DIAGRAM_DATA.nodes is empty.")

        seen = set()
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                emit_error(f"nodes[{i}] is not an object.")
                continue
            nid = node.get("id")
            if not nid or not isinstance(nid, str):
                emit_error(f"nodes[{i}] is missing a valid 'id' (non-empty string).")
                continue
            if nid in seen:
                emit_error(f'Duplicate node id "{nid}".')
            seen.add(nid)
            node_ids.add(nid)
            node_labels[nid] = node.get("label", "")
            node_types_map[nid] = resolve_type(node.get("type", ""))
            incident_edge_count[nid] = 0

            label = node.get("label")
            if not label or not isinstance(label, str):
                emit_error(f'Node "{nid}" is missing a valid "label" (non-empty string).')

            ntype = node.get("type")
            if not ntype or not isinstance(ntype, str):
                emit_error(f'Node "{nid}" is missing a valid "type".')
            elif resolve_type(ntype) not in CANONICAL_TYPES:
                resolved = resolve_type(ntype)
                emit_error(f'Node "{nid}" has unknown type "{ntype}" (resolved to "{resolved}").')

            desc = node.get("description")
            if desc is not None:
                if not isinstance(desc, str):
                    emit_error(f'Node "{nid}" description must be a string.')
                elif len(desc) < 15 or len(desc) > 96:
                    emit_warning(f'Node "{nid}" description is {len(desc)} chars (recommended 15-96).')

    # edges
    edges = data.get("edges")
    if not isinstance(edges, list):
        emit_error("DIAGRAM_DATA.edges is missing or not an array.")
        edges = []
    else:
        seen_edges = set()
        for i, edge in enumerate(edges):
            if not isinstance(edge, dict):
                emit_error(f"edges[{i}] is not an object.")
                continue
            src = edge.get("sourceId")
            tgt = edge.get("targetId")
            elabel = edge.get("label")

            if not src or not isinstance(src, str) or src not in node_ids:
                emit_error(f'Edge "{elabel or i}" has dangling or missing sourceId "{src}".')
            else:
                incident_edge_count[src] = incident_edge_count.get(src, 0) + 1

            if not tgt or not isinstance(tgt, str) or tgt not in node_ids:
                emit_error(f'Edge "{elabel or i}" has dangling or missing targetId "{tgt}".')
            else:
                incident_edge_count[tgt] = incident_edge_count.get(tgt, 0) + 1

            if not elabel or not isinstance(elabel, str) or not elabel.strip():
                emit_error(f'Edge at index {i} is missing a valid "label" (non-empty string).')

            evidence = edge.get("evidence")
            if not evidence or not isinstance(evidence, str) or not evidence.strip():
                emit_error(f'Edge "{elabel or i}" is missing "evidence".')
            else:
                eq = evidence_quality(evidence)
                if eq:
                    emit_warning(f'Edge "{elabel or i}" evidence "{evidence}" has {eq}.')

            confidence = edge.get("confidence")
            if not confidence or confidence not in VALID_CONFIDENCE:
                emit_error(f'Edge "{elabel or i}" has invalid confidence "{confidence}".')

            edge_key = (src, tgt, elabel)
            if edge_key in seen_edges:
                emit_warning(f'Duplicate edge: {src} -> {tgt} label="{elabel}".')
            seen_edges.add(edge_key)

    # clusters
    clusters = data.get("clusters")
    cluster_membership = {}
    if isinstance(clusters, list):
        for cluster in clusters:
            if not isinstance(cluster, dict):
                emit_error(f"clusters has a non-object entry.")
                continue
            cid = cluster.get("id") or cluster.get("label")
            if not cid:
                emit_warning(f"Cluster has no id or label.")
            for nid in (cluster.get("nodeIds") or []):
                cluster_membership.setdefault(nid, []).append(cid or "?")
                if nid not in node_ids:
                    emit_error(f'Cluster "{cid or "?"}" references missing node "{nid}".')
            layout_val = cluster.get("layout")
            if layout_val is not None and layout_val not in ("vertical", "circular"):
                emit_error(f'Cluster "{cid or "?"}" has invalid layout "{layout_val}". Valid values: {", ".join(sorted(VALID_CLUSTER_LAYOUTS))}, or absent.')

    # cross-cluster node error
    for nid, members in cluster_membership.items():
        if len(members) > 1:
            emit_error(f'Node "{nid}" belongs to {len(members)} clusters: {", ".join(members)}.'
                       f' A node can only belong to one cluster.')

    # orphaned node warning (no incident edges, no cluster)
    for nid in node_ids:
        in_cluster = nid in cluster_membership
        has_edges = incident_edge_count.get(nid, 0) > 0
        if not has_edges and not in_cluster:
            emit_warning(f'Node "{nid}" has no incident edges and belongs to no cluster — it may be orphaned.')

    # cluster-edge skip check
    check_cluster_edge_skips(data, emit_error)

    # intra-cluster node-skip check
    check_intra_cluster_node_skips(data, emit_error)

    # label overlap and edge length checks
    check_edge_label_overlaps(data, emit_error)

    # walkthrough
    walkthrough = data.get("walkthrough")
    if isinstance(walkthrough, list):
        wt_ids = set()
        for i, step in enumerate(walkthrough):
            if not isinstance(step, dict):
                emit_error(f"walkthrough[{i}] is not an object.")
                continue
            sid = step.get("id")
            if not sid or not isinstance(sid, str):
                emit_error(f"walkthrough[{i}] is missing a valid 'id' (non-empty string).")
            if sid in wt_ids:
                emit_error(f'Duplicate walkthrough step id "{sid}".')
            wt_ids.add(sid)

            stitle = step.get("title")
            if not stitle or not isinstance(stitle, str) or not stitle.strip():
                emit_error(f'Walkthrough step "{sid or i}" is missing a valid "title".')

            s_nodes = step.get("nodeIds")
            if not isinstance(s_nodes, list) or len(s_nodes) == 0:
                emit_error(f'Walkthrough step "{sid or i}" has no nodeIds.')
            else:
                for nid in s_nodes:
                    if nid not in node_ids:
                        emit_error(f'Walkthrough step "{sid or i}" references missing node "{nid}".')

                # dead-end walkthrough step: no edges between step's nodes
                wn = set(s_nodes)
                visible = sum(
                    1 for e in edges
                    if isinstance(e, dict) and e.get("sourceId") in wn and e.get("targetId") in wn
                )
                if len(s_nodes) >= 2 and visible == 0:
                    emit_warning(f'Walkthrough step "{sid or i}" has no edges connecting its nodes.'
                                 f' Users may see dimmed nodes with no relationships to follow.')

    # metadata checks
    if metadata:
        for field in ("audience", "purpose", "fidelity"):
            dv = data.get(field)
            mv = metadata.get(field)
            if dv and mv and dv != mv:
                emit_error(f"#agent-metadata.{field} ('{mv}') does not match DIAGRAM_DATA.{field} ('{dv}').")

        meta_entities = metadata.get("entities") or []
        meta_entity_ids = set()
        for i, entity in enumerate(meta_entities):
            eid = entity.get("id")
            if not eid:
                emit_error(f"metadata entities[{i}] is missing an 'id'.")
                continue
            meta_entity_ids.add(eid)
            if eid not in node_ids:
                emit_error(f"metadata entity '{eid}' has no matching DIAGRAM_DATA node.")
            else:
                entity_name = entity.get("name")
                if entity_name and node_labels.get(eid) and entity_name != node_labels[eid]:
                    emit_warning(f'metadata entity "{eid}" name "{entity_name}"'
                                 f' differs from DIAGRAM_DATA node label "{node_labels[eid]}".')
                entity_type = resolve_type(entity.get("type", ""))
                if entity_type and node_types_map.get(eid) and entity_type != node_types_map[eid]:
                    emit_error(f'metadata entity "{eid}" type "{entity_type}"'
                               f' differs from DIAGRAM_DATA node type "{node_types_map[eid]}".')

        for nid in node_ids:
            if nid not in meta_entity_ids:
                emit_error(f"DIAGRAM_DATA node '{nid}' is missing from #agent-metadata entities.")

        meta_relationships = metadata.get("relationships") or []
        for i, rel in enumerate(meta_relationships):
            rsrc = rel.get("sourceId")
            rtgt = rel.get("targetId")
            rlabel = rel.get("label", "unlabeled")
            if not rlabel or not isinstance(rlabel, str):
                emit_error(f"metadata relationships[{i}] is missing 'label'.")
            if rsrc and rsrc not in node_ids:
                emit_error(f"metadata relationship '{rlabel}' has dangling source '{rsrc}'.")
            if rtgt and rtgt not in node_ids:
                emit_error(f"metadata relationship '{rlabel}' has dangling target '{rtgt}'.")
            rconf = rel.get("confidence")
            if rconf and rconf not in VALID_CONFIDENCE:
                emit_error(f"metadata relationship '{rlabel}' has invalid confidence '{rconf}'.")
            revidence = rel.get("evidence")
            if not revidence:
                emit_error(f"metadata relationship '{rlabel}' is missing 'evidence'.")
            else:
                eq = evidence_quality(revidence)
                if eq:
                    emit_warning(f'metadata relationship "{rlabel}" evidence "{revidence}" has {eq}.')

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_diagram.py <path-to-diagram.html>", file=sys.stderr)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    if not html_path.exists():
        fail(f"File not found: {html_path}")
        sys.exit(1)

    # Protect template from direct overwrite
    if TEMPLATE_PATH.exists() and html_path.resolve() == TEMPLATE_PATH.resolve():
        fail(f"Output path is the template file itself ({TEMPLATE_PATH}). Save to a different file.")
        sys.exit(1)

    text = html_path.read_text(encoding="utf-8")

    # Structural completeness
    struct_issues = check_structural_completeness(text)
    for issue in struct_issues:
        fail(issue)
    if struct_issues:
        sys.exit(1)

    # Template integrity (SHA against canonical template)
    if TEMPLATE_PATH.exists():
        integ_issues = check_template_integrity(html_path)
        for issue in integ_issues:
            fail(issue)
        if integ_issues:
            sys.exit(1)

    # Extract raw DIAGRAM_DATA block for pre-checks
    raw_block = extract_raw_js_block(text, "DIAGRAM_DATA")
    if raw_block is None:
        fail("Could not find 'const DIAGRAM_DATA =' in file.")
        sys.exit(1)

    # Pre-scan for dangerous JS syntax (only within the block)
    dangerous = check_dangerous_js(raw_block)
    if dangerous:
        for line, desc in dangerous:
            fail(f"DIAGRAM_DATA line {line}: {desc}. The parser cannot handle this syntax.")
        sys.exit(1)

    # Pre-scan for unescaped braces inside strings
    brace_issues = check_braces_in_strings(raw_block)
    if brace_issues:
        for line, content in brace_issues:
            fail(f'DIAGRAM_DATA line ~{line}: literal brace characters inside string value:'
                 f' "{content[:60]}...". The JS parser cannot distinguish structural'
                 f' braces from literal ones.')
        sys.exit(1)

    # Convert to JSON and parse
    json_str = js_obj_to_json(raw_block)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        fail(f"Could not parse DIAGRAM_DATA JSON: {e}")
        sys.exit(1)

    metadata = extract_agent_metadata(text)

    errors, warnings = validate(data, metadata)

    if errors:
        print(f"\n{errors} error(s), {warnings} warning(s) found.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Valid — 0 errors, {warnings} warning(s).")
        sys.exit(0)


if __name__ == "__main__":
    main()
