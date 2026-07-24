# Platform Manifest Validation Schemas

This directory contains **Repository Policy Schemas** for platform manifests used across supported AI coding environments.

## Schema Classification & Provenance

The JSON schemas in this directory (`claude_plugin_schema.json`, `claude_marketplace_schema.json`, `cursor_plugin_schema.json`, `cursor_marketplace_schema.json`) are **stricter repository policy schemas**, not raw upstream vendor schemas.

### Purpose

1. **Platform Compatibility**: Ensure platform-specific manifests follow required field formats, relative paths (`./`), and structural types expected by host environments (Claude Code, Cursor).
2. **Repository Quality Standards**: Enforce mandatory metadata fields (such as `author`, `publisher`, `license`, `version`, `skills`, `agents`, `owner`) required for production release quality in this repository.

### Provenance & Policy Rules

- **Claude Plugin (`claude_plugin_schema.json`)**: Enforces required `author.name`, `license`, `skills` array, and `agents` directory path. Rejects deprecated or invalid fields (e.g. `publisher`).
- **Claude Marketplace (`claude_marketplace_schema.json`)**: Enforces required `owner.name`, `plugins` array with `name`, `version`, `description`, `source`.
- **Cursor Plugin (`cursor_plugin_schema.json`)**: Enforces `name`, `displayName`, `version`, `description`, `publisher`, `license`, `skills`, `agents`.
- **Cursor Marketplace (`cursor_marketplace_schema.json`)**: Enforces `owner.name`, `plugins` list with `name`, `description`, `source`. Rejects unsupported `version` field inside plugin items per Cursor's marketplace spec.
