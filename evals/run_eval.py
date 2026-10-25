"""Live truthfulness eval: how many facts do the generators invent?

Calls the real Claude API (needs ANTHROPIC_API_KEY). Uses the same model and effort
settings as the app, so `RESUME_TAILOR_MODEL=... make eval` compares models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from src import ai_engine  # noqa: E402
from src.truthcheck import unsupported_numbers, unsupported_terms  # noqa: E402

CASES = Path(__file__).with_name("cases.json")
PROFILE_KEYS = ("name", "email", "phone")


def profile_from(resume: str) -> dict[str, str]:
    parts = [p.strip() for p in resume.splitlines()[0].split("|")]
    return dict(zip(PROFILE_KEYS, parts, strict=False))


def score(case: dict[str, Any]) -> list[tuple[str, str, list[str]]]:
    resume, job = str(case["resume"]), str(case["job"])
    terms = [str(t) for t in case.get("forbidden_terms", [])]
    profile = profile_from(resume)
    rows = []
    for kind, generate in (
        ("resume", ai_engine.generate_tailored_resume),
        ("cover letter", ai_engine.generate_cover_letter),
    ):
        text = generate(job, resume, profile)
        invented = unsupported_numbers(resume, text) + unsupported_terms(resume, text, terms)
        rows.append((str(case["id"]), kind, invented))
    return rows


def main() -> int:
    load_dotenv()
    cases = json.loads(CASES.read_text())
    print(f"model={ai_engine.model()} effort={ai_engine.effort()} cases={len(cases)}\n")
    print("| case | output | invented |")
    print("|---|---|---|")
    total = 0
    for case in cases:
        for case_id, kind, invented in score(case):
            total += len(invented)
            print(f"| {case_id} | {kind} | {', '.join(invented) or '-'} |")
    print(f"\nInvented facts: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
