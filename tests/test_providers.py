"""Provider selection and the OpenAI-compatible path (mocked: no network)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src import ai_engine
from src.ai_engine import AIError


@pytest.fixture
def openai_env(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_PROVIDER", "openai")
    monkeypatch.setenv("RESUME_TAILOR_MODEL", "some-model")


def _reply(status: int = 200, payload: object = None) -> MagicMock:
    resp = MagicMock(status_code=status, ok=200 <= status < 300)
    resp.json.return_value = payload
    return resp


def _choice(content: str, finish: str = "stop") -> dict[str, object]:
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


def test_default_provider_is_anthropic():
    assert ai_engine.provider() == "anthropic"
    assert ai_engine.model() == "claude-opus-5-5"


@pytest.mark.parametrize("value", ["OpenAI", " openai "])
def test_provider_name_is_forgiving(monkeypatch, value):
    monkeypatch.setenv("RESUME_TAILOR_PROVIDER", value)
    assert ai_engine.provider() == "openai"


def test_unknown_provider_falls_back_to_anthropic(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_PROVIDER", "mystery")
    assert ai_engine.provider() == "anthropic"


@patch("src.ai_engine._client")
def test_anthropic_provider_never_calls_requests(mock_client):
    reply = MagicMock(stop_reason="end_turn", content=[MagicMock(type="text", text="hi")])
    mock_client.return_value.beta.messages.create.return_value = reply
    with patch("src.ai_engine.requests.post") as post:
        assert ai_engine._call_model("sys", "user") == "hi"
    post.assert_not_called()


def test_setup_problem_for_each_provider(monkeypatch):
    assert "ANTHROPIC_API_KEY" in (ai_engine.setup_problem() or "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert ai_engine.setup_problem() is None
    monkeypatch.setenv("RESUME_TAILOR_PROVIDER", "openai")
    assert "RESUME_TAILOR_MODEL" in (ai_engine.setup_problem() or "")
    monkeypatch.setenv("RESUME_TAILOR_MODEL", "m")
    assert ai_engine.setup_problem() is None


def test_openai_without_model_raises_before_any_call(monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_PROVIDER", "openai")
    with patch("src.ai_engine.requests.post") as post, pytest.raises(AIError, match="MODEL"):
        ai_engine._call_model("sys", "user")
    post.assert_not_called()


@patch("src.ai_engine.requests.post")
def test_openai_request_shape(post, openai_env, monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_API_KEY", "secret")
    post.return_value = _reply(payload=_choice("  tailored  "))
    assert ai_engine._call_model("the system", "the user") == "tailored"
    url = post.call_args.args[0]
    kwargs = post.call_args.kwargs
    assert url == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"] == {"Authorization": "Bearer secret"}
    assert kwargs["json"]["model"] == "some-model"
    assert kwargs["json"]["messages"] == [
        {"role": "system", "content": "the system"},
        {"role": "user", "content": "the user"},
    ]


@patch("src.ai_engine.requests.post")
def test_openai_custom_base_url_and_no_key(post, openai_env, monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_BASE_URL", "http://localhost:11434/v1/")
    post.return_value = _reply(payload=_choice("ok"))
    ai_engine._call_model("s", "u")
    assert post.call_args.args[0] == "http://localhost:11434/v1/chat/completions"
    assert post.call_args.kwargs["headers"] == {}


@patch("src.ai_engine.requests.post")
def test_openai_api_key_env_is_accepted(post, openai_env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    post.return_value = _reply(payload=_choice("ok"))
    ai_engine._call_model("s", "u")
    assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer sk-x"}


@pytest.mark.parametrize(
    ("status", "payload", "message"),
    [
        (401, None, "rejected"),
        (403, None, "rejected"),
        (429, None, "rate-limiting"),
        (500, None, r"error \(500\)"),
        (200, _choice("", "content_filter"), "declined"),
        (200, _choice("   "), "empty"),
        (200, {"choices": []}, "does not understand"),
        (200, {"nope": 1}, "does not understand"),
        (200, ["not", "a", "dict"], "does not understand"),
    ],
)
@patch("src.ai_engine.requests.post")
def test_openai_failures_become_plain_errors(post, openai_env, status, payload, message):
    post.return_value = _reply(status, payload)
    with pytest.raises(AIError, match=message):
        ai_engine._call_model("s", "u")


@patch("src.ai_engine.requests.post")
def test_openai_bad_json_is_a_plain_error(post, openai_env):
    resp = _reply(payload=None)
    resp.json.side_effect = ValueError("not json")
    post.return_value = resp
    with pytest.raises(AIError, match="does not understand"):
        ai_engine._call_model("s", "u")


@patch("src.ai_engine.requests.post")
def test_openai_unreachable_is_a_plain_error(post, openai_env):
    post.side_effect = requests.ConnectionError("down")
    with pytest.raises(AIError, match="Could not reach"):
        ai_engine._call_model("s", "u")


@patch("src.ai_engine.requests.post")
def test_generators_keep_truthfulness_rule_on_other_providers(post, openai_env):
    post.return_value = _reply(payload=_choice("Pat Example\nDraft"))
    ai_engine.generate_tailored_resume("Job", "Resume", {"name": "Pat Example"})
    system = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert ai_engine.TRUTHFULNESS_RULE in system
