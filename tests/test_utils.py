"""Tests for utility functions."""

import json
import socket
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.utils import MAX_BYTES, check_public_url, fetch_job_description, workday_api_url

PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

HTML = b"""
<html>
<head><title>Job</title></head>
<body>
    <nav>Nav stuff</nav>
    <div>
        <h1>Software Engineer</h1>
        <p>We are looking for a talented engineer.</p>
        <p>Requirements: Python, AWS, Docker</p>
        <p>You will design, build and operate backend services, mentor engineers,
        review designs, and work with product managers to ship features that customers
        rely on every day. Five or more years of experience building web services.</p>
    </div>
    <footer>Footer stuff</footer>
</body>
</html>
"""


def _resp(body: bytes = HTML, location: str | None = None) -> MagicMock:
    resp = MagicMock()
    resp.is_redirect = location is not None
    resp.headers = {"location": location} if location else {}
    resp.encoding = "utf-8"
    resp.raw.read.side_effect = lambda n, decode_content: body[:n]
    return resp


def _addr(ip: str) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]


@pytest.fixture
def public_dns():
    with patch("src.utils.socket.getaddrinfo", return_value=PUBLIC) as dns:
        yield dns


@patch("src.utils.requests.get")
def test_fetch_job_description(mock_get, public_dns):
    mock_get.return_value = _resp()
    result = fetch_job_description("https://example.com/job")
    assert "Software Engineer" in result
    assert "Python" in result
    assert "Nav stuff" not in result
    assert "Footer stuff" not in result
    assert mock_get.call_args.kwargs["allow_redirects"] is False


@patch("src.utils.requests.get")
def test_fetch_job_description_failure(mock_get, public_dns):
    mock_get.side_effect = requests.ConnectionError("Connection error")
    with pytest.raises(ValueError, match="Could not fetch URL"):
        fetch_job_description("https://bad-url.example.com")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "notaurl"])
def test_rejects_non_http_schemes(url):
    with pytest.raises(ValueError, match="Only http"):
        check_public_url(url)


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "fd00::1"]
)
def test_rejects_private_addresses(ip):
    with (
        patch("src.utils.socket.getaddrinfo", return_value=_addr(ip)),
        pytest.raises(ValueError, match="private or local"),
    ):
        check_public_url("http://looks-public.example.com/job")


def test_rejects_unknown_host():
    with (
        patch("src.utils.socket.getaddrinfo", side_effect=socket.gaierror),
        pytest.raises(ValueError, match="Could not find"),
    ):
        check_public_url("https://nope.example.com")


@patch("src.utils.requests.get")
def test_redirect_to_private_address_is_blocked(mock_get):
    mock_get.return_value = _resp(location="http://169.254.169.254/latest/meta-data")
    lookups = iter([PUBLIC, _addr("169.254.169.254")])
    with (
        patch("src.utils.socket.getaddrinfo", side_effect=lambda *a: next(lookups)),
        pytest.raises(ValueError, match="private or local"),
    ):
        fetch_job_description("https://example.com/job")


@patch("src.utils.requests.get")
def test_follows_public_redirect(mock_get, public_dns):
    mock_get.side_effect = [_resp(location="/jobs/1"), _resp()]
    assert "Software Engineer" in fetch_job_description("https://example.com/j")
    assert mock_get.call_args.args[0] == "https://example.com/jobs/1"


@patch("src.utils.requests.get")
def test_too_many_redirects(mock_get, public_dns):
    mock_get.return_value = _resp(location="/again")
    with pytest.raises(ValueError, match="Too many redirects"):
        fetch_job_description("https://example.com/loop")


@patch("src.utils.requests.get")
def test_oversized_page_is_rejected(mock_get, public_dns):
    mock_get.return_value = _resp(body=b"x" * (MAX_BYTES + 10))
    with pytest.raises(ValueError, match="too large"):
        fetch_job_description("https://example.com/huge")


WORKDAY = "https://acme.wd5.myworkdayjobs.com/Careers/job/Remote-USA/Data-Lead_JR1?source=LinkedIn"


@pytest.mark.parametrize(
    ("url", "api"),
    [
        (
            WORKDAY,
            "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/job/Remote-USA/Data-Lead_JR1",
        ),
        (
            "https://acme.wd1.myworkdayjobs.com/en-US/Ext/job/Data-Lead_JR2",
            "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/Ext/job/Data-Lead_JR2",
        ),
        ("https://acme.wd5.myworkdayjobs.com/Careers", None),
        ("https://example.com/Careers/job/x", None),
        ("https://myworkdayjobs.com.evil.example/Careers/job/x", None),
    ],
)
def test_workday_api_url(url, api):
    assert workday_api_url(url) == api


@patch("src.utils.requests.get")
def test_workday_postings_use_the_json_endpoint(mock_get, public_dns):
    payload = {
        "jobPostingInfo": {
            "title": "Data Lead",
            "jobDescription": "<p>" + "Own the data platform and lead the team. " * 10 + "</p>",
        }
    }
    mock_get.return_value = _resp(body=json.dumps(payload).encode())
    text = fetch_job_description(WORKDAY)
    assert text.startswith("Data Lead\nOwn the data platform")
    assert "/wday/cxs/acme/Careers/job/" in mock_get.call_args.args[0]
    assert mock_get.call_args.kwargs["headers"]["Accept"] == "application/json"


@patch("src.utils.requests.get")
def test_unexpected_workday_reply_is_a_plain_error(mock_get, public_dns):
    mock_get.return_value = _resp(body=b'{"something": "else"}')
    with pytest.raises(ValueError, match="does not understand"):
        fetch_job_description(WORKDAY)


@patch("src.utils.requests.get")
def test_javascript_only_page_says_paste_instead(mock_get, public_dns):
    mock_get.return_value = _resp(
        body=b"<html><body><div id='root'></div><script>app()</script></body></html>"
    )
    with pytest.raises(ValueError, match="Paste text"):
        fetch_job_description("https://example.com/job")
