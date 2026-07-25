# Integration Guide for AI Agents & Workflow Skills

## 1. Read-Only Skills Integration (Planning / Auditing / Design)
1. Check knowledge freshness via `build-codebase-knowledge status`.
2. Read `context.md` for high-level repository map.
3. Run resolver: `python scripts/resolve_task.py --repo-root . --task "<task>" --format json`.
4. Read only the top-ranked candidates specified in `candidates` and `read_order`.
5. Verify details directly in target source files.

## 2. Write Skills Integration (Implementation / Refactoring)
1. Pre-execution: Run resolver to obtain read slice.
2. Implementation: Modify files as required by task.
3. Post-execution: Call incremental refresh:
   ```bash
   python scripts/refresh_knowledge.py --repo-root . --changed-file path/to/file1.py --changed-file path/to/file2.py
   ```
4. Verify refresh state reports `fresh`.
