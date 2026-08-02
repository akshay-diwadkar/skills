"""Independently executable generators for the legacy resolver smoke fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path


FILES = {
    "python-small": {
        "pyproject.toml": '[tool.pytest.ini_options]\naddopts = "-q"\n',
        "src/authentication.py": "class AuthenticationService:\n    def authenticate_user(self) -> bool:\n        return True\n",
        "src/backoff.py": "class BackoffPolicy:\n    def schedule_retry(self) -> int:\n        return 1\n",
        "src/options.py": "def load_options() -> dict[str, str]:\n    return {}\n",
        "src/search.py": "def search_records() -> list[str]:\n    return []\n",
        "tests/test_authentication.py": "from src.authentication import AuthenticationService\n\ndef test_login_acceptance() -> None:\n    assert AuthenticationService().authenticate_user()\n",
        "tests/test_backoff.py": "from src.backoff import BackoffPolicy\n\ndef test_retry_schedule() -> None:\n    assert BackoffPolicy().schedule_retry() == 1\n",
    },
    "javascript-small": {
        "package.json": '{"scripts":{"test":"node --test","lint":"eslint .","build":"tsc"}}\n',
        "src/authentication.js": "export function authenticateUser() { return true; }\n",
        "src/backoff.js": "export class BackoffPolicy { scheduleRetry() { return 1; } }\n",
        "src/options.js": "export const loadOptions = () => ({});\n",
        "src/search.js": "export function searchRecords() { return []; }\n",
        "test/authentication.test.js": 'import { authenticateUser } from "../src/authentication.js";\nexport function testLoginAcceptance() { return authenticateUser(); }\n',
        "test/backoff.test.js": 'import { BackoffPolicy } from "../src/backoff.js";\nexport function testRetrySchedule() { return new BackoffPolicy().scheduleRetry() === 1; }\n',
    },
    "mixed-config": {
        "app/throttle.py": "class ThrottlePolicy:\n    def allow_request(self) -> bool:\n        return True\n",
        "lib/authorization.go": "package lib\n\nfunc AuthorizeUser() bool { return true }\n",
        "settings.yaml": "rate_limits:\n  requests_per_minute: 60\n",
        "web/encoding.js": "export function encodePayload(value) { return JSON.stringify(value); }\n",
        "tests/test_throttle.py": "from app.throttle import ThrottlePolicy\n\ndef test_rate_limit() -> None:\n    assert ThrottlePolicy().allow_request()\n",
        "test/encoding.test.js": 'import { encodePayload } from "../web/encoding.js";\nexport function testSerialization() { return encodePayload({ ok: true }) === \'{"ok":true}\'; }\n',
        "tsconfig.json": '{"compilerOptions":{"strict":true}}\n',
    },
}


def generate(fixture_id: str, output: Path) -> None:
    if fixture_id not in FILES:
        raise ValueError(f"unknown smoke fixture: {fixture_id}")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"fixture output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for relative, content in FILES[fixture_id].items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", choices=sorted(FILES))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    generate(args.fixture, args.output)
