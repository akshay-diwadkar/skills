# Platform Compatibility

## Supported Platforms

- **skills.sh**: Discovered automatically from canonical `skills/*/*/SKILL.md` paths.
- **Claude Plugin**: Registered via `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- **Cursor Plugin**: Registered via `.cursor-plugin/plugin.json` and `.cursor-plugin/marketplace.json`.
- **Codex / OpenAI**: Configured via `.codex/config.toml`, `.codex/agents/*.toml`, canonical skill paths, and optional `agents/openai.yaml`.

## Breaking Changes Policy

The following are breaking changes requiring major version bumps:
- Renaming or deleting a stable skill.
- Modifying a skill path after publication.
- Changing invocation from `model` or `both` to `user`.
- Modifying required output contracts or removing bundled scripts.
