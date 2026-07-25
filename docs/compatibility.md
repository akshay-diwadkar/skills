# Platform Compatibility Matrix

This document provides platform details regarding discovery mechanisms, skill support, and compatibility testing.

---

## 1. Compatibility Summary Table

| Platform | Skills Distributed | Manifest / Location | Discovery & Installation Mechanism | Status |
| --- | --- | --- | --- | --- |
| **skills.sh** | Yes (`skills/engineering/`) | Canonical `skills/*/*/SKILL.md` | `npx skills add akshay-diwadkar/skills` | **Supported** (Skills CLI) |
| **Manual / Symlink** | Yes (`skills/engineering/`) | Canonical `skills/*/*/SKILL.md` | Symlink into agent skills directory | **Supported** (Manual) |

---

## 2. Platform Details

### skills.sh

- **Discovery Mechanism**: Inspects canonical `skills/<domain>/<skill>/SKILL.md` paths.
- **Skills Support**: Full support for all individual skills.
- **Testing**: Validated by `tools/validation/validate_repository.py`.

---

## 3. Automated Repository Validation vs. Native Host Verification

Automated CI checks prove repository contract compliance, link integrity, and installed-runtime execution. Maintainers execute manual verification before releasing major versions.

---

## 4. Breaking Changes Policy

The following changes require a major version bump in `VERSION`:
- Renaming or removing a stable skill.
- Modifying a canonical skill path.
- Restricting invocation permissions (e.g. changing `both` to `user`).
