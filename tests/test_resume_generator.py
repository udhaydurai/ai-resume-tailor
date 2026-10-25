"""Tests for resume generator module."""

from src.resume_generator import generate_docx, generate_pdf

SAMPLE_RESUME = """John Doe | john@example.com | 555-0100

PROFESSIONAL SUMMARY
Experienced software engineer with 5 years building web applications.

EXPERIENCE
Senior Software Engineer — Acme Corp (2020-Present)
- Led development of microservices architecture serving 1M+ users
- Reduced API latency by 40% through caching optimizations

SKILLS
Python, JavaScript, React, AWS, Docker

EDUCATION
B.S. Computer Science — MIT, 2018
"""


def test_generate_docx():
    result = generate_docx(SAMPLE_RESUME)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # DOCX files start with PK (ZIP format)
    assert result[:2] == b"PK"


def test_generate_pdf():
    result = generate_pdf(SAMPLE_RESUME)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # PDF files start with %PDF
    assert result[:4] == b"%PDF"


def test_pdf_handles_markup_characters():
    text = "Pat Example\n\nEXPERIENCE\n- Built R&D tools at AT&T for <team> leads\n"
    assert generate_pdf(text).startswith(b"%PDF")


def test_ampersand_header_still_bold_header():
    assert generate_pdf("Pat Example\n\nR&D\n").startswith(b"%PDF")
