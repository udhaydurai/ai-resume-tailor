"""Tests for AI engine module (mocked — no API calls)."""

import json
from unittest.mock import patch, MagicMock

from src.ai_engine import (
    analyze_job_description,
    score_fit,
    keyword_match_report,
    _parse_json,
)


def _mock_response(text: str):
    """Create a mock Anthropic API response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


class TestParseJson:
    def test_plain_json(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_code_fences(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_invalid_json(self):
        result = _parse_json("not json at all")
        assert "error" in result


@patch("src.ai_engine._client")
def test_analyze_job_description(mock_client):
    response_data = {
        "title": "Software Engineer",
        "company": "Acme Corp",
        "requirements": ["3+ years Python"],
        "skills": ["Python", "AWS"],
        "keywords": ["microservices", "CI/CD"],
        "experience_level": "Mid",
        "summary": "A mid-level SWE role.",
    }
    mock_client.return_value.messages.create.return_value = _mock_response(
        json.dumps(response_data)
    )
    result = analyze_job_description("We need a Python developer...")
    assert result["title"] == "Software Engineer"
    assert "Python" in result["skills"]


@patch("src.ai_engine._client")
def test_score_fit(mock_client):
    response_data = {
        "score": 75,
        "explanation": "Good fit.",
        "strengths": ["Python experience"],
        "gaps": ["No AWS certs"],
        "suggestions": ["Get AWS certified"],
    }
    mock_client.return_value.messages.create.return_value = _mock_response(
        json.dumps(response_data)
    )
    result = score_fit("Job desc here", "Resume text here")
    assert result["score"] == 75


@patch("src.ai_engine._client")
def test_keyword_match_report(mock_client):
    response_data = {
        "matched": ["Python", "Docker"],
        "missing": ["Kubernetes"],
        "match_percentage": 67,
    }
    mock_client.return_value.messages.create.return_value = _mock_response(
        json.dumps(response_data)
    )
    result = keyword_match_report("Job desc", "Resume text")
    assert result["match_percentage"] == 67
    assert "Python" in result["matched"]
