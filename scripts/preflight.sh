#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "${ROOT}" ]]; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

cd "${ROOT}"

TARGET="meal_calender_api"
if [[ ! -d "${TARGET}" ]]; then
  echo "Error: expected directory '${TARGET}' in repo root." >&2
  exit 1
fi

echo "[1/4] Ruff auto-fix"
uv run ruff check "${TARGET}" --fix

echo "[2/4] Ruff format"
uv run ruff format "${TARGET}"

echo "[3/4] Ruff final check"
uv run ruff check "${TARGET}"

echo "[4/4] Django system check"
uv run python "${TARGET}/manage.py" check

echo "Preflight checks passed."
