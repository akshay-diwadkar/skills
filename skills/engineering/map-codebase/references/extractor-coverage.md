# Extractor Coverage

Install `requirements.txt` before building knowledge. Missing tree-sitter
grammars fail with an actionable error. Tree-sitter extractors provide
scope-aware symbols, full-body ranges, and imports.

<!-- BEGIN EXTRACTOR COVERAGE -->
| Extractor | Inputs | Coverage |
| --- | --- | --- |
| `python.py` | Python | Full AST extraction |
| `javascript.py` | JavaScript, TypeScript, JSX, TSX | Full tree-sitter extraction |
| `lexical.py` | Go, Rust, Java, C, C++ | Full tree-sitter extraction |
| `csharp.py` | C# | Full tree-sitter extraction |
| `configuration.py` | Repository configuration | Structural metadata and commands |
<!-- END EXTRACTOR COVERAGE -->
