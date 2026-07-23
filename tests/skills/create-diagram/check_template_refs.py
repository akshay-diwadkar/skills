"""Check that the template's JavaScript has no dangling function references.

Usage:
    python check_template_refs.py [--template <path>]

Exits 0 if all function call references resolve to a definition in the template.
Exits 1 if dangling references are found.
"""

import re
import sys
from pathlib import Path


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
DEFAULT_TEMPLATE = REPO_ROOT / "skills" / "engineering" / "create-diagram" / "assets" / "html-diagram-template.html"


# JS built-ins, DOM APIs, globals, and Node.js/runtime names that are
# always available and should not trigger dangling-reference warnings.
EXTERNAL_ALLOWLIST = frozenset({
    # DOM methods
    "getElementById", "querySelector", "querySelectorAll", "createElementNS",
    "createElement", "addEventListener", "removeEventListener",
    "getBoundingClientRect", "setAttribute", "getAttribute", "removeAttribute",
    "classList", "toggle", "add", "remove", "contains",
    "appendChild", "removeChild", "replaceChild", "insertBefore",
    "closest", "matches", "setTimeout", "setInterval", "clearTimeout",
    "requestAnimationFrame", "cancelAnimationFrame", "localStorage",
    "getItem", "setItem", "removeItem", "parse", "stringify",
    "console", "log", "warn", "error", "info",
    # Math / Number
    "max", "min", "abs", "sqrt", "floor", "ceil", "round", "pow",
    "atan2", "cos", "sin", "PI", "random",
    "isNaN", "parseInt", "parseFloat", "Number", "isFinite",
    # Array / Object / String
    "push", "pop", "shift", "unshift", "splice", "slice", "indexOf",
    "includes", "find", "findIndex", "filter", "map", "reduce", "forEach",
    "some", "every", "sort", "reverse", "join", "concat", "flat",
    "keys", "values", "entries", "assign", "create", "defineProperty",
    "hasOwnProperty", "toString", "valueOf",
    "startsWith", "endsWith", "trim", "split", "match", "replace", "search",
    "charCodeAt", "charAt", "toLowerCase", "toUpperCase", "substring",
    "replaceAll", "length",
    # Built-in constructors
    "Set", "Map", "WeakSet", "WeakMap", "Array", "Object", "String",
    "Number", "Boolean", "Date", "RegExp", "Error", "Promise",
    "Float32Array", "Float64Array", "Int32Array", "Uint32Array",
    # JS keywords and operators used with ( )
    "if", "else if", "for", "while", "do", "switch", "catch", "typeof",
    "instanceof", "delete", "void", "return", "throw", "new", "in",
    "of", "function", "class", "extends", "import", "export", "default",
    "from", "as", "async", "await", "yield", "super", "this",
    # Template-specific constants (accessed as functions indirectly)
    "CLUSTER_PAD", "CLUSTER_LABEL_H", "CLUSTER_GAP_X", "CLUSTER_INTRUSION_GAP",
    "COLLISION_GAP", "NODE_GAP_Y", "NODE_W", "NODE_H", "NODE_H_DESC",
    "CIRCULAR_RADIUS_FACTOR", "CIRCULAR_MIN_RADIUS", "MIN_READABLE_SCALE",
    "EDGE_END_PAD", "EDGE_MIN_SEPARATION", "EDGE_LAYOUT_STEP",
    "EDGE_LAYOUT_LIMIT", "EDGE_LAYOUT_PASSES",
    "TITLE_FONT_SIZE", "DESCRIPTION_FONT_SIZE", "MAX_DESC_CHARS", "MAX_DESC_LINES",
    "VERSION",
    # False positives - names inside string literals or comments
    "rgba", "shadow", "first", "place",
    "stage", "tier", "edges", "nodes", "files",
    # SVG attribute helpers (inside template literal strings)
    "translate", "scale", "rotate", "matrix",
    # RoughJS
    "rough", "svg",
    # DIAGRAM_DATA access
    "DIAGRAM_DATA",
    # State and DOM element access
    "state", "el", "rc", "canvas", "dragState", "nodeMap",
    "currentTheme", "NODE_TYPES",
    # Template functions (self-references caught by the checker)
    "THEMES", "TYPE_ALIASES", "VALID_CONFIDENCE",
})


# Names commonly used as function arguments (callbacks, predicates) that
# may appear as "name(" in source but are not external APIs.
# These are passed as arguments to higher-order functions.
KNOWN_CALLBACKS = frozenset({
    "node", "edge", "cluster", "n", "e", "c", "item", "el", "g", "d",
    "row", "layout", "a", "b", "id", "key", "val", "result", "value",
    "index", "i", "j", "k", "li", "id", "t", "ch", "point", "src",
    "tgt", "other", "member", "candidate", "existing", "nodeIds",
    "srcLabel", "tgtLabel", "parts", "confLabel", "confMap",
    "from", "to", "box", "nBox", "aBox", "bBox", "cBox", "def",
    "opt", "arg", "step", "nodeId", "stepNodeIds", "set", "focusIds",
    "connected", "unconnected", "prevIdx", "bc", "ordered",
    "placed", "types", "type", "usedTypes", "swatch", "label",
    "incident", "content", "start", "end", "control", "route",
})


# Names that appear as NAME( in source but are actually variable references
# passed as callbacks (not function calls). We skip these entirely.
CALLBACK_VARIABLES = frozenset(KNOWN_CALLBACKS)


def extract_function_defs(text):
    """Return set of all function names defined in the JS code."""
    defs = set()

    # function name( ... ) { ... }
    for m in re.finditer(r'(?:^|\s)(?:async\s+)?function\s+(\w+)\s*\(', text, re.MULTILINE):
        defs.add(m.group(1))

    # name = function( ... ) { ... }
    for m in re.finditer(r'(\w+)\s*[:=]\s*(?:async\s+)?function\s*\(', text):
        defs.add(m.group(1))

    # name = ( ... ) => { ... }   or   name = arg => { ... }
    for m in re.finditer(r'(\w+)\s*[:=]\s*(?:\([^)]*\)|\w+)\s*=>\s*', text):
        defs.add(m.group(1))

    return defs


def extract_function_calls(text):
    """Return set of all names used as function calls: name(."""
    calls = set()
    for m in re.finditer(r'(?<![.\w$])(\w+)\s*\(', text):
        calls.add(m.group(1))
    return calls


def check_template(template_path):
    """Check the template JS for dangling function references.

    Returns list of (reference_name, line_number) tuples for references
    that don't resolve to a defined function.
    """
    text = template_path.read_text(encoding="utf-8")

    # Extract <script> blocks (both inline and module)
    script_pattern = re.compile(
        r'<script[^>]*>([\s\S]*?)</script>', re.IGNORECASE,
    )
    blocks = script_pattern.findall(text)
    if not blocks:
        return ["No <script> blocks found in template."]

    all_defs = set()
    all_calls = {}

    for block in blocks:
        block_defs = extract_function_defs(block)
        all_defs.update(block_defs)

        # Track calls with line numbers
        for lineno, line in enumerate(block.splitlines(), 1):
            for m in re.finditer(r'(?<![.\w$])(\w+)\s*\(', line):
                name = m.group(1)
                if name not in all_calls:
                    all_calls[name] = []
                all_calls[name].append(lineno)

    # Consider all definitions as valid references
    all_defs.add("init")  # init() is the entry point, not defined as 'function init' in module scripts
    # Actually, init is defined as function init() - will be caught by the regex above.
    # But the DIAGRAM_DATA walkthrough uses `.forEach`, `.filter`, etc. which are in the allowlist.

    issues = []
    for name, lines in sorted(all_calls.items()):
        if name in EXTERNAL_ALLOWLIST:
            continue
        if name in CALLBACK_VARIABLES:
            continue
        if name in all_defs:
            continue
        # Skip single-letter names (typically arg destructuring or loop vars)
        if len(name) <= 1:
            continue
        # Skip names that are clearly object property accesses used as methods
        # (these have a . before them in the original source, but the regex
        # won't match those - we look for (?<![.\w$]) prefix)
        issues.append(f'  "{name}" used on line(s) {", ".join(map(str, lines[:5]))}'
                      f'{"..." if len(lines) > 5 else ""}')

    return issues


def main():
    template_path = DEFAULT_TEMPLATE
    if len(sys.argv) > 2:
        print("Usage: python check_template_refs.py [--template <path>]", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) == 2:
        template_path = Path(sys.argv[1])
        if not template_path.exists():
            print(f"File not found: {template_path}", file=sys.stderr)
            sys.exit(1)

    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    issues = check_template(template_path)

    if issues:
        print(f"ERROR: {len(issues)} dangling function reference(s) found:")
        for issue in issues:
            print(issue)
        print("\nAdd the function definition or add the name to EXTERNAL_ALLOWLIST")
        print("in tests/create-diagram/check_template_refs.py if it's a valid external reference.")
        sys.exit(1)
    else:
        print("OK - all function references resolve to definitions.")
        sys.exit(0)


if __name__ == "__main__":
    main()
