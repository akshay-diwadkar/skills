#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${1:-.env}"

if [[ ! -f "$ENV_PATH" ]]; then
  echo "Env file not found: $ENV_PATH" >&2
  return 2 2>/dev/null || exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

echo "Loaded GitHub environment variables from $ENV_PATH"
echo "Run: python scripts/check_github_env.py --env \"$ENV_PATH\""
