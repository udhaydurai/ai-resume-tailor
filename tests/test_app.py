"""Smoke test: drive the real Streamlit app headlessly, with Claude mocked."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

from src import job_tracker

REPO = Path(__file__).resolve().parents[1]
JOB = (REPO / "demo" / "sample_job_description.txt").read_text()
RESUME = (REPO / "demo" / "sample_resume.txt").read_text()

REPLIES = {
    "Analyze this job description": json.dumps(
        {"title": "Backend Engineer", "company": "Acme", "skills": ["Python"], "keywords": []}
    ),
    "Compare the resume": json.dumps(
        {"score": 72, "explanation": "Good.", "strengths": [], "gaps": [], "suggestions": []}
    ),
    "Identify ATS keywords": json.dumps(
        {"matched": ["Python"], "missing": ["Go"], "match_percentage": 50}
    ),
    "Rewrite the resume": "JOHN DOE\n\nEXPERIENCE\n- Grew revenue 900% at R&D Corp",
    "Write a professional cover letter": "Dear Hiring Manager,\n\nI am excited.",
}


def fake_create(**kwargs: object) -> MagicMock:
    prompt = kwargs["messages"][0]["content"]  # type: ignore[index]
    text = next(reply for start, reply in REPLIES.items() if prompt.startswith(start))
    return MagicMock(stop_reason="end_turn", content=[MagicMock(type="text", text=text)])


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(job_tracker, "DB_PATH", tmp_path / "tracker")
    client = MagicMock()
    client.beta.messages.create.side_effect = fake_create
    with patch("src.ai_engine._client", return_value=client), patch("dotenv.load_dotenv"):
        at = AppTest.from_file(str(REPO / "app.py"), default_timeout=30)
        at.session_state["job_desc"] = JOB
        at.session_state["resume_text"] = RESUME
        yield at


def click(at: AppTest, key: str) -> None:
    at.button(key=key).click().run()
    assert not at.exception, at.exception


def test_full_flow_with_mocked_claude(app):
    app.run()
    assert not app.exception
    for key in ("btn_analyze_jd", "btn_score", "btn_keywords", "btn_gen_resume", "btn_gen_cover"):
        click(app, key)
    markdown = " ".join(m.value for m in app.markdown)
    assert "Alignment Score" in markdown and "Keyword Match" in markdown
    warnings = " ".join(w.value for w in app.warning)
    assert "900%" in warnings
    assert app.session_state["tailored_resume"].startswith("JOHN DOE")
    assert app.session_state["cover_letter"].startswith("Dear Hiring Manager")


def test_missing_key_shows_a_warning(app, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    app.run()
    assert any("ANTHROPIC_API_KEY" in w.value for w in app.warning)


def test_refusal_shows_a_plain_error(app):
    with patch("src.ai_engine._client") as client:
        client.return_value.beta.messages.create.return_value = MagicMock(
            stop_reason="refusal", content=[]
        )
        app.run()
        click(app, "btn_analyze_jd")
    assert any("declined" in e.value for e in app.error)
