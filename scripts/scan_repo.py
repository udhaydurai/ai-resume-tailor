"""Fail if the repo (or the files given) holds real personal data or private files.

Reports file:line and the kind of problem, never the matched text, so the scan itself
does not copy personal data into logs.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

DOC_EXTS = {"doc", "docx", "pdf", "pages", "rtf"}
DATA_EXTS = {"db", "sqlite", "sqlite3", "csv", "xls", "xlsx", "vcf", "json-backup"}
SAFE_DOC_DIRS = ("demo/", "tests/fixtures/")
SKIP = {"uv.lock"}
SAFE_EMAIL_DOMAINS = re.compile(
    r"(^|\.)(example\.(com|org|net)|[\w-]+\.(test|example|invalid)|"
    r"users\.noreply\.github\.com)$",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(\.[\w-]+)+)")
PHONE = re.compile(r"(?<![\w-])(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w-])")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def name_problem(path: str) -> str | None:
    name = Path(path).name
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "secrets file"
    if ext in DATA_EXTS:
        return "data file (tracker or contact export)"
    if ext in DOC_EXTS and not path.startswith(SAFE_DOC_DIRS):
        return "resume document outside demo/ or tests/fixtures/"
    if path.startswith("private/"):
        return "file in private/"
    return None


def safe_phone(match: str) -> bool:
    digits = re.sub(r"\D", "", match)[-10:]
    return digits[3:6] == "555" and digits[6:8] == "01"


def content_problems(path: str, text: str) -> list[str]:
    problems = []
    for number, line in enumerate(text.splitlines(), start=1):
        for m in EMAIL.finditer(line):
            if not SAFE_EMAIL_DOMAINS.search(m.group(1)):
                problems.append(f"{path}:{number}: real-looking email (use @example.test)")
        for m in PHONE.finditer(line):
            if not safe_phone(m.group(0)):
                problems.append(f"{path}:{number}: real-looking phone (use 555-01xx)")
    return problems


def scan(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if path in SKIP:
            continue
        kind = name_problem(path)
        if kind:
            problems.append(f"{path}: {kind}")
            continue
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        problems.extend(content_problems(path, text))
    return problems


def main(argv: list[str]) -> int:
    problems = scan(argv or tracked_files())
    for problem in problems:
        print(problem)
    if problems:
        print(f"scan_repo: {len(problems)} problem(s). See docs/PRIVACY.md.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
