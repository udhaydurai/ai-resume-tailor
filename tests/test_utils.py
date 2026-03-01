"""Tests for utility functions."""

from unittest.mock import patch, MagicMock

import pytest
import requests

from src.utils import fetch_job_description


@patch("src.utils.requests.get")
def test_fetch_job_description(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
    <head><title>Job</title></head>
    <body>
        <nav>Nav stuff</nav>
        <div>
            <h1>Software Engineer</h1>
            <p>We are looking for a talented engineer.</p>
            <p>Requirements: Python, AWS, Docker</p>
        </div>
        <footer>Footer stuff</footer>
    </body>
    </html>
    """
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = fetch_job_description("https://example.com/job")
    assert "Software Engineer" in result
    assert "Python" in result
    # Nav and footer should be stripped
    assert "Nav stuff" not in result
    assert "Footer stuff" not in result


@patch("src.utils.requests.get")
def test_fetch_job_description_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("Connection error")
    with pytest.raises(ValueError, match="Could not fetch URL"):
        fetch_job_description("https://bad-url.example.com")
