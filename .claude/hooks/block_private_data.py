#!/usr/bin/env python3
"""PreToolUse: keep real resumes, the job tracker database and secrets away from Claude.

Strict mode (the default) blocks all of them. A human can switch to open mode in
.claude/privacy.local.json (git-ignored, and Claude cannot edit it):

    {"mode": "open", "private_dirs": ["~/Documents/Personal/Resumes"]}

Open mode lets Claude read the private folders and resume files, and write drafts into
the repo's private/ folder. Secrets and the tracker database stay blocked in every mode,
and Bash can never touch private folders, so nothing private is copied or committed.
Only what a call touches is checked (paths, globs, commands), not the text it writes.
Exit 2 blocks the call; stderr is shown to Claude.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
CONFIG = ROOT / ".claude" / "privacy.local.json"
DEFAULT_PRIVATE_DIRS = ["~/Documents/Personal", "private"]
READ_TOOLS = {"Read", "Grep", "Glob"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
SAFE_DOC_DIRS = ("demo/", "tests/fixtures/")

SECRET = re.compile(r"(?<![\w.-])\.env(?![\w.-])|(?<![\w.-])\.env\.(?!example\b)[\w.-]+")
TRACKER_DATA = re.compile(r"\.(db|sqlite3?)(-wal|-shm|-journal)?(?!\w)", re.IGNORECASE)
RESUME_DOC = re.compile(r"\.(docx?|pdf|pages|rtf)(?!\w)", re.IGNORECASE)


def load_config() -> tuple[str, list[Path]]:
    try:
        data = json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    mode = "open" if data.get("mode") == "open" else "strict"
    extra = [d for d in data.get("private_dirs", []) if isinstance(d, str) and d.strip()]
    return mode, [absolute(d) for d in [*DEFAULT_PRIVATE_DIRS, *extra]]


def absolute(path: str, base: Path = ROOT) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(path)))
    full = expanded if expanded.is_absolute() else base / expanded
    return Path(os.path.realpath(full))


def spellings(folder: Path) -> list[str]:
    home = os.path.realpath(os.path.expanduser("~"))
    out = [str(folder)]
    if str(folder).startswith(home + "/"):
        rest = str(folder)[len(home) :]
        out += ["~" + rest, "$HOME" + rest, "${HOME}" + rest]
    return out


def glob_reaches(word: str, folder: Path, base: Path) -> bool:
    """`~/Documents/Pers*` or `~/Documents/*/x` can expand into the folder."""
    cut = min((word.index(c) for c in "*?[" if c in word), default=-1)
    if cut < 0:
        return False
    prefix = os.path.expandvars(os.path.expanduser(word[:cut]))
    prefix = prefix if prefix.startswith("/") else str(base) + "/" + prefix
    return str(folder).startswith(prefix) and len(prefix) > len(str(folder.parent))


def touched(tool: str, tool_input: dict[str, object]) -> list[str]:
    """Paths and globs this call names. Bash commands are split into words."""
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        try:
            return shlex.split(command)
        except ValueError:
            return command.split()
    keys = ("file_path", "notebook_path", "path", "pattern", "glob")
    return [str(tool_input[k]) for k in keys if tool_input.get(k)]


def under(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def word_paths(words: list[str], private_dirs: list[Path]) -> list[Path]:
    """Resolve each word that may be a path, following `cd`/`pushd` like the shell would."""
    names = {d.name for d in private_dirs}
    base = ROOT
    out: list[Path] = []
    for i, word in enumerate(words):
        pieces = {word, *re.split(r"[=<>:]", word)}
        for piece in pieces:
            if piece and ("/" in piece or piece.startswith((".", "~", "$")) or piece in names):
                out.append(absolute(piece, base))
            if any(glob_reaches(piece, d, base) for d in private_dirs):
                out.extend(private_dirs)
        if i and words[i - 1] in {"cd", "pushd"}:
            base = absolute(word, base)
    return out


def relative_doc(word: str) -> bool:
    path = absolute(word)
    rel = str(path.relative_to(ROOT)) + "/" if under(path, ROOT) else str(path)
    return rel.startswith(SAFE_DOC_DIRS)


def decide(tool: str, tool_input: dict[str, object]) -> str | None:
    words = touched(tool, tool_input)
    if not words:
        return None
    mode, private_dirs = load_config()
    joined = " ".join(words)

    if SECRET.search(joined):
        return "Blocked: .env holds secrets. Ask the human to edit it."
    if TRACKER_DATA.search(joined):
        return "Blocked: the job tracker database holds personal data. Use the app to view it."

    paths = word_paths(words, private_dirs)
    spelled = any(s in joined for d in private_dirs for s in spellings(d))
    if spelled or any(under(p, d) for p in paths for d in private_dirs):
        if tool == "Bash":
            return "Blocked: Bash may not touch private folders in any mode."
        if mode == "open" and tool in READ_TOOLS:
            return None
        drafts = ROOT / "private"
        if mode == "open" and tool in WRITE_TOOLS and all(under(p, drafts) for p in paths):
            return None
        return (
            "Blocked: this is a private folder (strict privacy mode). Upload resumes through "
            "the app, or ask the human to switch to open mode (docs/PRIVACY.md)."
        )

    docs = [w for w in words if RESUME_DOC.search(w)]
    if docs and not all(relative_doc(w) for w in docs):
        if mode == "open" and tool in READ_TOOLS:
            return None
        return (
            "Blocked: resume documents outside demo/ and tests/fixtures/ are private "
            "(strict privacy mode). See docs/PRIVACY.md."
        )
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
