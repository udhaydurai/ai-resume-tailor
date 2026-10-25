"""Tests for the repo scanner and the review-report validator."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("SCRIPTS_DIR", REPO / "scripts"))


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan_repo = load("scan_repo")
validate_review = load("validate_review")


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "job_tracker." + "db",
        "exports/applications." + "csv",
        "resume.pdf",
        "docs/My Resume.docx",
        "private/draft.txt",
    ],
)
def test_private_files_are_flagged(path):
    assert scan_repo.name_problem(path)


@pytest.mark.parametrize(
    "path", [".env.example", "demo/sample.pdf", "tests/fixtures/resume.docx", "src/app.py"]
)
def test_ordinary_files_pass(path):
    assert scan_repo.name_problem(path) is None


@pytest.mark.parametrize(
    "line",
    [
        "Contact: jane.doe@" + "gmail.com",
        "Phone (415) 555-" + "2671",
        "Call 650.253." + "0000",
        "+1 212 736 " + "5000",
    ],
)
def test_real_looking_contact_details_are_flagged(line):
    problems = scan_repo.content_problems("x.txt", line)
    assert problems
    assert "gmail" not in problems[0] and "415" not in problems[0]


@pytest.mark.parametrize(
    "line",
    [
        "pat@example.test | 555-0101",
        "jo@example.com (555) 555-0199",
        "12345+udhay@users.noreply.github.com",
        "2021-2024, 50,000+ users, 60% faster",
    ],
)
def test_synthetic_contact_details_pass(line):
    assert scan_repo.content_problems("x.txt", line) == []


def test_scan_reads_files_and_skips_binaries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("ok.txt").write_text("pat@example.test")
    Path("bad.txt").write_text("call (415) 555-" + "2671")
    Path("blob.bin").write_bytes(b"\xff\xfe\x00")
    assert scan_repo.scan(["ok.txt", "bad.txt", "blob.bin", "uv.lock"]) == [
        "bad.txt:1: real-looking phone (use 555-01xx)"
    ]
    assert scan_repo.main(["bad.txt"]) == 1
    assert scan_repo.main(["ok.txt"]) == 0


def test_the_repo_itself_is_clean(monkeypatch):
    monkeypatch.chdir(REPO)
    assert scan_repo.scan(scan_repo.tracked_files()) == []


VALID = {
    "lens": "security",
    "verdict": "SHIP",
    "findings": [
        {
            "severity": "MINOR",
            "file": "src/utils.py",
            "line": 3,
            "claim": "A claim that is long enough",
            "proof": "uv run pytest",
            "fix": "Do the thing",
        }
    ],
    "untested": [],
}


def test_valid_report_passes(tmp_path):
    path = tmp_path / "security.json"
    path.write_text(json.dumps(VALID))
    assert validate_review.main([str(path)]) == 0


def test_invalid_reports_fail(tmp_path, capsys):
    bad = dict(VALID, lens="ux", extra=True)
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    (tmp_path / "broken.json").write_text("{")
    assert validate_review.main([str(tmp_path / "bad.json"), str(tmp_path / "broken.json")]) == 1
    out = capsys.readouterr().out
    assert "lens" in out and "not readable JSON" in out


def test_no_reports_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert validate_review.main([]) == 1
