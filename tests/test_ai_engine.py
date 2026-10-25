"""Tests for AI engine module (mocked — no API calls)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src import ai_engine
from src.ai_engine import (
    AIError,
    _parse_json,
    analyze_job_description,
    fit_score_from,
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


def _req(name: str, weight: str, status: str) -> dict[str, str]:
    return {"requirement": name, "weight": weight, "status": status, "evidence": ""}


class TestFitScoreFrom:
    def test_weights_and_credit(self):
        reqs = [
            _req("a", "core", "met"),
            _req("b", "required", "partial"),
            _req("c", "preferred", "missing"),
        ]
        # earned 3 + 1 + 0 = 4 of 6 possible
        assert fit_score_from(reqs) == 67

    def test_all_met_is_100(self):
        assert fit_score_from([_req("a", "core", "met"), _req("b", "preferred", "met")]) == 100

    def test_unknown_rows_are_left_out(self):
        reqs = [_req("a", "core", "met"), _req("b", "nice", "missing"), _req("c", "core", "maybe")]
        assert fit_score_from(reqs) == 100

    def test_case_and_whitespace_are_tolerated(self):
        assert fit_score_from([_req("a", " Core ", "MISSING"), _req("b", "core", "met")]) == 50

    def test_nothing_usable_is_zero(self):
        assert fit_score_from([]) == 0
        assert fit_score_from("not a list") == 0
        assert fit_score_from(["not a row", _req("a", "core", "met")]) == 100


class TestScoreFit:
    @patch("src.ai_engine._client")
    def test_model_score_is_ignored(self, mock_client):
        reply = {
            "score": 99,
            "requirements": [_req("a", "core", "met"), _req("b", "core", "missing")],
        }
        _create(mock_client).return_value = _mock_response(json.dumps(reply))
        assert score_fit("Job", "Resume")["score"] == 50

    @patch("src.ai_engine._client")
    def test_every_gap_listed_core_first(self, mock_client):
        reqs = [_req(f"pref{i}", "preferred", "missing") for i in range(4)]
        reqs += [_req("graph", "core", "missing"), _req("lake", "required", "partial")]
        reqs += [_req(f"core{i}", "core", "partial") for i in range(2)] + [
            _req("ok", "core", "met")
        ]
        _create(mock_client).return_value = _mock_response(json.dumps({"requirements": reqs}))
        gaps = score_fit("Job", "Resume")["gaps"]
        assert len(gaps) == 8
        assert [g.split("]")[0] for g in gaps[:3]] == [
            "[core, missing",
            "[core, partial",
            "[core, partial",
        ]
        assert gaps[3].startswith("[required, partial] lake")
        assert all(g.startswith("[preferred") for g in gaps[4:])
        assert not any("ok" in g for g in gaps)

    @patch("src.ai_engine._client")
    def test_no_requirements_is_an_error(self, mock_client):
        _create(mock_client).return_value = _mock_response(json.dumps({"score": 75}))
        assert "error" in score_fit("Job", "Resume")

    @patch("src.ai_engine._client")
    def test_unparseable_reply_is_an_error(self, mock_client):
        _create(mock_client).return_value = _mock_response("not json")
        assert "error" in score_fit("Job", "Resume")

    @patch("src.ai_engine._client")
    def test_prompt_asks_for_every_requirement_weighted(self, mock_client):
        _create(mock_client).return_value = _mock_response(
            json.dumps({"requirements": [_req("a", "core", "met")]})
        )
        score_fit("THE JOB", "THE RESUME")
        kwargs = _create(mock_client).call_args.kwargs
        prompt = kwargs["messages"][0]["content"]
        for word in ("core", "required", "preferred", "met", "partial", "missing", "impression"):
            assert word in prompt
        assert "max 5" not in prompt.split('"explanation"')[0]
        assert "THE JOB" not in kwargs["system"] and "THE RESUME" not in kwargs["system"]


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
    ai_engine._call_model("sys", "user")
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
    ai_engine._call_model("sys", "user")
    kwargs = _create(mock_client).call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["output_config"] == {"effort": "low"}


def test_unknown_effort_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_EFFORT", "turbo")
    assert ai_engine.effort() == "medium"


@patch("src.ai_engine._client")
def test_thinking_blocks_are_skipped(mock_client):
    _create(mock_client).return_value = _mock_response("the answer")
    assert ai_engine._call_model("sys", "user") == "the answer"


@patch("src.ai_engine._client")
def test_refusal_raises_plain_error(mock_client):
    _create(mock_client).return_value = _mock_response("", stop_reason="refusal")
    with pytest.raises(AIError, match="declined"):
        ai_engine._call_model("sys", "user")


@patch("src.ai_engine._client")
def test_empty_reply_raises(mock_client):
    _create(mock_client).return_value = _mock_response("   ")
    with pytest.raises(AIError, match="empty"):
        ai_engine._call_model("sys", "user")


@pytest.mark.parametrize("generate", [generate_tailored_resume, generate_cover_letter])
@patch("src.ai_engine._client")
def test_generators_forbid_invented_facts(mock_client, generate):
    _create(mock_client).return_value = _mock_response("Pat Example\nDraft")
    assert generate("Job", "Resume", PROFILE) == "Pat Example\nDraft"
    kwargs = _create(mock_client).call_args.kwargs
    assert ai_engine.TRUTHFULNESS_RULE in kwargs["system"]
    assert "Pat Example" in kwargs["messages"][0]["content"]
