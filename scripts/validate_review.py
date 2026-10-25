"""Check review-panel reports against docs/review/finding.schema.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parent.parent / "docs" / "review" / "finding.schema.json"


def errors_for(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return [f"{path}: not readable JSON ({exc})"]
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    return [
        f"{path}: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
        for e in validator.iter_errors(report)
    ]


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or sorted(Path(".review").glob("*.json"))
    if not paths:
        print("validate_review: no reports found in .review/")
        return 1
    errors = [e for p in paths for e in errors_for(p)]
    for error in errors:
        print(error)
    if not errors:
        print(f"validate_review: {len(paths)} report(s) valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
