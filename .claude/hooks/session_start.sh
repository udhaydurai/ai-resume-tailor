#!/usr/bin/env bash
# SessionStart: give Claude the current position in one glance.
cd "$CLAUDE_PROJECT_DIR" || exit 0
mode=$(python3 -c 'import json; print(json.load(open(".claude/privacy.local.json")).get("mode","strict"))' 2>/dev/null || echo strict)
[ "$mode" = "open" ] || mode=strict
echo "Branch: $(git branch --show-current)"
echo "Next roadmap slice: $(grep -m1 -E '^- \[ \] [0-9]' docs/ROADMAP.md | sed 's/^- \[ \] //')"
echo "Privacy mode: $mode (docs/PRIVACY.md)"
echo "Uncommitted files: $(git status --porcelain | wc -l | tr -d ' ')"
exit 0
