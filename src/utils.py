"""Utility functions for the AI Resume Tailor app."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup


def fetch_job_description(url: str) -> str:
    """Fetch and extract text from a job posting URL.

    Returns the extracted text content.

    Raises:
        ValueError: If the URL cannot be fetched.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Could not fetch URL: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse multiple blank lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)
