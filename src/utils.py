"""Utility functions for the AI Resume Tailor app."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3
MIN_TEXT = 200
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

    Workday postings are read through Workday's JSON endpoint, because their pages
    load the text with JavaScript.

    Raises:
        ValueError: If the URL is not public, cannot be fetched, or holds no job text.
    """
    api_url = workday_api_url(url)
    if api_url:
        text = _workday_text(_get(api_url, accept="application/json"))
    else:
        body, encoding = _get(url)
        text = html_to_text(body.decode(encoding, errors="replace"))
    if len(text) < MIN_TEXT:
        raise ValueError(
            "That page has almost no text: it probably loads the job with JavaScript. "
            "Open it in your browser, copy the job description, and use Paste text instead."
        )
    return text


def workday_api_url(url: str) -> str | None:
    """`https://acme.wd5.myworkdayjobs.com/[en-US/]Site/job/...` -> its JSON endpoint."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host.endswith(".myworkdayjobs.com"):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
        parts = parts[1:]
    if len(parts) < 3 or parts[1] != "job":
        return None
    tenant, site, rest = host.split(".")[0], parts[0], "/".join(parts[2:])
    return f"https://{host}/wday/cxs/{tenant}/{site}/job/{rest}"


def _workday_text(fetched: tuple[bytes, str]) -> str:
    body, encoding = fetched
    try:
        info = json.loads(body.decode(encoding, errors="replace"))["jobPostingInfo"]
        title, description = str(info.get("title", "")), str(info["jobDescription"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("Workday sent a reply this app does not understand.") from exc
    return "\n".join(part for part in (title, html_to_text(description)) if part)


def _get(url: str, accept: str | None = None) -> tuple[bytes, str]:
    headers = {**HEADERS, "Accept": accept} if accept else HEADERS
    try:
        for _ in range(MAX_REDIRECTS + 1):
            check_public_url(url)
            resp = requests.get(
                url, headers=headers, timeout=15, allow_redirects=False, stream=True
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
    return body, resp.encoding or "utf-8"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())
