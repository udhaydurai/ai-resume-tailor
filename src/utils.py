"""Utility functions for the AI Resume Tailor app."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def check_public_url(url: str) -> None:
    """Reject anything but http(s) URLs that resolve only to public addresses.

    Stops a pasted link from reaching this machine or its local network.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only http:// or https:// job links are supported.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise ValueError(f"Could not find {parsed.hostname}.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError("That link points to a private or local address.")


def fetch_job_description(url: str) -> str:
    """Fetch and extract text from a job posting URL.

    Returns the extracted text content.

    Raises:
        ValueError: If the URL is not public or cannot be fetched.
    """
    try:
        for _ in range(MAX_REDIRECTS + 1):
            check_public_url(url)
            resp = requests.get(
                url, headers=HEADERS, timeout=15, allow_redirects=False, stream=True
            )
            if resp.is_redirect and "location" in resp.headers:
                url = urljoin(url, resp.headers["location"])
                continue
            resp.raise_for_status()
            body = resp.raw.read(MAX_BYTES + 1, decode_content=True)
            break
        else:
            raise ValueError("Too many redirects.")
    except requests.RequestException as exc:
        raise ValueError(f"Could not fetch URL: {exc}") from exc
    if len(body) > MAX_BYTES:
        raise ValueError("That page is too large to read.")

    html = body.decode(resp.encoding or "utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)
