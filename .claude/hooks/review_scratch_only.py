#!/usr/bin/env python3
"""Per-agent PreToolUse hook for the judge: it may write only proof files under .review/."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()


def main() -> int:
    try:
        tool_input = json.load(sys.stdin).get("tool_input") or {}
    except ValueError:
        return 2
    raw = str(tool_input.get("file_path") or "")
    path = Path(os.path.realpath(raw if Path(raw).is_absolute() else ROOT / raw))
    if (ROOT / ".review") in path.parents:
        return 0
    print(f"The judge may write only under .review/ (proof tests). Got: {raw}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
