"""Tests for AI engine module (mocked — no API calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src import ai_engine
from src.ai_engine import (
    AIError,
    _parse_json,
    analyze_job_description,
    generate_cover_letter,
    generate_tailored_resume,
    keyword_match_report,
    score_fit,
)

PROFILE = {"name": "Pat Example", "email": "pat@example.test", "phone": "555-0101"}


def _mock_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    """A mock reply: a thinking block (always on for current models) then text."""
    thinking = MagicMock(type="thinking", thinking="")
    del thinking.text
    msg = MagicMock(stop_reason=stop_reason)
    msg.content = [thinking, MagicMock(type="text", text=text)]
    return msg


def _create(mock_client: MagicMock) -> MagicMock:
    return mock_client.return_value.beta.messages.create


class TestParseJson:
    def test_plain_json(self):
        assert _parse_json('{"key": "value"}') == {"key": "value"}

    def test_json_with_code_fences(self):
        assert _parse_json('```json\n{"key": "value"}\n```') == {"key": "value"}

    def test_json_inside_prose(self):
        assert _parse_json('Here you go: {"key": 1} hope it helps') == {"key": 1}

    def test_invalid_json(self):
        assert "error" in _parse_json("not json at all")

    def test_braces_that_are_not_json(self):
        assert "error" in _parse_json("use {curly} braces")

    def test_json_that_is_not_an_object(self):
        assert "error" in _parse_json("[1, 2, 3]")


@patch("src.ai_engine._client")
def test_analyze_job_description(mock_client):
    response_data = {
        "title": "Software Engineer",
        "company": "Acme Corp",
        "skills": ["Python", "AWS"],
    }
    _create(mock_client).return_value = _mock_response(json.dumps(response_data))
    result = analyze_job_description("We need a Python developer...")
    assert result["title"] == "Software Engineer"
    assert "Python" in result["skills"]


@patch("src.ai_engine._client")
def test_score_fit(mock_client):
    _create(mock_client).return_value = _mock_response(json.dumps({"score": 75}))
    assert score_fit("Job desc here", "Resume text here")["score"] == 75


@patch("src.ai_engine._client")
def test_keyword_match_report(mock_client):
    payload = {"matched": ["Python"], "missing": ["Kubernetes"], "match_percentage": 67}
    _create(mock_client).return_value = _mock_response(json.dumps(payload))
    result = keyword_match_report("Job desc", "Resume text")
    assert result["match_percentage"] == 67


@patch("src.ai_engine._client")
def test_request_uses_current_model_effort_and_fallbacks(mock_client, monkeypatch):
    monkeypatch.delenv("RESUME_TAILOR_MODEL", raising=False)
    monkeypatch.delenv("RESUME_TAILOR_EFFORT", raising=False)
    _create(mock_client).return_value = _mock_response("ok")
    ai_engine._call_claude("sys", "user")
    kwargs = _create(mock_client).call_args.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_config"] == {"effort": "medium"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert "temperature" not in kwargs


@patch("src.ai_engine._client")
def test_model_and_effort_come_from_env(mock_client, monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("RESUME_TAILOR_EFFORT", "low")
    _create(mock_client).return_value = _mock_response("ok")
    ai_engine._call_claude("sys", "user")
    kwargs = _create(mock_client).call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["output_config"] == {"effort": "low"}


def test_unknown_effort_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_EFFORT", "turbo")
    assert ai_engine.effort() == "medium"


@patch("src.ai_engine._client")
def test_thinking_blocks_are_skipped(mock_client):
    _create(mock_client).return_value = _mock_response("the answer")
    assert ai_engine._call_claude("sys", "user") == "the answer"


@patch("src.ai_engine._client")
def test_refusal_raises_plain_error(mock_client):
    _create(mock_client).return_value = _mock_response("", stop_reason="refusal")
    with pytest.raises(AIError, match="declined"):
        ai_engine._call_claude("sys", "user")


@patch("src.ai_engine._client")
def test_empty_reply_raises(mock_client):
    _create(mock_client).return_value = _mock_response("   ")
    with pytest.raises(AIError, match="empty"):
        ai_engine._call_claude("sys", "user")


@pytest.mark.parametrize("generate", [generate_tailored_resume, generate_cover_letter])
@patch("src.ai_engine._client")
def test_generators_forbid_invented_facts(mock_client, generate):
    _create(mock_client).return_value = _mock_response("Pat Example\nDraft")
    assert generate("Job", "Resume", PROFILE) == "Pat Example\nDraft"
    kwargs = _create(mock_client).call_args.kwargs
    assert ai_engine.TRUTHFULNESS_RULE in kwargs["system"]
    assert "Pat Example" in kwargs["messages"][0]["content"]
