#!/usr/bin/env bash
# PostToolUse: keep every edited Python file formatted and auto-fixed. Never blocks.
path=$(python3 -c 'import json,sys; d=(json.load(sys.stdin).get("tool_input") or {}); print(d.get("file_path",""))')
case "$path" in
  *.py) cd "$CLAUDE_PROJECT_DIR" && uv run --quiet ruff format --quiet "$path" && uv run --quiet ruff check --fix --quiet "$path" ;;
esac
exit 0
