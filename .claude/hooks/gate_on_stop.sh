#!/usr/bin/env bash
# Stop: Claude can't finish while changed code fails `make check-fast`.
active=$(python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())')
[ "$active" = "true" ] && exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
git status --porcelain | grep -Eq '\.(py|toml|lock)$|Makefile' || exit 0
if ! out=$(make check-fast 2>&1); then
  echo "make check-fast is failing. Fix it before finishing:" >&2
  printf '%s\n' "$out" | tail -40 >&2
  exit 2
fi
exit 0
