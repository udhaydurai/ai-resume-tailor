#!/usr/bin/env python3
"""Per-agent PreToolUse hook for reviewers and the judge: Bash may read and run tests only."""

from __future__ import annotations

import json
import re
import sys

HARMLESS_REDIRECT = re.compile(r"\d?>&\d|\d?>\s*/dev/null")
MUTATES = re.compile(
    r"(^|[;&|(\s])(rm|mv|cp|mkdir|touch|chmod|chown|tee|truncate|dd|ln|install|rsync|"
    r"brew|npm|pnpm|pip|pip3|curl|wget|ssh|scp|open)(\s|$)|"
    r"uv\s+(add|remove|sync|pip|lock)|"
    r"git\s+(commit|push|checkout|switch|reset|rebase|merge|stash|add|rm|mv|restore|clean|"
    r"tag|cherry-pick|apply|config)|"
    r"gh\s+(pr|issue|release|repo|api)\s|"
    r"sed\s+-i|perl\s+-[a-z]*i|awk\s+-i|"
    r"\b(python3?|node|ruby|perl)\s+(-\w*[ce]\b|-\s|-$|<<)|\b(bash|sh|zsh)\s+-c\b|>"
)


def main() -> int:
    try:
        command = str((json.load(sys.stdin).get("tool_input") or {}).get("command", ""))
    except ValueError:
        return 2
    if MUTATES.search(HARMLESS_REDIRECT.sub("", command)):
        print(
            "Read-only reviewer: this command could change files, git, packages or the "
            "network. Run tests or read-only commands; write proof tests as text in your report.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
