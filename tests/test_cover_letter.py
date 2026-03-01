"""Tests for cover letter generator module."""

from src.cover_letter import generate_cover_letter_docx


SAMPLE_LETTER = """Dear Hiring Manager,

I am excited to apply for the Software Engineer role at Acme Corp.

My background in full-stack development aligns well with your mission to build scalable cloud solutions.

In my current role at Beta Inc, I led a team of 5 engineers to deliver a real-time analytics platform that reduced reporting time by 60%.

I would welcome the opportunity to discuss how I can contribute to your team. I am available for an interview at your convenience.

Sincerely,
John Doe
"""


def test_generate_cover_letter_docx():
    profile = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "555-0100",
        "linkedin": "https://linkedin.com/in/johndoe",
    }
    result = generate_cover_letter_docx(SAMPLE_LETTER, profile)
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:2] == b"PK"


def test_generate_cover_letter_docx_empty_profile():
    profile = {"name": "", "email": "", "phone": "", "linkedin": ""}
    result = generate_cover_letter_docx(SAMPLE_LETTER, profile)
    assert isinstance(result, bytes)
    assert len(result) > 0
