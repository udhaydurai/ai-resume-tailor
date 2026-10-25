#!/usr/bin/env python3
"""PreToolUse: Claude may not weaken its own guardrails. A human edits these files.

Only paths inside this repo are guarded, and reading a guardrail file is always fine.
Exit 2 blocks the call; stderr is shown to Claude.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()

GUARDRAILS = (
    r"\.claude/settings(\.local)?\.json|\.claude/privacy\.local\.json|"
    r"\.claude/hooks(/|$|\s)|\.claude/agents(/|$|\s)|"
    r"scripts/scan_repo\.py|scripts/validate_review\.py|"
    r"docs/review/finding\.schema\.json|"
    r"\.github/workflows(/|$|\s)|\.pre-commit-config\.yaml|\.gitignore|\.gitleaks\.toml"
)
PROTECTED = re.compile(r"(^|/)(" + GUARDRAILS + r")")
IN_COMMAND = re.compile(r"(^|[\s/\"'=<>])(" + GUARDRAILS + r")")
BYPASS = re.compile(
    r"--no-verify|\bSKIP=|PRE_COMMIT_ALLOW_NO_CONFIG|disableAllHooks|core\.hooksPath|"
    r"git\s+push\b[^;&|]*\s(--force\S*|-f)(\s|$)|git\s+push\b[^;&|]*\s\+\S"
)
HARMLESS_REDIRECT = re.compile(r"\d?>&\d|\d?>\s*/dev/null")
CHANGES_FILES = re.compile(
    r">|\b(tee|truncate|rm|mv|cp|ln|chmod|chown|install|dd|rsync|unlink|touch|mkdir)\b|"
    r"sed\s+-i|perl\s+-[a-z]*i|awk\s+-i|"
    r"\b(python3?|node|ruby|perl)\s+(-\w*[ce]\b|-\s|-$|<<)|\b(bash|sh|zsh)\s+-c\b|"
    r"git\s+(checkout|restore|rm|mv|apply|stash|reset|clean|update-index)\b"
)


def guarded(path: str) -> bool:
    full = Path(path) if Path(path).is_absolute() else ROOT / path
    real = Path(os.path.realpath(full))
    for candidate in {full, real}:
        try:
            rel = candidate.relative_to(ROOT)
        except ValueError:
            continue
        if PROTECTED.search(str(rel)):
            return True
    return False


def decide(tool: str, tool_input: dict[str, object]) -> str | None:
    if tool in {"Edit", "Write", "NotebookEdit"}:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if path and guarded(path):
            return (
                f"{path} is a guardrail file. Only a human changes it. Explain the change and stop."
            )
        return None
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        if BYPASS.search(command):
            return "Bypassing hooks, disabling them, or force-pushing is not allowed."
        writes = CHANGES_FILES.search(HARMLESS_REDIRECT.sub("", command))
        if writes and IN_COMMAND.search(command.replace(str(ROOT) + "/", "")):
            return "That command could change a guardrail file. Only a human changes those."
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        print("Blocked: hook input was not JSON.", file=sys.stderr)
        return 2
    reason = decide(str(data.get("tool_name", "")), data.get("tool_input") or {})
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
